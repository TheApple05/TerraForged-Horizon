//! TerraForged terrain nodes for Horizon's public native mod SDK.
use std::sync::{Arc, Mutex, Weak};

use mod_api::{
    BiomeMapper, BiomeMapperType, DensityFunction, DensityFunctionType, Hooks, Registrar,
    RegistrationContext,
};
use serde_json::Value;
use terraforged_native_adapter::{
    noise_registry::NoiseRegistry, preset::CellPresetInput, preset_editor::apply_overrides,
};
use terraforged_native_core::{
    classic_biomes,
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
    fn build_sampler(&self, seed: i32) -> Result<KernelSampler, String> {
        KernelSampler::new(
            &self.preset,
            seed,
            self.ground.clone(),
            self.edge.clone(),
            SamplerOptions::for_preset(&self.preset),
        )
        .map_err(|err| err.to_string())
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
            self.build_sampler(seed)
                .expect("validated TerraForged preset"),
        );
        *active = Some((seed, Arc::clone(&sampler)));
        sampler
    }
}

struct TerrainCatalog {
    defaults: Value,
    bundled: Arc<Terrain>,
    configured: Mutex<Vec<(Value, Weak<Terrain>)>>,
}

impl TerrainCatalog {
    fn bundled() -> Result<Self, String> {
        let input = CellPresetInput::from_json(PRESET).map_err(|err| err.to_string())?;
        let noises = NoiseRegistry::from_json(NOISES).map_err(|err| err.to_string())?;
        let noise = |id| noises.get(id).map_err(|err| err.to_string());
        let bundled = Arc::new(Terrain {
            preset: input.kernel,
            ground: noise("reterraforged:terrain/ground")?,
            edge: noise("reterraforged:climate/biome_edge_shape")?,
            active: Mutex::default(),
        });
        Ok(Self {
            defaults: input.original,
            bundled,
            configured: Mutex::default(),
        })
    }

    fn terrain(&self, settings: Option<&Value>) -> Result<Arc<Terrain>, String> {
        let Some(settings) = settings else {
            return Ok(self.bundled.clone());
        };
        let overrides = settings
            .as_object()
            .ok_or("TerraForged preset settings must be an object")?;
        if overrides.is_empty() {
            return Ok(self.bundled.clone());
        }

        // Cache only live graph owners. This also shares a sampler between nodes of one preset.
        let mut configured = self.configured.lock().map_err(|err| err.to_string())?;
        configured.retain(|(_, terrain)| terrain.strong_count() != 0);
        if let Some(terrain) = configured
            .iter()
            .find(|(key, _)| key == settings)
            .and_then(|(_, terrain)| terrain.upgrade())
        {
            return Ok(terrain);
        }
        let preset = apply_overrides(&self.defaults, overrides)?;
        let terrain = Arc::new(Terrain {
            preset: CellPresetInput::from_value(preset)
                .map_err(|err| err.to_string())?
                .kernel,
            ground: self.bundled.ground.clone(),
            edge: self.bundled.edge.clone(),
            active: Mutex::default(),
        });
        // Kernel construction validates parameter relationships independently of the seed.
        terrain.build_sampler(0)?;
        if configured.len() < 16 {
            configured.push((settings.clone(), Arc::downgrade(&terrain)));
        }
        Ok(terrain)
    }
}

struct DensityType(Arc<TerrainCatalog>);

const CLASSIC_VARIANTS: &str = "/miscellaneous/classicBiomeVariants";

struct ClassicMapperType(Arc<TerrainCatalog>);

impl BiomeMapperType for ClassicMapperType {
    fn decode(&self, config: &str) -> Result<Arc<dyn BiomeMapper>, String> {
        let settings: Value = serde_json::from_str(config).map_err(|err| err.to_string())?;
        let terrain = self.0.terrain(Some(&settings))?;
        let enabled = settings[CLASSIC_VARIANTS]
            .as_bool()
            .or_else(|| self.0.defaults.pointer(CLASSIC_VARIANTS)?.as_bool())
            .ok_or("missing TerraForged classic biome setting")?;
        Ok(Arc::new(ClassicMapper { terrain, enabled }))
    }
}

struct ClassicMapper {
    terrain: Arc<Terrain>,
    enabled: bool,
}

impl BiomeMapper for ClassicMapper {
    fn additional_biomes(&self) -> Vec<String> {
        if self.enabled {
            classic_biomes::VARIANTS.map(str::to_owned).into()
        } else {
            Vec::new()
        }
    }

