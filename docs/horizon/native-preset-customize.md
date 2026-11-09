# Native Customize preview

The native Customize menu is available in the local `0.1.1-customize.dev1`
preview. The published [Windows 0.1.0 release](windows-0.1.0-release.md) remains
the qualified default-only stable release; its frozen assets are unchanged.

Create a new world, choose **World → World Type: TerraForged → Customize**.
The menu exposes 28 supported native controls: continent size/irregularity,
terrain scales/weights, fancy mountains, biome sizes/warping, climate biases,
river widths/count, lake/wetland chance, smoothing and classic biome variants.
It uses the game's sliders, buttons and narration with paging. Done applies
the draft; Cancel/Escape discard it, and Reset changes only the draft.

Choices are saved with each world's overworld stem. Re-Create restores them,
and fresh default worlds do not inherit another world's choices. This menu
configures new worlds; it does not change already generated terrain.

Customized worlds require the preview engine and matching HMOD. They use
`terraforged:customized_v1` with a `terraforged:preset` JSON string. The old
0.1.0 engine was tested on a disposable copy: it refuses the unknown noise
settings ID with startup exit1 and a diagnostic report, preserving saved
settings and region files. Keep stable and preview worlds in separate profiles.
Malformed saved JSON was also tested on a disposable copy and refused without
changing those files. These checks do not claim a friendly downgrade UI.

The v1 format retains frozen kernel-v1 hidden fields, permits only exposed
settings within bounds, and limits serialized settings to 60 KiB. Unsupported
or malformed settings fail rather than substituting bundled defaults. Future
schema changes need a migration. World height/sea level, Java's full settings
surface, map preview and import/export are outside this initial native menu.

The [selected qualification evidence](../validation/horizon-customize-dev1/SUMMARY.json)
binds the exact local HMOD/client hashes and source pins. Genuine launcher build,
three-world creation/save, edited-world reopen with further generation,
Re-Create, Cancel/Reset, GUI-scale changes and image review passed. An independent
MSVC reader compared 15,360 stored quart biome values against the selected
generator, bundled defaults and vanilla. Edited and classic-off worlds differ
from the default generator; a fresh default world in the same process retains
the default classic biome. All runtime worlds were disposable QA worlds.

The isolated actual Title logic test passed mouse/keyboard arrows, Escape,
Done/Cancel/Reset and saved-setting refusal before replacement. Runtime keyboard
injection at the title is unavailable in the existing control API; no desktop
automation was used. Three adapter tests cover invalid data, roundtrip and each
exposed minimum/maximum, including combined bounds through finite terrain queries.

Public-tree, formatting and full workspace Clippy with warnings denied passed.
The broad Windows host check has 2,610 passing tests and one unchanged drop-motion
physics failure (one ULP). The exact baseline function/test reproduces it using
byte-identical shared core code without linking editor code; this is not a full
baseline-suite run. A separate Python failure selected the WSL bash proxy; its
seven affected tests pass with installed Git Bash. The full Windows host suite
is therefore not claimed green. The initial runtime attempt's stale readiness
location and unsupported title-key attempt remain recorded as failed harness
attempts, followed by the scoped passing runs above.

Engine changes are split into [settings/save API](https://github.com/TheApple05/horizon/pull/15)
and [menu](https://github.com/TheApple05/horizon/pull/16) PRs. The native
integration is [PR17](https://github.com/TheApple05/TerraForged-Horizon/pull/17).
This is a functional Windows x64 singleplayer preview, not a stable editor
release, multiplayer/modpack qualification or long-duration benchmark.
