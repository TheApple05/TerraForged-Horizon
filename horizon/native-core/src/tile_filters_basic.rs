//! MIT ReTerraForged modifiers, in-place smoothing and steepness.
use crate::{
    cell::Cell,
    graph::{GraphError, java_max, java_min},
    layout::Levels,
    noise_util as u,
    preset::SmoothingSettings,
    terrain::TerrainRegistry,
    tile::TileBuffer,
};

#[derive(Clone, Copy, Debug)]
pub struct Modifier {
    min: f32,
    max: f32,
    range: f32,
    inversions: usize,
}

impl Modifier {
    pub fn range(min: f32, max: f32) -> Self {
        Self {
            min,
            max,
            range: max - min,
            inversions: 0,
        }
    }

    pub fn invert(self) -> Self {
        Self {
            min: self.min,
            max: self.max,
            range: self.range,
            inversions: self.inversions + 1,
        }
    }

    pub fn value(&self, value: f32) -> f32 {
        let mut raw = if value > self.max {
            1.0
        } else if value < self.min {
            0.0
        } else {
            (value - self.min) / self.range
        };
        for _ in 0..self.inversions {
            raw = 1.0 - raw;
        }
        raw
    }

    pub fn modify(
        &self,
        cell: &Cell,
        value: f32,
        terrains: &TerrainRegistry,
    ) -> Result<f32, GraphError> {
        let terrain = terrains
            .get(cell.terrain)
            .ok_or(GraphError::InvalidSourceParameters(
                "owned filter terrain ID",
            ))?;
        let mut strength_modifier = 1.0;
        let erosion_modifier = terrain.erosion_modifier();
        if erosion_modifier != 1.0 {
            let alpha = u::map_clamped_range(cell.terrain_region_edge, 0.0, 0.15, 0.15);
            strength_modifier = u::lerp_f32(1.0, erosion_modifier, alpha);
        }
        if cell.river_mask < 0.1 {
            strength_modifier *= u::map_clamped_range(cell.river_mask, 0.002, 0.1, 0.098);
        }
        Ok(self.value(cell.height) * strength_modifier * value)
    }
}

#[derive(Clone, Debug)]
pub struct Smoothing {
    smoothing_radius: f32,
    smoothing_rate: f32,
    modifier: Modifier,
}

impl Smoothing {
    pub fn new(settings: SmoothingSettings, levels: Levels) -> Self {
        Self {
            smoothing_radius: settings.smoothing_radius,
            smoothing_rate: settings.smoothing_rate,
            modifier: Modifier::range(levels.ground(1), levels.ground(120)).invert(),
        }
    }

    pub fn apply(
        &self,
        tile: &mut TileBuffer,
        iterations: i32,
        terrains: &TerrainRegistry,
    ) -> Result<(), GraphError> {
        let mut remaining = iterations;
        while remaining > 0 {
            remaining -= 1;
            self.apply_once(tile, terrains)?;
        }
        Ok(())
    }

    fn apply_once(
        &self,
        tile: &mut TileBuffer,
        terrains: &TerrainRegistry,
    ) -> Result<(), GraphError> {
        let radius = u::round_legacy(self.smoothing_radius + 0.5);
        let radius_sq = self.smoothing_radius * self.smoothing_radius;

        let total = tile.size.total;
        if !self.smoothing_radius.is_finite()
            || self.smoothing_radius <= 0.0
            || radius >= total - radius
        {
            return Ok(());
        }
        let max_z = total - radius;
        let max_x = total - radius;
        let mut neighbours = Vec::new();
        let mut weights = 0.0;
        for dz in -radius..=radius {
            for dx in -radius..=radius {
                let dist2 = (dx * dx + dz * dz) as f32;
                if dist2 <= radius_sq {
                    let weight = 1.0 - dist2 / radius_sq;
                    neighbours.push(((dz * total + dx) as isize, weight));
                    weights += weight;
                }
            }
        }

        let mut z = radius;
        while z < max_z {
            let mut x = radius;
            while x < max_x {
                let idx = (z * total + x) as usize;
                let cell = tile.cells[idx];
                if !cell.erosion_mask {
                    let mut total_weighted = 0.0;
                    // Interior traversal keeps every offset in bounds; preserve dz/dx sum order.
                    for &(offset, weight) in &neighbours {
                        total_weighted +=
                            tile.cells[(idx as isize + offset) as usize].height * weight;
                    }
                    if weights > 0.0 {
                        let dif = cell.height - total_weighted / weights;
                        let amount =
                            self.modifier
                                .modify(&cell, dif * self.smoothing_rate, terrains)?;
                        let cell_mut = &mut tile.cells[idx];
                        cell_mut.height -= amount;
                    }
                }
                x += 1;
            }
            z += 1;
        }
        Ok(())
    }
}

#[derive(Clone, Debug)]
pub struct Steepness {
    radius: i32,
    scaler: f32,
    water_level: f32,
}

