//! MIT PresetNoiseRouterData formulas expressed in the 26.3 density schema.
//! Vanilla helper definitions are read from the player's resources at runtime.
use crate::noise_registry::{DecodeError, Result, float};
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};
use terraforged_native_core::preset::KernelPreset;

#[derive(Clone, Debug)]
pub struct RouterPlan {
    pub router: Value,
    pub definitions: BTreeMap<String, String>,
    aliases: Vec<(String, String)>,
}
impl RouterPlan {
    /// Derive a world-local registry. Never mutate GeneratorData's shared maps.
    pub fn materialize(&self, base: &BTreeMap<String, String>) -> Result<BTreeMap<String, String>> {
        let mut result = base.clone();
        for (alias, original) in &self.aliases {
            result.insert(
                alias.clone(),
                base.get(original)
                    .ok_or_else(|| {
                        DecodeError(format!("Required 26.3 density helper absent: {original}"))
                    })?
                    .clone(),
            );
        }
        result.extend(self.definitions.clone());
        Ok(result)
    }

    /// Keep altered density definitions inside the saved world's settings.
    /// Vanilla references with no dependency on an override stay shared.
    pub fn stock_router(&self, base: &BTreeMap<String, String>) -> Result<Value> {
        let densities = self
            .materialize(base)?
            .into_iter()
            .map(|(id, text)| {
                serde_json::from_str(&text)
                    .map(|value| (id.clone(), value))
                    .map_err(|error| DecodeError(format!("Density {id}: {error}")))
            })
            .collect::<Result<BTreeMap<_, _>>>()?;
        let mut local: BTreeSet<_> = self
            .definitions
            .keys()
            .chain(self.aliases.iter().map(|(name, _)| name))
            .map(String::as_str)
            .collect();
        let mut dependents = BTreeMap::<&str, Vec<&str>>::new();
        for (id, value) in &densities {
            visit_references(value, &mut |reference| {
                if densities.contains_key(reference) {
                    dependents.entry(reference).or_default().push(id);
                }
            });
        }
        let mut pending: Vec<_> = local.iter().copied().collect();
        while let Some(id) = pending.pop() {
            if let Some(inherited) = dependents.get(id) {
                for &id in inherited {
                    if local.insert(id) {
                        pending.push(id);
                    }
                }
            }
        }
        let mut router = self.router.clone();
        let mut remaining = 32_768;
        inline_density(&mut router, &densities, &local, 0, &mut remaining)?;
        Ok(router)
    }
}

fn visit_references<'a>(value: &'a Value, visit: &mut impl FnMut(&'a str)) {
    match value {
        Value::String(id) => visit(id),
        Value::Array(values) => {
            for value in values {
                visit_references(value, visit);
            }
        }
        Value::Object(fields) => {
            for (key, value) in fields {
                if density_field(key) {
                    visit_references(value, visit);
                }
            }
        }
        _ => {}
    }
}

fn density_field(key: &str) -> bool {
    !matches!(key, "type" | "noise")
}

