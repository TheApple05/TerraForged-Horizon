// Per-load resource derivation. This module retains no world owner or seed.
use super::*;
use crate::worldgen::tags::TagDefinitions;
use horizon_core::density::terraforged_runtime::kernel::{
    classic_biome_data, classic_biomes::VARIANTS,
};

fn tags(
    raw: &Bundle,
    packs: &WorldgenOverrides,
    kind: &str,
    known: impl Fn(&str) -> bool,
) -> Result<BTreeMap<String, Vec<String>>, GeneratorError> {
    let mut definitions = TagDefinitions::default();
    for (name, json) in raw {
        definitions.apply_json(name, "prepared", json)?;
    }
    for (name, pack, json) in packs.tags(kind) {
        definitions.apply_json(name, pack, json)?;
    }
    // Like the host's feature catalog, unavailable unrelated tags are omitted.
    // Using one of those missing tags still fails the bounded tree classifier.
    let built = definitions
        .build(|id, _| known(id).then(|| id.to_owned()))
        .map_err(|error| resource(format!("TerraForged {kind}: {error:?}")))?;
    Ok(built.tags)
}

pub fn augment(dir: &Path, packs: &WorldgenOverrides) -> Result<WorldgenOverrides, GeneratorError> {
    let parents = read_bundle(dir, packs, "biomes")?;
    let configured = read_bundle(dir, packs, "features")?;
    let placed = read_bundle(dir, packs, "placed_features")?;
    let empty = WorldgenOverrides::default();
    let raw_biome_tags = read_bundle(dir, &empty, "biome_tags")?;
    let biome_tags = tags(&raw_biome_tags, &empty, "biome_tags", |id| {
        parents.contains_key(id) || VARIANTS.contains(&id)
    })?;
    let raw_feature_tags =
        read_optional_bundle(dir, &empty, "placed_feature_tags")?.unwrap_or_default();
    let feature_tags = tags(&raw_feature_tags, packs, "placed_feature_tags", |id| {
        placed.contains_key(id)
    })?;
    let derived =
        classic_biome_data::derive(&parents, &configured, &placed, &biome_tags, &feature_tags)
            .map_err(resource)?;
    let mut defaults = WorldgenOverrides::default();
    for (kind, entries) in [
        ("biomes", derived.biomes),
        ("features", derived.configured_features),
        ("placed_features", derived.placed_features),
    ] {
        for (id, json) in entries {
            defaults.set(kind, &id, json);
        }
    }
    for (id, values) in derived.biome_tags {
        defaults.add_tag(
            "biome_tags",
            &id,
            "terraforged_native",
            serde_json::json!({"replace":false,"values":values}).to_string(),
        );
    }
    Ok(crate::worldgen::overrides::terraforged_defaults::with_defaults(&defaults, packs))
}

thread_local! { static LOADING: std::cell::Cell<bool> = const { std::cell::Cell::new(false) }; }
struct Loading<'a>(&'a std::cell::Cell<bool>);
impl Drop for Loading<'_> {
    fn drop(&mut self) {
        self.0.set(false);
    }
}
pub fn maybe_load(
    dir: &Path,
    registry: &'static BlockRegistry,
    packs: &WorldgenOverrides,
) -> Option<Result<Arc<GeneratorData>, GeneratorError>> {
    LOADING.with(|loading| {
        if loading.replace(true) {
            return None;
        }
        let _reset = Loading(loading);
        Some(
            augment(dir, packs)
                .and_then(|overrides| GeneratorData::load_with(dir, registry, &overrides)),
        )
    })
}
