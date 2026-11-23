fn terraforged_open_world(
    data: &std::sync::Arc<GeneratorData>,
    seed: i64,
    preset: &str,
    dimension: &str,
    with_structures: bool,
    saved_stem: Option<&serde_json::Value>,
) -> std::ops::ControlFlow<Result<OverworldGenerator, GeneratorError>> {
    use horizon_core::density::terraforged_runtime::kernel;
    use kernel::preset_editor;
    if dimension != "minecraft:overworld" {
        return std::ops::ControlFlow::Continue(());
    }
    // Preserve the engine's precedence: a dimension override, saved stem, then
    // a newly selected preset. A saved vanilla world wins over a UI default.
    let dimension_stem: Option<serde_json::Value> = match data.dimensions.get(dimension) {
        Some(json) => match serde_json::from_str(json) {
            Ok(value) => Some(value),
            Err(error) => return std::ops::ControlFlow::Break(Err(error.into())),
        },
        None => None,
    };
    let stem = dimension_stem.as_ref().or(saved_stem);
    let selected = match stem {
        Some(stem) => matches!(
            stem["generator"]["settings"].as_str(),
            Some("terraforged:overworld" | preset_editor::SETTINGS_ID)
        ),
        None => preset == "terraforged:default",
    };
    if !selected {
        return std::ops::ControlFlow::Continue(());
    }
    if stem.is_some_and(|stem| stem["generator"]["type"].as_str() != Some("minecraft:noise")) {
        return std::ops::ControlFlow::Break(Err(resource(
            "TerraForged world stem is not a noise generator",
        )));
    }
    let preset_json = if stem
        .is_some_and(|s| s["generator"]["settings"].as_str() == Some(preset_editor::SETTINGS_ID))
    {
        let Some(text) = stem.and_then(|s| s["generator"][preset_editor::DATA_KEY].as_str()) else {
            return std::ops::ControlFlow::Break(Err(resource(
                "Saved TerraForged custom preset is missing or not a string",
            )));
        };
        let defaults = match serde_json::from_str(kernel::builtin_preset_json()) {
            Ok(value) => value,
            Err(error) => return std::ops::ControlFlow::Break(Err(error.into())),
        };
        if let Err(error) = preset_editor::decode(text, &defaults) {
            return std::ops::ControlFlow::Break(Err(resource(error)));
        }
        text
    } else {
        if stem.is_some_and(|s| s["generator"].get(preset_editor::DATA_KEY).is_some()) {
            return std::ops::ControlFlow::Break(Err(resource(
                "Custom settings require the customized generator ID",
            )));
        }
        kernel::builtin_preset_json()
    };
    std::ops::ControlFlow::Break(
        terraforged_world::open(
            data.clone(),
            seed,
            preset_json,
            kernel::builtin_noises_json(),
            with_structures,
        )
        .map(|opened| opened.generator),
    )
}
