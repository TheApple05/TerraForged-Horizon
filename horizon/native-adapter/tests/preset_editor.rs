use serde_json::Value;
use terraforged_native_adapter::preset_editor::*;
fn defaults() -> Value {
    serde_json::from_str(include_str!("../../tests/fixtures/kernel-v1/preset.json")).unwrap()
}
#[test]
fn settings_roundtrip_and_hidden_fields_are_preserved() {
    let original = defaults();
    let mut edited = original.clone();
    edited["terrain"]["general"]["globalVerticalScale"] = serde_json::json!(0.42);
    edited["climate"]["biomeShape"]["biomeSize"] = serde_json::json!(750);
    validate(&edited, &original).unwrap();
    assert_eq!(decode(&edited.to_string(), &original).unwrap(), edited);
    assert_eq!(edited["caves"], original["caves"]);
    edited["world"]["properties"]["seaLevel"] = serde_json::json!(100);
    assert!(validate(&edited, &original).is_err());
}
#[test]
fn malformed_missing_wrong_types_and_outside_ranges_refuse() {
    let original = defaults();
    validate(&original, &original).unwrap();
    for replacement in [
        serde_json::json!(0),
        serde_json::json!(10001),
        serde_json::json!(750.5),
        serde_json::json!("750"),
        Value::Null,
    ] {
        let mut value = original.clone();
        value["world"]["continent"]["continentScale"] = replacement;
        assert!(validate(&value, &original).is_err());
    }
    assert!(decode("{", &original).is_err());
    assert!(decode(&" ".repeat(MAX_BYTES + 1), &original).is_err());
    let mut value = original.clone();
    value["extra"] = Value::Bool(true);
    assert!(validate(&value, &original).is_err());
}

#[test]
fn exposed_bounds_construct_native_generators_and_keep_finite_terrain() {
    use terraforged_native_adapter::{noise_registry::NoiseRegistry, preset::CellPresetInput};
    use terraforged_native_core::{
        cell::Cell,
        kernel_sampler::{KernelSampler, SamplerOptions},
    };
    let original = defaults();
    let noises = NoiseRegistry::from_json(include_str!(
        "../../tests/fixtures/kernel-v1/noise-registry.json"
    ))
    .unwrap();
    let mut cases = Vec::new();
    for field in FIELDS {
        let choices = match field.kind {
            Kind::Boolean => vec![Value::Bool(false), Value::Bool(true)],
            Kind::Number {
                min, max, integer, ..
            } => [min, max]
                .map(|n| {
                    if integer {
                        Value::from(n as i64)
                    } else {
                        Value::from(n)
                    }
                })
                .to_vec(),
        };
        for choice in choices {
            let mut value = original.clone();
            *value.pointer_mut(field.path).unwrap() = choice;
            cases.push((field.path.to_owned(), value));
        }
    }
    for upper in [false, true] {
        let mut value = original.clone();
        for field in FIELDS {
            *value.pointer_mut(field.path).unwrap() = match field.kind {
                Kind::Boolean => Value::Bool(upper),
                Kind::Number {
                    min, max, integer, ..
                } => {
                    let number = if upper { max } else { min };
                    if integer {
                        Value::from(number as i64)
                    } else {
                        Value::from(number)
                    }
                }
            };
        }
        cases.push((format!("combined bounds {upper}"), value));
    }
    for (label, value) in cases {
        validate(&value, &original).unwrap();
        let preset = CellPresetInput::from_json(&value.to_string())
            .unwrap()
            .kernel;
        let sampler = KernelSampler::new(
            &preset,
            8675309,
            noises.get("reterraforged:terrain/ground").unwrap(),
            noises
                .get("reterraforged:climate/biome_edge_shape")
                .unwrap(),
            SamplerOptions::for_preset(&preset),
        )
        .unwrap();
        for (x, z) in [(8.0, 8.0), (417800.0, -626680.0)] {
            let mut cell = Cell::default();
            sampler.heightmap().apply(&mut cell, x, z, true).unwrap();
            assert!(cell.height.is_finite(), "{label}");
        }
    }
}
