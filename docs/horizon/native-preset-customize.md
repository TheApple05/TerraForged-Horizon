# Native Customize development

This work follows the shipped [Windows 0.1.0 release](windows-0.1.0-release.md).
That release and its default-only preset remain unchanged. The editor is being
qualified as `0.1.1-customize.dev1`; no stable editor release is claimed here.

The new creation screen exposes 28 supported native controls: continent size
and irregularity, terrain scales and weights, fancy mountains, biome sizes and
warping, climate biases, river widths/count, lake/wetland chance, smoothing and
classic biome variants. It uses existing game sliders, buttons and narration,
with pages, mouse dragging and keyboard navigation. Done applies the draft to
the new world; Cancel/Escape discard it, and Reset changes only the draft.

Choices are saved with each world's overworld stem. Re-Create retains the stem
and restores its choices. Fresh default worlds do not inherit another world's
settings. Configurations use `terraforged:customized_v1` and a
`terraforged:preset` JSON string in the generator compound. The old 0.1.0
engine has no noise settings with that ID and returns an error rather than
silently generating default terrain. Actual old-client refusal remains part
of the pending runtime qualification.

The v1 format retains the frozen kernel-v1 hidden fields, permits only the
exposed settings within their bounds, and limits serialized settings to 60 KiB.
Malformed, missing or unsupported configuration fails clearly. A future schema
change needs a migration; it must not silently substitute bundled defaults.
World height, sea level, the full Java editor, map preview and import/export
are outside this initial native menu.

The engine work is split into [settings/save API](https://github.com/TheApple05/horizon/pull/15)
and [menu](https://github.com/TheApple05/horizon/pull/16) changes. Windows
client/control-tool type checks and the isolated save/menu interaction test
passed. The adapter's three tests cover malformed data, saved-setting
roundtrip and every exposed minimum/maximum, including combined bounds,
through native sampler construction and finite terrain queries. Formatting,
adapter Clippy with warnings denied and source staging also pass.

An integrated native client build, image review, edited/default-world generation,
save/reopen, Re-Create, malformed-world refusal and old-client refusal still
need to pass. All runtime tests use separate scratch worlds. Existing player
worlds and the installed stable profile are preserved.