fn inline_density(
    value: &mut Value,
    densities: &BTreeMap<String, Value>,
    local: &BTreeSet<&str>,
    depth: usize,
    remaining: &mut usize,
) -> Result<()> {
    if depth > 64 || *remaining == 0 {
        return Err(DecodeError(
            "Expanded stock density graph exceeds its limits".into(),
        ));
    }
    *remaining -= 1;
    if let Some(id) = value.as_str().filter(|id| local.contains(id)) {
        *value = densities[id].clone();
        return inline_density(value, densities, local, depth + 1, remaining);
    }
    match value {
        Value::Object(fields) => match fields.get("type").and_then(Value::as_str) {
            Some("reterraforged:cell") => {
                fields.insert("type".into(), json!("terraforged:cell"));
            }
            Some("reterraforged:clamp_to_nearest_unit") => {
                if fields.get("function").and_then(Value::as_str) != Some("terraforged:height") {
                    return Err(DecodeError(
                        "Stock quantization requires TerraForged height".into(),
                    ));
                }
                *value = json!({"type":"terraforged:cell","field":"height","quantize_height":true});
            }
            _ => {
                for (key, value) in fields {
                    if density_field(key) {
                        inline_density(value, densities, local, depth + 1, remaining)?;
                    }
                }
            }
        },
        Value::Array(values) => {
            for value in values {
                inline_density(value, densities, local, depth + 1, remaining)?;
            }
        }
        _ => {}
    }
    Ok(())
}
fn binary(kind: &str, left: Value, right: Value) -> Value {
    json!({"type":format!("minecraft:{kind}"),"left":left,"right":right})
}
fn unary(kind: &str, input: Value) -> Value {
    json!({"type":format!("minecraft:{kind}"),"input":input})
}
fn add(a: Value, b: Value) -> Value {
    binary("add", a, b)
}
fn mul(a: Value, b: Value) -> Value {
    binary("mul", a, b)
}
fn min(a: Value, b: Value) -> Value {
    binary("min", a, b)
}
fn max(a: Value, b: Value) -> Value {
    binary("max", a, b)
}
fn cell(field: &str) -> Value {
    json!({"type":"reterraforged:cell","field":field})
}
fn clamp(input: Value, low: f64, high: f64) -> Value {
    json!({"type":"minecraft:clamp","input":input,"min":low,"max":high})
}
fn gradient(from: i32, to: i32, low: f64, high: f64) -> Value {
    json!({"type":"minecraft:gradient","axis":"y","from_coordinate":from,"to_coordinate":to,"from_value":low,"to_value":high})
}
fn interpolated(input: Value, xz: i32, y: i32) -> Value {
    json!({"type":"minecraft:interpolated","cell_size_xz":xz,"cell_size_y":y,"input":input})
}
fn noise(name: &str, y: f64) -> Value {
    json!({"type":"minecraft:noise","noise":format!("minecraft:{name}"),"xz_scale":1.0,"y_scale":y})
}
fn choice(input: Value, upper: f64, inside: Value, outside: Value) -> Value {
    json!({"type":"minecraft:range_choice","input":input,"min_inclusive":-1000000.0,"max_exclusive":upper,"when_in_range":inside,"when_out_of_range":outside})
}
fn probability(p: f32, input: Value) -> Value {
    if p == 0.0 {
        json!(1.0)
    } else {
        add(json!((1.0_f32 - p) as f64), input)
    }
}
fn slide(input: Value) -> Value {
    json!({"type":"minecraft:lerp","alpha":gradient(-64,-40,0.0,1.0),"first":15.0/128.0,"second":input})
}

