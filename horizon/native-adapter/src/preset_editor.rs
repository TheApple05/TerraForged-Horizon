//! Supported native controls. Hidden preset fields remain frozen to the bundled schema.
use serde_json::Value;

pub const MAX_BYTES: usize = 60 * 1024;
pub const SETTINGS_ID: &str = "terraforged:customized_v1";
pub const DATA_KEY: &str = "terraforged:preset";

#[derive(Clone, Copy, Debug)]
pub enum Kind {
    Number {
        min: f64,
        max: f64,
        step: f64,
        integer: bool,
    },
    Boolean,
}
#[derive(Clone, Copy, Debug)]
pub struct Field {
    pub path: &'static str,
    pub label: &'static str,
    pub kind: Kind,
}
macro_rules! number {
    ($path:literal, $label:literal, $min:expr, $max:expr, $step:expr, $integer:expr) => {
        Field {
            path: $path,
            label: concat!("terraforged.customize.", $label),
            kind: Kind::Number {
                min: $min,
                max: $max,
                step: $step,
                integer: $integer,
            },
        }
    };
}
// shortcut: expose qualified native controls only; extend this schema when more runtime settings are supported.
pub const FIELDS: &[Field] = &[
    number!(
        "/world/continent/continentScale",
        "continent_scale",
        500.0,
        10000.0,
        100.0,
        true
    ),
    number!(
        "/world/continent/continentJitter",
        "continent_jitter",
        0.1,
        1.0,
        0.05,
        false
    ),
    number!(
        "/terrain/general/terrainRegionSize",
        "terrain_regions",
        125.0,
        5000.0,
        25.0,
        true
    ),
    number!(
        "/terrain/general/globalVerticalScale",
        "vertical_scale",
        0.1,
        1.0,
        0.01,
        false
    ),
    number!(
        "/terrain/general/globalHorizontalScale",
        "horizontal_scale",
        0.25,
        5.0,
        0.05,
        false
    ),
    Field {
        path: "/terrain/general/fancyMountains",
        label: "terraforged.customize.fancy_mountains",
        kind: Kind::Boolean,
    },
    number!(
        "/terrain/steppe/weight",
        "steppe_weight",
        0.1,
        10.0,
        0.1,
        false
    ),
    number!(
        "/terrain/plains/weight",
        "plains_weight",
        0.1,
        10.0,
        0.1,
        false
    ),
    number!(
        "/terrain/hills/weight",
        "hills_weight",
        0.1,
        10.0,
        0.1,
        false
    ),
    number!(
        "/terrain/dales/weight",
        "dales_weight",
        0.1,
        10.0,
        0.1,
        false
    ),
    number!(
        "/terrain/plateau/weight",
        "plateau_weight",
        0.1,
        10.0,
        0.1,
        false
    ),
    number!(
        "/terrain/badlands/weight",
        "badlands_weight",
        0.1,
        10.0,
        0.1,
        false
    ),
    number!(
        "/terrain/torridonian/weight",
        "torridonian_weight",
        0.1,
        10.0,
        0.1,
        false
    ),
    number!(
        "/terrain/mountains/weight",
        "mountains_weight",
        0.1,
        10.0,
        0.1,
        false
    ),
    number!(
        "/terrain/volcano/weight",
        "volcano_weight",
        0.1,
        10.0,
        0.1,
        false
    ),
    number!(
        "/climate/biomeShape/biomeSize",
        "biome_size",
        50.0,
        2000.0,
        25.0,
        true
    ),
    number!(
        "/climate/biomeShape/macroNoiseSize",
        "macro_biomes",
        1.0,
        20.0,
        1.0,
        true
    ),
    number!(
        "/climate/biomeShape/biomeWarpScale",
        "biome_warp_scale",
        25.0,
        500.0,
        25.0,
        true
    ),
    number!(
        "/climate/biomeShape/biomeWarpStrength",
        "biome_warp_strength",
        0.0,
        250.0,
        5.0,
        true
    ),
    number!(
        "/climate/temperature/bias",
        "temperature_bias",
        -0.5,
        0.5,
        0.05,
        false
    ),
    number!(
        "/climate/moisture/bias",
        "moisture_bias",
        -0.5,
        0.5,
        0.05,
        false
    ),
    number!("/rivers/riverCount", "river_count", 0.0, 30.0, 1.0, true),
    number!(
        "/rivers/mainRivers/bedWidth",
        "main_river_width",
        1.0,
        20.0,
        1.0,
        true
    ),
    number!(
        "/rivers/branchRivers/bedWidth",
        "branch_river_width",
        1.0,
        20.0,
        1.0,
        true
    ),
    number!("/rivers/lakes/chance", "lake_chance", 0.0, 1.0, 0.05, false),
    number!(
        "/rivers/wetlands/chance",
        "wetland_chance",
        0.0,
        1.0,
        0.05,
        false
    ),
    number!(
        "/filters/smoothing/smoothingRate",
        "smoothing",
        0.0,
        1.0,
        0.05,
        false
    ),
    Field {
        path: "/miscellaneous/classicBiomeVariants",
        label: "terraforged.customize.classic_biomes",
        kind: Kind::Boolean,
    },
];

pub fn validate(value: &Value, defaults: &Value) -> Result<(), String> {
    if !value.is_object() || value.to_string().len() > MAX_BYTES {
        return Err("TerraForged custom settings must be an object of at most 60 KiB".into());
    }
    // Frozen kernel-v1 hidden fields belong to customized_v1; migrate before changing that schema.
    let mut expected = defaults.clone();
    for field in FIELDS {
        let entry = value
            .pointer(field.path)
            .ok_or_else(|| format!("Missing setting {}", field.path))?;
        let valid = match field.kind {
            Kind::Boolean => entry.is_boolean(),
            Kind::Number {
                min, max, integer, ..
            } => entry.as_f64().is_some_and(|n| {
                n.is_finite() && (min..=max).contains(&n) && (!integer || entry.as_i64().is_some())
            }),
        };
        if !valid {
            return Err(format!("Invalid or out-of-range setting {}", field.path));
        }
        *expected
            .pointer_mut(field.path)
            .ok_or_else(|| format!("Bundled setting missing {}", field.path))? = entry.clone();
    }
    // Reject unknown settings rather than accepting unsupported controls or unbounded work.
    if &expected != value {
        return Err("Unsupported or changed hidden TerraForged settings".into());
    }
    Ok(())
}

pub fn decode(text: &str, defaults: &Value) -> Result<Value, String> {
    if text.len() > MAX_BYTES {
        return Err("TerraForged custom settings exceed 60 KiB".into());
    }
    let value = serde_json::from_str(text)
        .map_err(|e| format!("Invalid TerraForged custom settings: {e}"))?;
    validate(&value, defaults)?;
    Ok(value)
}
