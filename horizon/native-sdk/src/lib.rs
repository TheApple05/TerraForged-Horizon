//! TerraForged terrain nodes for Horizon's public native mod SDK.
use std::sync::{Arc, Mutex};

use mod_api::{DensityFunction, DensityFunctionType, Hooks, Registrar, RegistrationContext};
use serde_json::Value;
use terraforged_native_adapter::{noise_registry::NoiseRegistry, preset::CellPresetInput};
use terraforged_native_core::{
    density_primitives::{CellField, clamp_to_nearest_unit},
    graph::Noise,
    kernel_sampler::{KernelSampler, SamplerOptions},
    preset::KernelPreset,
};

const PRESET: &str = include_str!("../../tests/fixtures/kernel-v1/preset.json");
const NOISES: &str = include_str!("../../tests/fixtures/kernel-v1/noise-registry.json");

struct Terrain {
    preset: KernelPreset,
    ground: Noise,
    edge: Noise,
    active: Mutex<Option<(i32, Arc<KernelSampler>)>>,
}

impl Terrain {
    fn bundled() -> Result<Self, String> {
        let preset = CellPresetInput::from_json(PRESET)
            .map_err(|err| err.to_string())?
            .kernel;
        let noises = NoiseRegistry::from_json(NOISES).map_err(|err| err.to_string())?;
        let noise = |id| noises.get(id).map_err(|err| err.to_string());
        Ok(Self {
            preset,
            ground: noise("reterraforged:terrain/ground")?,
            edge: noise("reterraforged:climate/biome_edge_shape")?,
            active: Mutex::default(),
        })
    }

    fn sampler(&self, seed: i64) -> Arc<KernelSampler> {
        // The existing TerraForged kernel uses the low 32 bits of the world seed.
        let seed = seed as i32;
        let mut active = self.active.lock().expect("TerraForged sampler lock");
        if let Some((active_seed, sampler)) = active.as_ref()
            && *active_seed == seed
        {
            return Arc::clone(sampler);
        }
        let sampler = Arc::new(
            KernelSampler::new(
                &self.preset,
                seed,
                self.ground.clone(),
                self.edge.clone(),
                SamplerOptions::for_preset(&self.preset),
            )
            .expect("validated bundled TerraForged preset"),
        );
        *active = Some((seed, Arc::clone(&sampler)));
        sampler
    }
}

struct DensityType(Arc<Terrain>);

impl DensityFunctionType for DensityType {
    fn decode(&self, json: &str) -> Result<Arc<dyn DensityFunction>, String> {
        let node: Value = serde_json::from_str(json).map_err(|err| err.to_string())?;
        let field = node["field"]
            .as_str()
            .ok_or("missing TerraForged cell field")?;
        let field = CellField::parse(field).map_err(|err| err.to_string())?;
        let quantize_height = match node.get("quantize_height") {
            None | Some(Value::Bool(false)) => false,
            Some(Value::Bool(true)) if field == CellField::Height => true,
            _ => {
                return Err(
                    "quantize_height must be a boolean and only height can be quantized".into(),
                );
            }
        };
        Ok(Arc::new(CellDensity {
            terrain: Arc::clone(&self.0),
            field,
            quantize_height,
        }))
    }
}

struct CellDensity {
    terrain: Arc<Terrain>,
    field: CellField,
    quantize_height: bool,
}

impl CellDensity {
    fn column(&self, sampler: &KernelSampler, x: i32, z: i32) -> f32 {
        let cell = sampler
            .sample(x, z)
            .expect("TerraForged tile generation failed");
        let heightmap = sampler.heightmap();
        let value = self
            .field
            .read(
                &cell,
                heightmap.levels,
                heightmap.control_points,
                &heightmap.terrains,
            )
            .expect("TerraForged cell field conversion failed");
        if self.quantize_height {
            clamp_to_nearest_unit(
                f64::from(value),
                self.terrain.preset.world.properties.terrain_scaler(),
            ) as f32
        } else {
            value
        }
    }
}

impl DensityFunction for CellDensity {
    fn range(&self) -> [f32; 2] {
        // Use the SDK's largest conservative bounds rather than the Java metadata.
        [-1_000_000.0, 1_000_000.0]
    }

    fn varies_with_y(&self) -> bool {
        false
    }

    fn sample(&self, [x, _, z]: [i32; 3], seed: i64) -> f32 {
        self.column(&self.terrain.sampler(seed), x, z)
    }

    fn fill(
        &self,
        origin: [i32; 3],
        step: [i32; 3],
        count: [usize; 3],
        seed: i64,
        out: &mut [f32],
    ) {
        if count.contains(&0) {
            return;
        }
        let sampler = self.terrain.sampler(seed);
        let mut columns = out.chunks_exact_mut(count[1]);
        for z in 0..count[2] {
            let z = origin[2].wrapping_add((z as i32).wrapping_mul(step[2]));
            for x in 0..count[0] {
                let x = origin[0].wrapping_add((x as i32).wrapping_mul(step[0]));
                columns
                    .next()
                    .expect("Horizon volume buffer")
                    .fill(self.column(&sampler, x, z));
            }
        }
    }
}

#[derive(Default)]
struct TerraForged;

#[mod_api::horizon_mod]
impl Hooks for TerraForged {
    fn register(&self, registrar: &mut dyn Registrar, _: &RegistrationContext) {
        let terrain = Terrain::bundled().expect("bundled TerraForged inputs");
        registrar.register_density_function_type("cell", DensityType(Arc::new(terrain)));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decoded_cell_matches_kernel_across_y_and_seed_switches() {
        let terrain = Arc::new(Terrain::bundled().unwrap());
        let density_type = DensityType(Arc::clone(&terrain));
        assert!(
            density_type
                .decode(r#"{"field":"height","quantize_height":8}"#)
                .is_err()
        );
        assert!(
            density_type
                .decode(r#"{"field":"erosion","quantize_height":true}"#)
                .is_err()
        );
        assert!(density_type.decode(r#"{"field":"undefined"}"#).is_err());
        let height = density_type.decode(r#"{"field":"height"}"#).unwrap();
        assert!(!height.varies_with_y());
        let quantized = density_type
            .decode(r#"{"field":"height","quantize_height":true}"#)
            .unwrap();
        let seeds = [8675309, i64::MIN + 41, 8675309];
        for seed in seeds {
            let sampler = terrain.sampler(seed);
            let expected = sampler.sample(-17, 21).unwrap().height;
            assert_eq!(
                height.sample([-17, 45, 21], seed).to_bits(),
                expected.to_bits()
            );
            let expected_quantized = clamp_to_nearest_unit(
                f64::from(expected),
                terrain.preset.world.properties.terrain_scaler(),
            ) as f32;
            assert_eq!(
                quantized.sample([-17, -5, 21], seed).to_bits(),
                expected_quantized.to_bits()
            );
            let mut actual = [f32::NAN; 12];
            height.fill([-17, -5, 21], [3, 2, -7], [3, 2, 2], seed, &mut actual);
            for (index, value) in actual.into_iter().enumerate() {
                let x = -17 + 3 * ((index / 2) % 3) as i32;
                let z = 21 - 7 * (index / 6) as i32;
                assert_eq!(
                    value.to_bits(),
                    sampler.sample(x, z).unwrap().height.to_bits()
                );
            }
        }
    }
}
