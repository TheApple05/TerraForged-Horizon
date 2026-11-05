fn terraforged_load_biome_resources(
    dir: &std::path::Path,
    registry: &'static BlockRegistry,
    overrides: &WorldgenOverrides,
) -> std::ops::ControlFlow<Result<Arc<GeneratorData>, GeneratorError>> {
    match terraforged_resources::maybe_load(dir, registry, overrides) {
        Some(result) => std::ops::ControlFlow::Break(result),
        None => std::ops::ControlFlow::Continue(()),
    }
}
