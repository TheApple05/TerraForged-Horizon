// Base client registry metadata is present before Create's pack filtering.
use super::*;
thread_local! { static LOADING: std::cell::Cell<bool> = const { std::cell::Cell::new(false) }; }
struct Loading<'a>(&'a std::cell::Cell<bool>);
impl Drop for Loading<'_> {
    fn drop(&mut self) {
        self.0.set(false);
    }
}
pub fn maybe_load(root: &Path) -> Option<Result<Biomes>> {
    LOADING.with(|loading| {
        if loading.replace(true) {
            return None;
        }
        let _reset = Loading(loading);
        Some((|| {
            let base = Biomes::load(root)?;
            let overrides = horizon_world::worldgen::generator::terraforged_resources::augment(
                &root.join("worldgen"),
                &horizon_world::worldgen::overrides::WorldgenOverrides::default(),
            )
            .map_err(|error| std::io::Error::other(error.to_string()))?;
            let definitions = overrides
                .entries("biomes")
                .map(|(id, json)| {
                    serde_json::from_str::<Value>(json).map(|value| (id.to_owned(), value))
                })
                .collect::<std::result::Result<Vec<_>, _>>()?;
            let mut out =
                base.with_packs(definitions.iter().map(|(id, value)| (id.as_str(), value)));
            // Code-defined metadata is part of the base snapshot for every world.
            out.builtin = Arc::new(out.list.clone());
            out.packs.clear();
            Ok(out)
        })())
    })
}
