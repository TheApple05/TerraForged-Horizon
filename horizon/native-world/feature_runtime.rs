// Source pillar/marsh placement. All retained samplers belong to this world.
use super::*;
use crate::{
    heightmap::HeightmapType,
    worldgen::{
        DecodeError,
        block_feature::FeatureBlockBindings,
        block_predicate::PredicateBlockResolver,
        external_feature::{ExternalFeature, ExternalFeatureDecoder, ExternalFeatureWorld},
        placement::PlacementQueryError,
    },
};
use horizon_core::density::terraforged_runtime::kernel::{
    classic_pillars, kernel_sampler::KernelSampler, marsh_sampler, pillar_sampler,
};
type Query<T> = Result<T, PlacementQueryError>;
fn graph_error(error: impl std::fmt::Debug) -> PlacementQueryError {
    PlacementQueryError::Failed(format!("TerraForged feature: {error:?}"))
}
fn state(blocks: &FeatureBlockBindings<'_>, name: &str) -> Result<BlockStateId, DecodeError> {
    blocks
        .registry()
        .default_state(name)
        .ok_or_else(|| DecodeError::Registry(format!("missing native feature material {name}")))
}
fn air(blocks: &FeatureBlockBindings<'_>) -> Result<[BlockStateId; 3], DecodeError> {
    Ok([
        state(blocks, "minecraft:air")?,
        state(blocks, "minecraft:cave_air")?,
        state(blocks, "minecraft:void_air")?,
    ])
}
#[derive(Debug)]
pub struct NativeFeatureDecoder {
    kernel: Arc<KernelSampler>,
    pillars: Arc<pillar_sampler::PillarSampler>,
    marsh: Arc<marsh_sampler::MarshSampler>,
    seed: i32,
    enabled: bool,
}
impl NativeFeatureDecoder {
    pub fn new(
        kernel: Arc<KernelSampler>,
        seed: i64,
        enabled: bool,
    ) -> Result<Self, GeneratorError> {
        Ok(Self {
            kernel,
            pillars: Arc::new(
                pillar_sampler::PillarSampler::new(seed as i32)
                    .map_err(|e| resource(format!("native pillar sampler: {e:?}")))?,
            ),
            marsh: Arc::new(
                marsh_sampler::MarshSampler::new()
                    .map_err(|e| resource(format!("native marsh sampler: {e:?}")))?,
            ),
            seed: seed as i32,
            enabled,
        })
    }
}
impl ExternalFeatureDecoder for NativeFeatureDecoder {
    fn decode(
        &self,
        kind: &str,
        json: &str,
        blocks: &FeatureBlockBindings<'_>,
    ) -> Option<Result<Arc<dyn ExternalFeature>, DecodeError>> {
        match kind {
            "reterraforged:classic_pillar" => Some((|| {
                let value: Value = serde_json::from_str(json)?;
                let stone = value["stone_forest"]
                    .as_bool()
                    .ok_or(DecodeError::Field("stone_forest"))?;
                use pillar_sampler::Material as M;
                let mut materials = [BlockStateId(0); 9];
                for (i, material) in [
                    M::Orange,
                    M::Terracotta,
                    M::Brown,
                    M::Yellow,
                    M::White,
                    M::LightGray,
                    M::Stone,
                    M::Dirt,
                    M::Grass,
                ]
                .into_iter()
                .enumerate()
                {
                    materials[i] = state(blocks, material.id())?;
                }
                Ok(Arc::new(Pillars {
                    kernel: self.kernel.clone(),
                    sampler: self.pillars.clone(),
                    seed: self.seed,
                    enabled: self.enabled,
                    stone,
                    materials,
                    air: air(blocks)?,
                }) as Arc<dyn ExternalFeature>)
            })()),
            "reterraforged:swamp_surface" => Some((|| {
                let value: Value = serde_json::from_str(json)?;
                let material = |key| blocks.predicate_state(&value[key].to_string());
                Ok(Arc::new(Marsh {
                    sampler: self.marsh.clone(),
                    air: air(blocks)?,
                    clay: material("clay_material")?,
                    gravel: material("gravel_material")?,
                    dirt: material("dirt_material")?,
                }) as Arc<dyn ExternalFeature>)
            })()),
            _ => None,
        }
    }
}
#[derive(Debug)]
struct Pillars {
    kernel: Arc<KernelSampler>,
    sampler: Arc<pillar_sampler::PillarSampler>,
    seed: i32,
    enabled: bool,
    stone: bool,
    materials: [BlockStateId; 9],
    air: [BlockStateId; 3],
}
impl Pillars {
    fn boundary(
        &self,
        world: &mut dyn ExternalFeatureWorld,
        x: i32,
        y: i32,
        z: i32,
        name: &str,
    ) -> Query<f32> {
        for distance in [4, 8, 12, 16] {
            for (x, z) in [
                (x.wrapping_add(distance), z),
                (x.wrapping_sub(distance), z),
                (x, z.wrapping_add(distance)),
                (x, z.wrapping_sub(distance)),
            ] {
                if !world.noise_biome_is([x >> 2, y >> 2, z >> 2], name)? {
                    return Ok(distance as f32 / 16.0);
                }
            }
        }
        Ok(1.0)
    }
}
impl ExternalFeature for Pillars {
    fn place(&self, world: &mut dyn ExternalFeatureWorld, origin: [i32; 3]) -> Query<bool> {
        if !self.enabled {
            return Ok(false);
        }
        if world.world_seed()? as i32 != self.seed {
            return Err(PlacementQueryError::Failed(
                "native pillar owner belongs to another seed".into(),
            ));
        }
        let (base_x, base_z) = (origin[0] & !15, origin[2] & !15);
        let (sea, max_y) = (world.sea_level()?, world.max_y()?);
        let name = if self.stone {
            "reterraforged:stone_forest"
        } else {
            "reterraforged:bryce"
        };
        let mut changed = false;
        for dz in 0..16 {
            for dx in 0..16 {
                let (x, z) = (base_x.wrapping_add(dx), base_z.wrapping_add(dz));
                // PlacementContext returns first available Y; ChunkAccess.getHeight
                // in the source returns the highest taken block, one below that.
                let surface = world
                    .height(HeightmapType::OceanFloor, x, z)?
                    .wrapping_sub(1);
                if surface <= sea || surface >= max_y {
                    continue;
                }
                let pos = [x, surface, z];
                let mut base_allowed = false;
                for tag in [
                    "minecraft:grass_blocks",
                    "minecraft:base_stone_overworld",
                    "minecraft:dirt",
                    "minecraft:sand",
                    "minecraft:terracotta",
                ] {
                    if world.block_matches_tag(pos, tag)? {
                        base_allowed = true;
                        break;
                    }
                }
                if !base_allowed || !world.noise_biome_is([x >> 2, surface >> 2, z >> 2], name)? {
                    continue;
                }
                let cell = self.kernel.sample(x, z).map_err(graph_error)?;
                let mask =
                    classic_pillars::mask(cell.biome_region_edge, cell.river_mask, cell.gradient)
                        * self.boundary(world, x, surface, z, name)?;
                let height = classic_pillars::added_height(
                    self.sampler.shape(x, z, self.stone),
                    mask,
                    self.stone,
                );
                let top = (surface + height).min(max_y);
                if top <= surface {
                    continue;
                }
                let mut empty = true;
                for y in surface + 1..=top {
                    if !self.air.contains(&world.block_state([x, y, z])?) {
                        empty = false;
                        break;
                    }
                }
                if !empty {
                    continue;
                }
                let palette = self
                    .sampler
                    .palette(pillar_sampler::PillarSampler::palette_index(
                        cell.biome_region_id,
                    ))
                    .ok_or_else(|| {
                        PlacementQueryError::Failed("native pillar palette index".into())
                    })?;
                let shift = if self.stone {
                    0
                } else {
                    self.sampler.band_shift(x, z)
                };
                for y in surface + 1..=top {
                    let material = if self.stone {
                        pillar_sampler::PillarSampler::stone_material(y - surface, top - surface)
                    } else {
                        palette
                            .at(y - surface + shift, height.max(1))
                            .map_err(graph_error)?
                    };
                    world.set_chunk_block([x, y, z], self.materials[material as usize])?;
                }
                changed = true;
            }
        }
        Ok(changed)
    }
}
#[derive(Debug)]
struct Marsh {
    sampler: Arc<marsh_sampler::MarshSampler>,
    air: [BlockStateId; 3],
    clay: BlockStateId,
    gravel: BlockStateId,
    dirt: BlockStateId,
}
impl Marsh {
    fn material(&self, x: i32, y: i32, z: i32, water_y: i32) -> BlockStateId {
        match self.sampler.material(x, y, z, water_y) {
            marsh_sampler::Material::Clay => self.clay,
            marsh_sampler::Material::Gravel => self.gravel,
            marsh_sampler::Material::Dirt => self.dirt,
        }
    }
}
impl ExternalFeature for Marsh {
    fn place(&self, world: &mut dyn ExternalFeatureWorld, origin: [i32; 3]) -> Query<bool> {
        let (base_x, base_z) = (origin[0] & !15, origin[2] & !15);
        let water_y = world.sea_level()?.wrapping_sub(1);
        let mut changed = false;
        for dx in 0..16 {
            for dz in 0..16 {
                let (x, z) = (base_x.wrapping_add(dx), base_z.wrapping_add(dz));
                let surface = world
                    .height(HeightmapType::WorldSurface, x, z)?
                    .wrapping_sub(1);
                let quart = [x >> 2, surface >> 2, z >> 2];
                if !world.noise_biome_is(quart, "minecraft:swamp")?
                    && !world.noise_biome_is(quart, "reterraforged:marshland")?
                {
                    continue;
                }
                let noise = crate::worldgen::biome_temperature::biome_info_noise_f64(
                    f64::from(x) * 0.25,
                    f64::from(z) * 0.25,
                );
                if noise > 0.0 {
                    for y in (surface - 10..=surface).rev() {
                        let pos = [x, y, z];
                        if self.air.contains(&world.block_state(pos)?) {
                            continue;
                        }
                        if y == water_y
                            && world.fluid_state(pos)?.kind() != crate::fluid::FluidKind::Empty
                        {
                            world.set_chunk_block(pos, self.material(x, water_y, z, water_y))?;
                            changed = true;
                        }
                        break;
                    }
                }
                let y = world
                    .height(HeightmapType::OceanFloorWg, x, z)?
                    .wrapping_sub(1);
                if y <= water_y {
                    world.set_chunk_block([x, y, z], self.material(x, y, z, water_y))?;
                    changed = true;
                }
            }
        }
        Ok(changed)
    }
}
