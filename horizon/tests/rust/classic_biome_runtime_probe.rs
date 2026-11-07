//! Natural noise and stored-quart checks. Coordinates are advisory Java locations.
use horizon_core::{
    density::terraforged_runtime::kernel::classic_biomes::VARIANTS, position::ChunkPos,
};
use horizon_world::{
    registry::BlockRegistry,
    worldgen::generator::{GeneratorData, terraforged_world},
};
use serde_json::{Value, json};
use std::{fs, path::Path};
fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 3 {
        return Err("own resource root, configuration and advisory targets required".into());
    }
    let root = Path::new(&args[0]);
    let input: Value = serde_json::from_str(&fs::read_to_string(&args[1])?)?;
    let targets: Value = serde_json::from_str(&fs::read_to_string(&args[2])?)?;
    let registry = Box::leak(Box::new(BlockRegistry::from_facts_json(fs::File::open(
        root.join("facts.json"),
    )?)?));
    let data = GeneratorData::load(&root.join("worldgen"), registry)?;
    let seed = targets["seed"].as_i64().ok_or("target seed missing")?;
    let opened = terraforged_world::open(
        data.clone(),
        seed,
        &input["preset"].to_string(),
        &input["noiseRegistry"].to_string(),
        false,
    )?;
    let weak = opened.kernel;
    let native = opened.generator;
    let mut worker = native.worker();
    let mut observations = Vec::new();
    let mut missing = Vec::new();
    for name in VARIANTS {
        let target = &targets["targets"][name];
        let x = target["x"].as_i64().ok_or("target X missing")? as i32;
        let y = target["y"].as_i64().ok_or("target Y missing")? as i32;
        let z = target["z"].as_i64().ok_or("target Z missing")? as i32;
        let quart = [x >> 2, y >> 2, z >> 2];
        let source = worker.noise_biomes(&[quart]).remove(0);
        let chunk = worker.generate_proto(ChunkPos::new(x >> 4, z >> 4))?;
        let stored = chunk.biome_at(x, y, z).to_owned();
        assert_eq!(
            source.as_deref(),
            Some(stored.as_str()),
            "live source and stored quart differ for {name}"
        );
        if stored != name {
            missing.push(name);
        }
        observations.push(json!({"expected":name,"at":[x,y,z],"source":source,"stored":stored,"surfaceY":chunk.surface_height(x&15,z&15)}));
        native.release_caches();
        worker.release();
    }
    let mut disabled = input["preset"].clone();
    disabled["miscellaneous"]["classicBiomeVariants"] = false.into();
    let disabled = terraforged_world::open(
        data.clone(),
        seed,
        &disabled.to_string(),
        &input["noiseRegistry"].to_string(),
        false,
    )?;
    let disabled_weak = disabled.kernel;
    let mut off = disabled.generator.worker();
    let caves = [[0, -1, 0], [1024, -8, -2048], [-3167, -16, 3167]];
    let enabled_caves = worker.noise_biomes(&caves);
    assert_eq!(enabled_caves, off.noise_biomes(&caves));
    let mut disabled_queries = Vec::new();
    for target in targets["targets"]
        .as_object()
        .ok_or("targets object required")?
        .values()
    {
        disabled_queries.push([
            target["x"].as_i64().unwrap() as i32 >> 2,
            target["y"].as_i64().unwrap() as i32 >> 2,
            target["z"].as_i64().unwrap() as i32 >> 2,
        ]);
    }
    let disabled_names = off.noise_biomes(&disabled_queries);
    assert!(disabled_names.iter().all(|name| {
        name.as_deref()
            .is_some_and(|id| !id.starts_with("reterraforged:"))
    }));
    off.release();
    drop(off);
    disabled.generator.release_caches();
    drop(disabled.generator);
    assert!(disabled_weak.upgrade().is_none());
    worker.release();
    drop(worker);
    native.release_caches();
    drop(native);
    assert!(
        weak.upgrade().is_none(),
        "native feature/mapper owner leaked"
    );
    println!(
        "{}",
        serde_json::to_string_pretty(
            &json!({"status":if missing.is_empty(){"passed-native-classic-natural-source-and-stored-quarts"}else{"failed-advisory-target-coverage"},"worldSeed":seed,"observations":observations,"missing":missing,"caveSamples":enabled_caves,"classicDisabledSamples":disabled_names,"releasedBothKernelOwners":true,"notCovered":["Feature block placement at these locations","Independent full-chunk Java parity","Client metadata/save/launcher/performance"]})
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
