use serde_json::Value;
use std::{collections::BTreeMap, error::Error, fs::File, io::Read, path::Path};
use terraforged_native_adapter::{preset::CellPresetInput, router::default_router};

const PRESET: &str = include_str!("../../../tests/fixtures/kernel-v1/preset.json");
const STEMS: &str =
    include_str!("../../../native-content/data/terraforged/worldgen/world_preset/default.json");

fn registry(root: &Path, name: &str) -> Result<BTreeMap<String, String>, Box<dyn Error>> {
    const LIMIT: u64 = 16 << 20;
    let path = root.join("worldgen").join(name);
    let mut bytes = Vec::new();
    File::open(&path)?.take(LIMIT + 1).read_to_end(&mut bytes)?;
    if bytes.len() as u64 > LIMIT {
        return Err(format!("{} exceeds 16 MiB", path.display()).into());
    }
    Ok(serde_json::from_slice(&bytes)?)
}

fn stock_preset(root: &Path) -> Result<Value, Box<dyn Error>> {
    let preset = CellPresetInput::from_json(PRESET)?;
    let planner = default_router(&preset.kernel, &preset.original["caves"])?;
    let normal = registry(root, "world_presets.json")?;
    let normal: Value = serde_json::from_str(
        normal
            .get("minecraft:normal")
            .ok_or("Missing vanilla 26.3 normal preset")?,
    )?;
    let generator = &normal["dimensions"]["minecraft:overworld"]["generator"];
    if generator["type"] != "minecraft:noise" {
        return Err("Vanilla 26.3 Overworld template is not a noise generator".into());
    }
    let mut settings: Value = if let Some(id) = generator["settings"].as_str() {
        let settings = registry(root, "settings.json")?;
        serde_json::from_str(
            settings
                .get(id)
                .ok_or("Missing vanilla 26.3 Overworld noise settings")?,
        )?
    } else {
        generator["settings"].clone()
    };
    if settings["noise"]["min_y"].as_i64() != Some(-64)
        || settings["noise"]["height"].as_i64() != Some(384)
        || settings["sea_level"].as_i64() != Some(63)
    {
        return Err("Expected 26.3 Overworld bounds -64..320 and sea level 63".into());
    }
    settings["noise_router"] = planner.stock_router(&registry(root, "densities.json")?)?;
    settings["spawn_target"] = Value::Array(Vec::new());
    let mut stems: Value = serde_json::from_str(STEMS)?;
    stems["dimensions"]["minecraft:overworld"]["generator"]["settings"] = settings;
    Ok(stems)
}

fn main() -> Result<(), Box<dyn Error>> {
    let resources = std::env::args_os()
        .nth(1)
        .ok_or("Pass prepared Horizon 26.3 resources")?;
    serde_json::to_writer(
        std::io::stdout().lock(),
        &stock_preset(Path::new(&resources))?,
    )?;
    Ok(())
}
