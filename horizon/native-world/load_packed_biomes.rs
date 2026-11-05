fn terraforged_load_packed_biomes(
    world_root: &std::path::Path,
    resources: &std::path::Path,
    base: &std::sync::Arc<horizon_client::biome::Biomes>,
    enabled_features: &[String],
) -> std::ops::ControlFlow<Arc<horizon_client::biome::Biomes>> {
    match crate::game::terraforged_biome_packs::maybe_packed(world_root, resources, base, enabled_features) {
        Some(result) => std::ops::ControlFlow::Break(result),
        None => std::ops::ControlFlow::Continue(()),
    }
}
