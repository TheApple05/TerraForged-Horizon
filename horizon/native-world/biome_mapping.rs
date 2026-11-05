// Parent lookup keeps its host tie/search state; only the qualified policy changes IDs.
use horizon_core::{
    density::SampleError,
    density::terraforged_runtime::kernel::{classic_biomes, kernel_sampler::KernelSampler},
};
use std::sync::Arc;
#[derive(Debug)]
pub struct ClassicMapper {
    sampler: Arc<KernelSampler>,
    enabled: bool,
    names: Vec<String>,
}
impl ClassicMapper {
    pub fn new(sampler: Arc<KernelSampler>, enabled: bool) -> Self {
        Self {
            sampler,
            enabled,
            names: classic_biomes::VARIANTS
                .iter()
                .map(|name| (*name).to_owned())
                .collect(),
        }
    }
}
impl crate::worldgen::biome_source::BiomeMapper for ClassicMapper {
    fn additional_biomes(&self) -> &[String] {
        &self.names
    }
    fn map<'a>(&'a self, parent: &'a str, quart: [i32; 3]) -> Result<&'a str, SampleError> {
        if !self.enabled || quart[1] < 0 || !classic_biomes::eligible(parent) {
            return Ok(parent);
        }
        let cell = self
            .sampler
            .sample(quart[0].wrapping_mul(4), quart[2].wrapping_mul(4))
            .map_err(|_| SampleError::External("TerraForged biome tile generation failed"))?;
        let terrain =
            self.sampler
                .heightmap()
                .terrains
                .get(cell.terrain)
                .ok_or(SampleError::External(
                    "TerraForged biome terrain identity missing",
                ))?;
        Ok(classic_biomes::select(parent, &cell, terrain))
    }
}
