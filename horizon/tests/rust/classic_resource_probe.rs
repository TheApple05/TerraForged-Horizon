//! Integration checks over the actual prepared resources and generation loader.
use horizon_core::density::terraforged_runtime::kernel::classic_biomes::VARIANTS;
use horizon_world::{
    registry::BlockRegistry,
    worldgen::{generator::{GeneratorData, terraforged_resources}, overrides::WorldgenOverrides, tags::TagDefinitions},
};
use serde_json::{Value, json};
use std::{collections::BTreeMap, fs, path::Path};

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let root = std::env::args_os().nth(1).ok_or("prepared resource root required")?;
    let root = Path::new(&root);
    let dir = root.join("worldgen");
    let registry = Box::leak(Box::new(BlockRegistry::from_facts_json(fs::File::open(root.join("facts.json"))?)?));
    let empty = WorldgenOverrides::default();
    let defaults = terraforged_resources::augment(&dir, &empty)?;
    assert_eq!(defaults.entries("biomes").count(), 17);
    assert_eq!(defaults.entries("features").count(), 3);
    assert_eq!(defaults.entries("placed_features").count(), 8);
    let data = GeneratorData::load(&dir, registry)?;
    let mut variants = BTreeMap::new();
    for name in VARIANTS {
        let id = data.biome_id(name).ok_or("derived biome absent from real registry")?;
        let value: Value = serde_json::from_str(data.biome_json(id))?;
        assert_eq!(value["features"].as_array().ok_or("feature steps missing")?.len(), 11);
        variants.insert(name, id.0);
    }
    for (id, _) in defaults.entries("features") {
        assert!(data.configured_feature_json(id).is_some(), "{id}");
    }
    for (id, _) in defaults.entries("placed_features") {
        assert!(data.placed_feature_json(id).is_some(), "{id}");
    }

    // A user variant definition wins, arbitrary kinds survive, and a replacing
    // tag removes native members through the host's actual tag builder.
    let mut packs = WorldgenOverrides::default();
    let mut custom: Value = serde_json::from_str(data.biome_json(data.biome_id(VARIANTS[0]).unwrap()))?;
    custom["temperature"] = json!(0.125);
    custom["effects"]["water_color"] = json!(1193046);
    packs.set("biomes", VARIANTS[0], custom.to_string());
    packs.set("future_extension_kind", "test:retain", "{\"sentinel\":17}".into());
    let (tag, _, _) = defaults.tags("biome_tags").next().ok_or("no inherited biome tags")?;
    packs.add_tag("biome_tags", tag, "test:replace", json!({"replace":true,"values":["minecraft:plains"]}).to_string());
    let merged = terraforged_resources::augment(&dir, &packs)?;
    assert_eq!(merged.entries("future_extension_kind").collect::<Vec<_>>(), [("test:retain", "{\"sentinel\":17}")]);
    let prepared: BTreeMap<String, String> = serde_json::from_str(&fs::read_to_string(dir.join("biome_tags.json"))?)?;
    let mut definitions = TagDefinitions::default();
    for (id, raw) in &prepared { definitions.apply_json(id, "prepared", raw)?; }
    for (id, pack, raw) in merged.tags("biome_tags") { definitions.apply_json(id, pack, raw)?; }
    let tags = definitions.build(|id, _| data.biome_id(id).map(|_| id.to_owned()))?;
    assert_eq!(tags.tags[tag], ["minecraft:plains"]);
    let packed = GeneratorData::load_with(&dir, registry, &packs)?;
    let observed: Value = serde_json::from_str(packed.biome_json(packed.biome_id(VARIANTS[0]).unwrap()))?;
    assert_eq!(observed, custom);
    let again = GeneratorData::load(&dir, registry)?;
    let unchanged: Value = serde_json::from_str(again.biome_json(again.biome_id(VARIANTS[0]).unwrap()))?;
    assert_ne!(unchanged, custom, "a world pack leaked into the next resource load");
    println!("{}", serde_json::to_string_pretty(&json!({
        "status":"passed-native-classic-resource-integration", "variants":variants,
        "configuredFeatures":3, "placedFeatures":8, "variantOverrideWon":true,
        "replacingTagWon":tag, "arbitraryResourceKindRetained":true, "nextLoadUnchanged":true,
        "warnings":packed.warnings(), "notCovered":["Client metadata IDs/colors", "Feature block placement", "Natural biome coverage", "Performance"]
    }))?);
    Ok(())
}
fn main() { if let Err(error) = run() { eprintln!("{error}"); std::process::exit(1); } }
