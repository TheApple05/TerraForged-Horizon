//! Run only the native geology through real FEATURES regions and heightmaps.
//! Biome/terrain selection is untouched; other decoration is removed by packs.
use horizon_core::position::ChunkPos;
use horizon_world::{registry::BlockRegistry,worldgen::{generator::{GeneratorData,ProtoChunk,terraforged_world},overrides::WorldgenOverrides}};
use serde_json::{Value,json};
use std::{collections::BTreeMap,fs,path::Path};
fn run()->Result<(),Box<dyn std::error::Error>> {
    let args:Vec<_>=std::env::args().skip(1).collect();
    if args.len()!=3{return Err("own resources, configuration, advisory targets required".into());}
    let root=Path::new(&args[0]);let dir=root.join("worldgen");
    let input:Value=serde_json::from_str(&fs::read_to_string(&args[1])?)?;
    let targets:Value=serde_json::from_str(&fs::read_to_string(&args[2])?)?;
    let seed=targets["seed"].as_i64().ok_or("seed missing")?;
    let registry=Box::leak(Box::new(BlockRegistry::from_facts_json(fs::File::open(root.join("facts.json"))?)?));
    let data=GeneratorData::load(&dir,registry)?;
    let mut packs=WorldgenOverrides::default();
    for id in data.biome_names() {
        let mut biome:Value=serde_json::from_str(data.biome_json(data.biome_id(id).unwrap()))?;
        let mut steps=vec![Vec::<String>::new();11];
        match id.as_ref() {
            "reterraforged:bryce"=>steps[0].push("reterraforged:bryce_surface".into()),
            "reterraforged:stone_forest"=>steps[0].push("reterraforged:stone_forest_surface".into()),
            "reterraforged:marshland"=>steps[0].push("reterraforged:classic_marsh_surface".into()),
            _=>{},
        }
        biome["features"]=serde_json::to_value(steps)?;
        packs.set("biomes",id,biome.to_string());
    }
    let controlled=GeneratorData::load_with(&dir,registry,&packs)?;
    let opened=terraforged_world::open(controlled,seed,&input["preset"].to_string(),&input["noiseRegistry"].to_string(),false)?;
    let weak=opened.kernel;let native=opened.generator;let mut worker=native.worker();let mut observations=Vec::new();
    let mut failures=Vec::new();
    for name in ["reterraforged:bryce","reterraforged:stone_forest","reterraforged:marshland"] {
        let target=&targets["targets"][name];let x=target["x"].as_i64().ok_or("X missing")? as i32;
        let z=target["z"].as_i64().ok_or("Z missing")? as i32;
        let (cx,cz)=(x>>4,z>>4);let mut region=Vec::new();
        for dz in -1..=1 {for dx in -1..=1 {region.push(worker.generate_proto(ChunkPos::new(cx+dx,cz+dz))?);}}
        let mut region:[ProtoChunk;9]=region.try_into().map_err(|_|"nine chunks required")?;
        let before:Vec<_>=(-64..320).flat_map(|y|(0..16).flat_map(move|z|(0..16).map(move|x|(x,y,z))))
            .map(|(x,y,z)|region[4].block(x,y,z)).collect();
        let stats=worker.decorate(&mut region)?;
        let mut changed=0;let mut overwritten_non_air=0;let mut materials=BTreeMap::new();
        let mut columns=BTreeMap::<(i32,i32),usize>::new();let mut index=0;
        for y in -64..320 {for z in 0..16 {for x in 0..16 {
            let old=before[index];let new=region[4].block(x,y,z);index+=1;
            if old==new {continue;}changed+=1;*columns.entry((x,z)).or_default()+=1;
            let old_name=&registry.state(old).ok_or("unregistered old state")?.name;
            let new_name=registry.state(new).ok_or("unregistered native material")?.name.clone();
            *materials.entry(new_name).or_insert(0usize)+=1;
            if !matches!(old_name.as_str(),"minecraft:air"|"minecraft:cave_air"|"minecraft:void_air") {overwritten_non_air+=1;}
        }}}
        if stats.failed!=0 || stats.unsupported!=0 || changed==0 {failures.push(name);}
        if name!="reterraforged:marshland" {assert_eq!(overwritten_non_air,0,"pillar overwrote existing material");}
        observations.push(json!({"biome":name,"chunk":[cx,cz],"changedBlocks":changed,"changedColumns":columns.len(),"maxChangedColumn":columns.values().max(),"overwrittenNonAir":overwritten_non_air,"materials":materials,"decoration":{"placed":stats.placed,"failed":stats.failed,"unsupported":stats.unsupported,"skipped":stats.skipped},"centerDecorated":region[4].is_decorated()}));
        native.release_caches();worker.release();
    }
    let unsupported=native.unsupported_features();assert!(unsupported.is_empty(),"native geology unsupported: {unsupported:?}");
    worker.release();drop(worker);native.release_caches();drop(native);assert!(weak.upgrade().is_none());
    println!("{}",serde_json::to_string_pretty(&json!({"status":if failures.is_empty(){"passed-real-native-geology-placement"}else{"failed-no-native-geology-placement"},"worldSeed":seed,"observations":observations,"failures":failures,"releasedKernelOwner":true,"otherDecorationDisabledByTestPack":true,"biomeSelectionOverridden":false,"notCovered":["Independent Java whole-feature block parity","Synthetic clipping/boundary/obstruction cases","Mixed full decoration/structures","Client/launcher/performance"]}))?);Ok(())
}
fn main(){if let Err(error)=run(){eprintln!("{error}");std::process::exit(1);}}
