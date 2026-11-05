//! Controlled geometry around the real native feature, with actual seeded graphs.
use horizon_core::density::terraforged_runtime::kernel::kernel_sampler::KernelSampler;
use horizon_world::{fluid::FluidState,heightmap::HeightmapType,registry::{BlockRegistry,BlockStateId},worldgen::{
    block_feature::FeatureBlockBindings,external_feature::{ExternalFeature,ExternalFeatureDecoder,ExternalFeatureWorld},
    generator::{GeneratorData,terraforged_features::NativeFeatureDecoder,terraforged_world},placement::PlacementQueryError,
}};
use serde_json::{Value,json};
use std::{collections::{BTreeMap,BTreeSet},fs,path::Path,sync::Arc};
type Q<T>=Result<T,PlacementQueryError>;
struct Column {
    at:[i32;2],surface:i32,seed:i64,air:BlockStateId,stone:BlockStateId,
    obstacle:Option<BlockStateId>,natural:bool,matching:bool,taper:bool,
    fail_after:Option<usize>,writes:BTreeMap<[i32;3],BlockStateId>,
}
impl ExternalFeatureWorld for Column {
    fn block_state(&mut self,p:[i32;3])->Q<BlockStateId> {
        Ok(self.writes.get(&p).copied().unwrap_or_else(|| {
            if p[0]==self.at[0] && p[2]==self.at[1] && p[1]==self.surface+1 {
                if let Some(state)=self.obstacle {return state;}
            }
            if p[1]<=self.surface {self.stone}else{self.air}
        }))
    }
    fn set_chunk_block(&mut self,p:[i32;3],state:BlockStateId)->Q<()> {
        if self.fail_after==Some(self.writes.len()) {return Err(PlacementQueryError::Failed("injected write failure".into()));}
        assert!((-64..=319).contains(&p[1]));assert_eq!([p[0],p[2]],self.at);
        assert_eq!(self.block_state(p)?,self.air,"native pillar overwrote an existing block");
        self.writes.insert(p,state);Ok(())
    }
    fn height(&mut self,_:HeightmapType,x:i32,z:i32)->Q<i32> {Ok(if [x,z]==self.at {self.surface+1}else{63})}
    fn min_y(&mut self)->Q<i32>{Ok(-64)}
    fn max_y(&mut self)->Q<i32>{Ok(319)}
    fn sea_level(&mut self)->Q<i32>{Ok(63)}
    fn world_seed(&mut self)->Q<i64>{Ok(self.seed)}
    fn fluid_state(&mut self,_:[i32;3])->Q<FluidState>{Ok(FluidState::EMPTY)}
    fn block_matches_tag(&mut self,p:[i32;3],_:&str)->Q<bool>{Ok(self.natural && [p[0],p[2]]==self.at)}
    fn noise_biome_is(&mut self,q:[i32;3],_:&str)->Q<bool>{
        Ok(self.matching && (!self.taper || (q[0]==self.at[0]>>2 && q[2]==self.at[1]>>2)))
    }
}
fn decoder(kernel:Arc<KernelSampler>,seed:i64,enabled:bool,blocks:&FeatureBlockBindings<'_>,stone:bool)->Result<Arc<dyn ExternalFeature>,Box<dyn std::error::Error>> {
    Ok(NativeFeatureDecoder::new(kernel,seed,enabled)?.decode("reterraforged:classic_pillar",&json!({"type":"reterraforged:classic_pillar","stone_forest":stone}).to_string(),blocks).ok_or("decoder did not claim pillar")??)
}
fn run()->Result<(),Box<dyn std::error::Error>> {
    let args:Vec<_>=std::env::args().skip(1).collect();if args.len()!=3{return Err("resources, configuration and targets required".into());}
    let root=Path::new(&args[0]);let input:Value=serde_json::from_str(&fs::read_to_string(&args[1])?)?;
    let targets:Value=serde_json::from_str(&fs::read_to_string(&args[2])?)?;let seed=targets["seed"].as_i64().unwrap();
    let registry=Box::leak(Box::new(BlockRegistry::from_facts_json(fs::File::open(root.join("facts.json"))?)?));
    let data=GeneratorData::load(&root.join("worldgen"),registry)?;
    let opened=terraforged_world::open(data,seed,&input["preset"].to_string(),&input["noiseRegistry"].to_string(),false)?;
    let kernel=opened.kernel.upgrade().ok_or("kernel absent")?;
    let bindings=FeatureBlockBindings::new(registry,BTreeSet::new())?;let mut observations=Vec::new();
    for (biome,stone) in [("reterraforged:bryce",false),("reterraforged:stone_forest",true)] {
        let target=&targets["targets"][biome];let hint=[target["x"].as_i64().unwrap() as i32,target["z"].as_i64().unwrap() as i32];
        let make=|at,surface|Column {at,surface,seed,air:registry.default_state("minecraft:air").unwrap(),stone:registry.default_state("minecraft:stone").unwrap(),obstacle:None,natural:true,matching:true,taper:false,fail_after:None,writes:BTreeMap::new()};
        let feature=decoder(kernel.clone(),seed,true,&bindings,stone)?;
        // A biome location need not have a positive ridge at its exact block.
        // Select a positive column by executing the feature, without projecting
        // its height formula into the test or changing any kernel values.
        let mut chosen=None;
        'find:for dz in 0..16 {for dx in 0..16 {
            let at=[(hint[0]&!15)+dx,(hint[1]&!15)+dz];let mut trial=make(at,80);
            feature.place(&mut trial,[at[0],0,at[1]])?;
            if trial.writes.len()>16 {chosen=Some(at);break 'find;}
        }}
        let at=chosen.ok_or("no strong pillar column in advisory chunk")?;
        let create=|surface|make(at,surface);
        let origin=[at[0],0,at[1]];let mut normal=create(80);assert!(feature.place(&mut normal,origin)?);
        let full=normal.writes.len();assert!(full>3);
        let mut clipped=create(316);assert!(feature.place(&mut clipped,origin)?);assert_eq!(clipped.writes.len(),3);
        if stone {
            assert_eq!(clipped.writes[&[at[0],317,at[1]]],registry.default_state("minecraft:stone").unwrap());
            assert_eq!(clipped.writes[&[at[0],318,at[1]]],registry.default_state("minecraft:dirt").unwrap());
            assert_eq!(clipped.writes[&[at[0],319,at[1]]],registry.default_state("minecraft:grass_block").unwrap());
        }
        let mut edge=create(80);edge.taper=true;assert!(feature.place(&mut edge,origin)?);assert!(edge.writes.len()<full);
        for obstacle in ["minecraft:water","minecraft:oak_log"] {
            let mut blocked=create(80);blocked.obstacle=registry.default_state(obstacle);
            assert!(!feature.place(&mut blocked,origin)?);assert!(blocked.writes.is_empty());
        }
        let mut no_footing=create(80);no_footing.natural=false;assert!(!feature.place(&mut no_footing,origin)?);
        let mut other_biome=create(80);other_biome.matching=false;assert!(!feature.place(&mut other_biome,origin)?);
        for surface in [63,319] {let mut outside=create(surface);assert!(!feature.place(&mut outside,origin)?);}
        let mut wrong=create(80);wrong.seed+=1;assert!(feature.place(&mut wrong,origin).is_err());assert!(wrong.writes.is_empty());
        let mut failed=create(80);failed.fail_after=Some(2);assert!(feature.place(&mut failed,origin).is_err());assert_eq!(failed.writes.len(),2);
        let disabled=decoder(kernel.clone(),seed,false,&bindings,stone)?;assert!(!disabled.place(&mut create(80),origin)?);drop(disabled);
        observations.push(json!({"biome":biome,"selectedColumn":at,"fullHeight":full,"boundaryHeight":edge.writes.len(),"clippedHeight":3,"stoneClippedCapChecked":stone,"waterAndStructureProtected":true,"invalidFootingAndBiomeSkipped":true,"seaAndMaxYSkipped":true,"foreignSeedRejected":true,"writeErrorPropagatedAfterTwoWrites":true,"disabledSkipped":true}));
    }
    drop(kernel);opened.generator.release_caches();drop(opened.generator);assert!(opened.kernel.upgrade().is_none());
    println!("{}",serde_json::to_string_pretty(&json!({"status":"passed-native-pillar-placement-edge-cases","observations":observations,"releasedKernelOwner":true,"scope":"Actual native decoder/feature with real seeded graphs and a controlled one-column world; separate real-region checks cover production heightmaps.","notCovered":["Independent Java whole-feature parity","Marsh synthetic geometry","Client/launcher/performance"]}))?);Ok(())
}
fn main(){if let Err(error)=run(){eprintln!("{error}");std::process::exit(1);}}
