//! Original swamp-surface material noise and Java double-literal comparisons.
//! Adapted from MIT ReTerraForged SwampSurfaceFeature; see LICENSE-RETERRAFORGED.
use crate::{
    graph::{GraphError, Noise},
    noises,
};
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Material {
    Clay,
    Gravel,
    Dirt,
}
impl Material {
    pub fn id(self) -> &'static str {
        match self {
            Self::Clay => "minecraft:clay",
            Self::Gravel => "minecraft:gravel",
            Self::Dirt => "minecraft:dirt",
        }
    }
}
#[derive(Clone, Debug)]
pub struct MarshSampler {
    material: Noise,
}
impl MarshSampler {
    pub fn new() -> Result<Self, GraphError> {
        Ok(Self {
            material: noises::warp_white(noises::simplex(23, 40, 2)?, 213, 2, 4.0)?,
        })
    }
    pub fn value(&self, x: i32, z: i32) -> f32 {
        self.material.compute(x as f32, z as f32, 0)
    }
    pub fn material(&self, x: i32, y: i32, z: i32, water_y: i32) -> Material {
        Self::select(self.value(x, z), y, water_y)
    }
    pub fn select(value: f32, y: i32, water_y: i32) -> Material {
        // Java promotes the float operand for the source's 0.6/0.75 double literals.
        if f64::from(value) > 0.6 {
            if f64::from(value) < 0.75 && y < water_y {
                Material::Clay
            } else {
                Material::Gravel
            }
        } else {
            Material::Dirt
        }
    }
}