impl Steepness {
    pub fn new(radius: i32, scaler: f32, levels: Levels) -> Self {
        Self {
            radius,
            scaler,
            water_level: levels.water,
        }
    }

    pub fn apply(&self, tile: &mut TileBuffer) {
        let total = tile.size.total;
        let mut z = 0;
        while z < total {
            let mut x = 0;
            while x < total {
                if let Some(idx) = tile.raw_index(x, z) {
                    let cell = tile.cells[idx];
                    let mut total_height_dif = 0.0;
                    let mut dz = -1;
                    while dz <= 2 {
                        let mut dx = -1;
                        while dx <= 2 {
                            if dx != 0 || dz != 0 {
                                let nx = x + dx * self.radius;
                                let nz = z + dz * self.radius;
                                if let Some(neighbour) = tile.get_raw(nx, nz) {
                                    let height = java_max(neighbour.height, self.water_level);
                                    total_height_dif +=
                                        (cell.height - height).abs() / self.radius as f32;
                                }
                            }
                            dx += 1;
                        }
                        dz += 1;
                    }
                    tile.cells[idx].gradient = java_min(1.0, total_height_dif * self.scaler);
                }
                x += 1;
            }
            z += 1;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn original_smoothing_once(
        smoothing: &Smoothing,
        tile: &mut TileBuffer,
        terrains: &TerrainRegistry,
    ) -> Result<(), GraphError> {
        let radius = u::round_legacy(smoothing.smoothing_radius + 0.5);
        let radius_sq = smoothing.smoothing_radius * smoothing.smoothing_radius;
        let total = tile.size.total;
        for z in radius..total - radius {
            for x in radius..total - radius {
                let Some(index) = tile.raw_index(x, z) else {
                    continue;
                };
                let cell = tile.cells[index];
                if cell.erosion_mask {
                    continue;
                }
                let mut total_weighted = 0.0;
                let mut weights = 0.0;
                for dz in -radius..=radius {
                    for dx in -radius..=radius {
                        let dist2 = (dx * dx + dz * dz) as f32;
                        if dist2 <= radius_sq
                            && let Some(neighbour) = tile.get_raw(x + dx, z + dz)
                        {
                            let weight = 1.0 - dist2 / radius_sq;
                            total_weighted += neighbour.height * weight;
                            weights += weight;
                        }
                    }
                }
                if weights > 0.0 {
                    let dif = cell.height - total_weighted / weights;
                    let amount = smoothing.modifier.modify(
                        &cell,
                        dif * smoothing.smoothing_rate,
                        terrains,
                    )?;
                    tile.cells[index].height -= amount;
                }
            }
        }
        Ok(())
    }

    #[test]
    fn smoothing_matches_original_bits_for_radii_masks_and_tile_borders() {
        let terrains = TerrainRegistry::new();
        for (factor, border) in [(0, 0), (1, 0), (0, 1)] {
            for radius in [0.0, 1.8, 3.0, 8.0] {
                let smoothing = Smoothing::new(
                    SmoothingSettings {
                        iterations: 3,
                        smoothing_radius: radius,
                        smoothing_rate: 0.75,
                    },
                    Levels::new(384, 63),
                );
                let mut original = TileBuffer::new(-1, 2, factor, border).unwrap();
                for (index, cell) in original.cells.iter_mut().enumerate() {
                    cell.height = (index * 37 % 101) as f32 / 125.0 + 0.05;
                    cell.terrain = if index % 3 == 0 { 9 } else { 8 };
                    cell.terrain_region_edge = (index % 17) as f32 / 32.0;
                    cell.river_mask = (index % 13) as f32 / 32.0;
                    cell.erosion_mask = index % 7 == 0;
                }
                let mut optimized = original.clone();
                for _ in 0..3 {
                    original_smoothing_once(&smoothing, &mut original, &terrains).unwrap();
                }
                smoothing.apply(&mut optimized, 3, &terrains).unwrap();
                for (index, (expected, actual)) in
                    original.cells.iter().zip(&optimized.cells).enumerate()
                {
                    assert_eq!(
                        actual.height.to_bits(),
                        expected.height.to_bits(),
                        "factor={factor} border={border} radius={radius} index={index}"
                    );
                }
            }
        }
    }

    #[test]
    fn smoothing_skips_nonfinite_and_oversized_radii() {
        let terrains = TerrainRegistry::new();
        for radius in [
            f32::NAN,
            f32::INFINITY,
            f32::NEG_INFINITY,
            f32::MAX,
            -f32::MAX,
            8.0,
        ] {
            let smoothing = Smoothing::new(
                SmoothingSettings {
                    iterations: 1,
                    smoothing_radius: radius,
                    smoothing_rate: 1.0,
                },
                Levels::new(384, 63),
            );
            let mut tile = TileBuffer::new(0, 0, 0, 0).unwrap();
            smoothing.apply(&mut tile, 1, &terrains).unwrap();
            assert!(tile.cells.iter().all(|cell| cell.height.to_bits() == 0));
        }
    }
}
