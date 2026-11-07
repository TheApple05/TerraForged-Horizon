//! Client metadata and the real enabled-world-pack path; no game is launched.
use horizon_client::{biome::Biomes, game::terraforged_biome_packs};
use horizon_core::{
    density::terraforged_runtime::kernel::classic_biomes::VARIANTS, version::DATA_PACK_FORMAT,
};
use horizon_world::{registry::BlockRegistry, worldgen::generator::GeneratorData};
use serde_json::{Value, json};
use std::{collections::BTreeMap, fs, path::Path, sync::Arc};
fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 2 {
        return Err("own resources and fresh scratch directory required".into());
    }
    let resources = Path::new(&args[0]);
    let scratch = Path::new(&args[1]);
    if scratch.exists() {
        return Err("scratch already exists".into());
    }
    fs::create_dir(scratch)?;
    let registry = Box::leak(Box::new(BlockRegistry::from_facts_json(fs::File::open(
        resources.join("facts.json"),
    )?)?));
    let data = GeneratorData::load(&resources.join("worldgen"), registry)?;
    let base = Arc::new(Biomes::load(resources)?);
    let mut names = BTreeMap::new();
    for name in VARIANTS {
        assert!(base.contains(name), "client registry is missing {name}");
        let client_id = base.id(name);
        let generation_id = data.biome_id(name).ok_or("generation biome absent")?;
        assert_eq!(
            u32::from(client_id),
            generation_id.0,
            "builtin-plus-classic registry IDs disagree"
        );
        let info = base.get(client_id);
        let raw: Value = serde_json::from_str(data.biome_json(generation_id))?;
        assert_eq!(info.name, name);
        assert_eq!(
            info.temperature,
            raw["temperature"].as_f64().ok_or("temperature absent")? as f32
        );
        assert_eq!(
            info.downfall,
            raw["downfall"].as_f64().ok_or("downfall absent")? as f32
        );
        if let Some(water) = raw["effects"]["water_color"].as_u64() {
            assert_eq!(info.water, water as u32);
        }
        names.insert(name, client_id);
    }
    let world = scratch.join("packed-world");
    let pack = world.join("datapacks/native-priority");
    fs::create_dir_all(pack.join("data/reterraforged/worldgen/biome"))?;
    fs::create_dir_all(pack.join("data/minecraft/worldgen/biome"))?;
    fs::write(pack.join("pack.mcmeta"),json!({"pack":{"min_format":[DATA_PACK_FORMAT.0,DATA_PACK_FORMAT.1],"max_format":[DATA_PACK_FORMAT.0,DATA_PACK_FORMAT.1],"description":"Native biome metadata QA"}}).to_string())?;
    fs::write(
        world.join("datapacks.json"),
        json!({"enabled":["vanilla","file/native-priority"],"disabled":[]}).to_string(),
    )?;
    let mut bryce: Value =
        serde_json::from_str(data.biome_json(data.biome_id("reterraforged:bryce").unwrap()))?;
    bryce["temperature"] = json!(0.125);
    bryce["effects"]["water_color"] = json!(0x123456);
    fs::write(
        pack.join("data/reterraforged/worldgen/biome/bryce.json"),
        bryce.to_string(),
    )?;
    let mut jungle: Value =
        serde_json::from_str(data.biome_json(data.biome_id("minecraft:jungle").unwrap()))?;
    jungle["effects"]["water_color"] = json!(0xabcdef);
    fs::write(
        pack.join("data/minecraft/worldgen/biome/jungle.json"),
        jungle.to_string(),
    )?;
    let packed = terraforged_biome_packs::maybe_packed(&world, resources, &base, &[])
        .ok_or("world metadata derivation failed")?;
    assert_eq!(
        packed.get(packed.id("reterraforged:bryce")).temperature,
        0.125
    );
    assert_eq!(packed.get(packed.id("reterraforged:bryce")).water, 0x123456);
    assert_eq!(
        packed.get(packed.id("reterraforged:stone_forest")).water,
        0xabcdef,
        "derived client variant ignored its packed parent"
    );
    assert_ne!(
        base.get(base.id("reterraforged:bryce")).water,
        0x123456,
        "pack changed base metadata"
    );
    let clean = scratch.join("clean-world");
    fs::create_dir(&clean)?;
    let clean = terraforged_biome_packs::maybe_packed(&clean, resources, &base, &[])
        .ok_or("clean world metadata failed")?;
    for name in VARIANTS {
        assert_eq!(
            clean.get(clean.id(name)).water,
            base.get(base.id(name)).water,
            "a world's pack leaked to the next world"
        );
    }
    println!(
        "{}",
        serde_json::to_string_pretty(
            &json!({"status":"passed-native-client-classic-biome-metadata","variants":names,"allClassicMetadataPresent":true,"builtinAndClassicIdsMatchGeneration":true,"explicitVariantPackWon":true,"derivedParentPackReachedClient":true,"baseAndNextWorldUnchanged":true,"notCovered":["Rendered scenery","GPU behavior","Save-file round trip","Standard launcher and mod combinations"]})
        )?
    );
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
