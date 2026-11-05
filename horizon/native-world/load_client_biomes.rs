fn terraforged_load_client_biomes(root: &std::path::Path) -> std::ops::ControlFlow<Result<Biomes>> {
    match terraforged_client_biomes::maybe_load(root) {
        Some(result) => std::ops::ControlFlow::Break(result),
        None => std::ops::ControlFlow::Continue(()),
    }
}
