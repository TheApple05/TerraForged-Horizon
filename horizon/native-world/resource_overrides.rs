// Metadata defaults below the complete user pack stack, including unknown kinds.
use super::WorldgenOverrides;
pub fn with_defaults(defaults: &WorldgenOverrides, packs: &WorldgenOverrides) -> WorldgenOverrides {
    let mut out = defaults.clone();
    for (kind, entries) in &packs.entries {
        out.entries
            .entry(kind.clone())
            .or_default()
            .extend(entries.clone());
    }
    for (kind, tags) in &packs.tags {
        out.tags
            .entry(kind.clone())
            .or_default()
            .extend(tags.clone());
    }
    out
}
