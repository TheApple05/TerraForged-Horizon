// Recompute per-world client metadata from exactly the enabled generation packs.
use horizon_client::biome::Biomes;
use std::{path::Path, sync::Arc};
fn build(
    world_root: &Path,
    resources: &Path,
    base: &Arc<Biomes>,
    enabled_features: &[String],
) -> Result<Arc<Biomes>, String> {
    let packs = horizon_client::datapack::discover_with_features(world_root, resources);
    let enabled = horizon_client::datapack::enabled_ids(world_root, &packs, enabled_features);
    let enabled: Vec<_> = enabled
        .iter()
        .filter_map(|id| packs.iter().find(|pack| &pack.id == id))
        .collect();
    let (overrides, _) = horizon_client::datapack::worldgen_overrides(&enabled, |_| true);
    let overrides = horizon_world::worldgen::generator::terraforged_resources::augment(
        &resources.join("worldgen"),
        &overrides,
    )
    .map_err(|error| error.to_string())?;
    let definitions = overrides
        .entries("biomes")
        .map(|(id, json)| {
            serde_json::from_str::<serde_json::Value>(json).map(|value| (id.to_owned(), value))
        })
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| error.to_string())?;
    Ok(Arc::new(base.with_packs(
        definitions.iter().map(|(id, value)| (id.as_str(), value)),
    )))
}
pub fn maybe_packed(
    world_root: &Path,
    resources: &Path,
    base: &Arc<Biomes>,
    enabled_features: &[String],
) -> Option<Arc<Biomes>> {
    match build(world_root, resources, base, enabled_features) {
        Ok(biomes) => Some(biomes),
        Err(error) => {
            // The generation-data hook rejects the same invalid definitions and
            // propagates the load error; do not crash the title/render thread.
            log::error!("TerraForged client biome metadata: {error}");
            None
        }
    }
}