    fn map(&self, base_biome: &str, [x, y, z]: [i32; 3], seed: i64) -> Result<Option<u16>, String> {
        if !self.enabled || y < 0 || !classic_biomes::eligible(base_biome) {
            return Ok(None);
        }
        let sampler = self.terrain.sampler(seed);
        let cell = sampler
            .sample(x.wrapping_mul(4), z.wrapping_mul(4))
            .map_err(|err| err.to_string())?;
        let terrain = sampler
            .heightmap()
            .terrains
            .get(cell.terrain)
            .ok_or("TerraForged biome terrain identity missing")?;
        let biome = classic_biomes::select(base_biome, &cell, terrain);
        if biome == base_biome {
            return Ok(None);
        }
        let index = classic_biomes::VARIANTS
            .iter()
            .position(|id| *id == biome)
            .ok_or("TerraForged selected an undeclared biome")?;
        Ok(Some(index as u16))
    }
}

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
            terrain: self.0.terrain(node.get("preset"))?,
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
        let terrain = Arc::new(TerrainCatalog::bundled().expect("bundled TerraForged inputs"));
        registrar.register_density_function_type("cell", DensityType(terrain.clone()));
        registrar.register_biome_mapper_type("classic", ClassicMapperType(terrain));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decoded_cell_matches_kernel_across_y_and_seed_switches() {
        let catalog = Arc::new(TerrainCatalog::bundled().unwrap());
        let terrain = catalog.bundled.clone();
        let density_type = DensityType(catalog);
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

    #[test]
    fn custom_presets_are_validated_and_distinct_for_the_same_seed() {
        let catalog = Arc::new(TerrainCatalog::bundled().unwrap());
        let density_type = DensityType(catalog.clone());
        for preset in [
            r#"null"#,
            r#"{"unknown":true}"#,
            r#"{"/world/continent/continentScale":200}"#,
            r#"{"/world/continent/continentScale":750.5}"#,
            r#"{"/miscellaneous/classicBiomeVariants":1}"#,
        ] {
            assert!(
                density_type
                    .decode(&format!(r#"{{"field":"height","preset":{preset}}}"#))
                    .is_err()
            );
        }
        let overrides = serde_json::json!({"/world/continent/continentScale": 500});
        let edited = catalog.terrain(Some(&overrides)).unwrap();
        assert!(Arc::ptr_eq(
            &edited,
            &catalog.terrain(Some(&overrides)).unwrap()
        ));
        assert!(!Arc::ptr_eq(&edited, &catalog.terrain(None).unwrap()));
        let default = density_type.decode(r#"{"field":"continent"}"#).unwrap();
        let custom = density_type
            .decode(&format!(r#"{{"field":"continent","preset":{overrides}}}"#))
            .unwrap();
        let point = [341, 100, -590];
        let seed = 42;
        let expected = CellDensity {
            terrain: edited.clone(),
            field: CellField::Continent,
            quantize_height: false,
        };
        assert_eq!(
            custom.sample(point, seed).to_bits(),
            expected
                .column(&edited.sampler(seed), point[0], point[2])
                .to_bits()
        );
        assert_ne!(
            default.sample(point, seed).to_bits(),
            custom.sample(point, seed).to_bits()
        );
    }

    #[test]
    fn classic_biome_policy_uses_the_world_configuration() {
        let catalog = Arc::new(TerrainCatalog::bundled().unwrap());
        let mapper_type = ClassicMapperType(catalog);
        let enabled = mapper_type.decode("{}").unwrap();
        let disabled = mapper_type
            .decode(r#"{"/miscellaneous/classicBiomeVariants":false}"#)
            .unwrap();
        assert_eq!(enabled.additional_biomes(), classic_biomes::VARIANTS);
        assert!(disabled.additional_biomes().is_empty());
        assert!(
            mapper_type
                .decode(r#"{"/miscellaneous/classicBiomeVariants":2}"#)
                .is_err()
        );
        let seed = 42;
        // Test the base biome's override policy with real TerraForged cells.
        for x in (0..128).step_by(8) {
            let quart = [x, 10, 0];
            assert_eq!(
                disabled.map("minecraft:badlands", quart, seed).unwrap(),
                None
            );
            assert_eq!(
                enabled.map("minecraft:badlands", [x, -1, 0], seed).unwrap(),
                None
            );
            assert_eq!(enabled.map("minecraft:ocean", quart, seed).unwrap(), None);
            if enabled
                .map("minecraft:badlands", quart, seed)
                .unwrap()
                .is_some()
            {
                return;
            }
        }
        panic!("fixture needs a mapped badlands biome");
    }
}
