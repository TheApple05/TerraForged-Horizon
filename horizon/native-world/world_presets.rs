// Native preset metadata only. Generator owners stay in the constructed world.
use super::{
    Tag,
    custom_presets::{
        self, CustomPreset, CustomPresetEditor, PresetSetting, RegisteredPreset, SettingKind,
    },
};
use horizon_core::density::terraforged_runtime::kernel::{self, preset_editor};
use std::sync::OnceLock;
fn string(value: &str) -> Tag {
    Tag::String(value.into())
}
fn overworld() -> Result<Tag, String> {
    Ok(Tag::compound([
        ("type", string("minecraft:overworld")),
        (
            "generator",
            Tag::compound([
                ("type", string("minecraft:noise")),
                ("settings", string("terraforged:overworld")),
                (
                    "biome_source",
                    Tag::compound([
                        ("type", string("minecraft:multi_noise")),
                        ("preset", string("minecraft:overworld")),
                    ]),
                ),
            ]),
        ),
    ]))
}
fn recognizes(generator: &Tag) -> bool {
    generator.get("type") == Some(&string("minecraft:noise"))
        && (generator.get("settings") == Some(&string("terraforged:overworld"))
            || generator.get("settings") == Some(&string(preset_editor::SETTINGS_ID)))
}
fn defaults() -> Result<serde_json::Value, String> {
    serde_json::from_str(kernel::builtin_preset_json()).map_err(|e| e.to_string())
}
fn fields() -> Vec<PresetSetting> {
    preset_editor::FIELDS
        .iter()
        .map(|field| PresetSetting {
            path: field.path,
            label: field.label,
            kind: match field.kind {
                preset_editor::Kind::Boolean => SettingKind::Boolean,
                preset_editor::Kind::Number {
                    min,
                    max,
                    step,
                    integer,
                } => SettingKind::Number {
                    min,
                    max,
                    step,
                    integer,
                },
            },
        })
        .collect()
}
fn customized(value: &serde_json::Value) -> Result<Tag, String> {
    preset_editor::validate(value, &defaults()?)?;
    let mut stem = overworld()?;
    let Some(Tag::Compound(generator)) = stem.get_mut("generator") else {
        return Err("Native generator missing".into());
    };
    // Old 0.1.0 rejects this unknown settings ID instead of generating default-terrain seams.
    generator.insert("settings".into(), string(preset_editor::SETTINGS_ID));
    generator.insert(preset_editor::DATA_KEY.into(), string(&value.to_string()));
    Ok(stem)
}
fn settings(stem: &Tag) -> Result<Option<serde_json::Value>, String> {
    let generator = stem.get("generator").ok_or("Native generator missing")?;
    if generator.get("settings") == Some(&string("terraforged:overworld")) {
        if generator.get(preset_editor::DATA_KEY).is_some() {
            return Err("Custom settings require the customized generator ID".into());
        }
        return Ok(None);
    }
    if generator.get("settings") != Some(&string(preset_editor::SETTINGS_ID)) {
        return Err("Unknown TerraForged generator".into());
    }
    let Some(Tag::String(text)) = generator.get(preset_editor::DATA_KEY) else {
        return Err("Saved TerraForged custom preset is missing".into());
    };
    let text = text
        .to_string()
        .map_err(|e| format!("Invalid saved preset string: {e}"))?;
    preset_editor::decode(&text, &defaults()?).map(Some)
}
pub fn register() {
    static REGISTERED: OnceLock<Result<RegisteredPreset, String>> = OnceLock::new();
    if let Err(error) = REGISTERED.get_or_init(|| {
        let preset = custom_presets::register(CustomPreset {
            id: "terraforged:default",
            label: "generator.terraforged.default",
            overworld,
            recognizes,
        })?;
        custom_presets::register_editor(
            preset,
            CustomPresetEditor {
                fields,
                defaults,
                overworld: customized,
                settings,
            },
        )?;
        Ok(preset)
    }) {
        panic!("TerraForged preset registration failed: {error}");
    }
}