pub fn default_router(preset: &KernelPreset, caves: &Value) -> Result<RouterPlan> {
    // Broader numerical presets remain supported by the kernel. This first
    // world plan requires the current overworld's actual vertical envelope.
    let world = &preset.world.properties;
    if world.world_height != 320 || world.world_depth != 64 || world.sea_level != 63 {
        return Err(DecodeError(
            "Native world router currently requires height 320, depth 64, sea level 63".into(),
        ));
    }
    let entrance = float(caves, "entranceCaveProbability")?;
    let cheese = float(caves, "cheeseCaveProbability")?;
    let spaghetti = float(caves, "spaghettiCaveProbability")?;
    let noodle = float(caves, "noodleCaveProbability")?;
    let cheese_depth = float(caves, "cheeseCaveDepthOffset")?;
    if [entrance, cheese, spaghetti, noodle]
        .iter()
        .any(|p| !p.is_finite() || !(0.0..=1.0).contains(p))
        || !cheese_depth.is_finite()
    {
        return Err(DecodeError(
            "Finite native cave probabilities in [0,1] and finite depth required".into(),
        ));
    }
    if noodle != 1.0 {
        return Err(DecodeError(
            "Native world router currently requires default noodle probability 1".into(),
        ));
    }
    let mut plan = RouterPlan {
        router: Value::Null,
        definitions: BTreeMap::new(),
        aliases: Vec::new(),
    };
    let mut put = |name: &str, value: Value| {
        plan.definitions.insert(name.into(), value.to_string());
    };
    put("terraforged:height", cell("height"));
    for (name, field) in [
        ("continents", "continent"),
        ("erosion", "erosion"),
        ("ridges", "weirdness"),
    ] {
        put(&format!("minecraft:overworld/{name}"), cell(field));
    }
    let offset = add(
        json!((-0.50375_f32 - 0.5_f32) as f64),
        mul(
            json!({"type":"reterraforged:clamp_to_nearest_unit","function":"terraforged:height","resolution":world.terrain_scaler()}),
            json!(2.0),
        ),
    );
    put("minecraft:overworld/offset", offset);
    put(
        "minecraft:overworld/depth",
        add(
            gradient(-64, 320, 1.5, -1.5),
            json!("minecraft:overworld/offset"),
        ),
    );
    put("minecraft:overworld/base_3d_noise", json!(0.0));
    put(
        "minecraft:overworld/jaggedness",
        add(json!(0.0), json!(0.0)),
    );
    let source_entrances = "terraforged:source/caves/entrances";
    let source_spaghetti = "terraforged:source/caves/spaghetti_2d";
    put(
        "minecraft:overworld/caves/entrances",
        probability(entrance, json!(source_entrances)),
    );
    put(
        "minecraft:overworld/caves/spaghetti_2d",
        probability(spaghetti, json!(source_spaghetti)),
    );
    plan.aliases.push((
        source_entrances.into(),
        "minecraft:overworld/caves/entrances".into(),
    ));
    plan.aliases.push((
        source_spaghetti.into(),
        "minecraft:overworld/caves/spaghetti_2d".into(),
    ));
    let sloped = json!("minecraft:overworld/sloped_cheese");
    let cave_layer = mul(json!(4.0), unary("square", noise("cave_layer", 8.0)));
    let sloped_caves = add(
        clamp(
            add(
                json!(0.27),
                probability(cheese, noise("cave_cheese", 2.0 / 3.0)),
            ),
            -1.0,
            1.0,
        ),
        clamp(add(json!(1.5), mul(json!(-0.64), sloped.clone())), 0.0, 0.5),
    );
    let underground = min(
        min(
            add(cave_layer, sloped_caves),
            json!("minecraft:overworld/caves/entrances"),
        ),
        add(
            json!("minecraft:overworld/caves/spaghetti_2d"),
            json!("minecraft:overworld/caves/spaghetti_roughness_function"),
        ),
    );
    let underground = max(
        underground,
        choice(
            json!("minecraft:overworld/caves/pillars"),
            0.03,
            json!(-1000000.0),
            json!("minecraft:overworld/caves/pillars"),
        ),
    );
    let entrances = if entrance > 0.0 {
        min(
            sloped.clone(),
            mul(
                json!(5.0),
                interpolated(json!("minecraft:overworld/caves/entrances"), 4, 8),
            ),
        )
    } else {
        sloped.clone()
    };
    let final_density = min(
        unary(
            "squeeze",
            mul(
                choice(
                    sloped.clone(),
                    cheese_depth as f64,
                    entrances,
                    interpolated(slide(underground), 4, 8),
                ),
                json!(0.64),
            ),
        ),
        json!("minecraft:overworld/caves/noodle"),
    );
    // 26.3 makes the structure field an explicit router input.
    let final_density = add(final_density, json!({"type":"minecraft:beardifier"}));
    let initial = mul(
        json!(4.0),
        unary(
            "quarter_negative",
            mul(
                json!("minecraft:overworld/depth"),
                unary("cache", json!("minecraft:overworld/factor")),
            ),
        ),
    );
    let preliminary = slide(clamp(add(initial, json!(-90.0 / 128.0)), -64.0, 64.0));
    let surface = json!({"type":"minecraft:find_top_surface","density":add(preliminary,json!(-0.390625)),"lower_bound":-64,"upper_bound":320.0,"cell_height":8});
    plan.router = json!({"temperature":cell("temperature"),"vegetation":cell("moisture"),"continents":"minecraft:overworld/continents","erosion":"minecraft:overworld/erosion","depth":add(json!("minecraft:overworld/depth"),json!(-0.275)),"ridges":"minecraft:overworld/ridges","chunk_surface_level":interpolated(surface,16,1),"final_density":final_density});
    Ok(plan)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stock_router_inlines_local_overrides_and_keeps_vanilla_dependencies() {
        let base = BTreeMap::from([
            (
                "minecraft:inherited".into(),
                r#"{"type":"minecraft:min","left":"minecraft:overridden","right":"minecraft:unchanged"}"#.into(),
            ),
            ("minecraft:overridden".into(), "0.25".into()),
            ("minecraft:unchanged".into(), "0.5".into()),
        ]);
        let plan = RouterPlan {
            router: json!({"final_density":"minecraft:inherited","temperature":"terraforged:quantized"}),
            definitions: BTreeMap::from([
                (
                    "minecraft:overridden".into(),
                    add(cell("height"), json!("terraforged:original")).to_string(),
                ),
                (
                    "terraforged:quantized".into(),
                    json!({"type":"reterraforged:clamp_to_nearest_unit","function":"terraforged:height","resolution":256}).to_string(),
                ),
            ]),
            aliases: vec![("terraforged:original".into(), "minecraft:overridden".into())],
        };
        assert_eq!(
            plan.stock_router(&base).unwrap(),
            json!({
                "final_density": {
                    "type":"minecraft:min",
                    "left": {
                        "type":"minecraft:add",
                        "left":{"type":"terraforged:cell","field":"height"},
                        "right":0.25
                    },
                    "right":"minecraft:unchanged"
                },
                "temperature":{"type":"terraforged:cell","field":"height","quantize_height":true}
            })
        );
        assert_eq!(base["minecraft:overridden"], "0.25");
    }

    #[test]
    fn stock_router_rejects_recursive_local_density_definitions() {
        let plan = RouterPlan {
            router: json!({"final_density":"terraforged:loop"}),
            definitions: BTreeMap::from([(
                "terraforged:loop".into(),
                json!("terraforged:loop").to_string(),
            )]),
            aliases: Vec::new(),
        };
        assert!(plan.stock_router(&BTreeMap::new()).is_err());
    }
}
