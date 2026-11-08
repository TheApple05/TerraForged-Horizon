# Launcher and representative modpack validation

November 7, 2026 (Pacific). This is an experimental native Horizon 26.3 port.
The separate Java 26.2 Fabric/NeoForge port has its own repository and evidence.

## Verified installation and build paths

The checked launcher source is `TheApple05/horizon@f43eebfc04b73f0c2bbf5048f7a3ab36c240f21d`, now merged through [host PR13](https://github.com/TheApple05/horizon/pull/13). It accepts combined native/content `.hmod` packages and preserves their extension and bytes. The local QA pack combines TerraForged, the unchanged official Coordinates HUD 2.0.0 `.hnmod`, and a small independently built content/recipe/light fixture, QA Glow.

The genuine launcher installs those archives, refuses native compilation without explicit trust, builds both native bundles and pins the resulting client to its pack instance. ZIP and MRPACK export/import preserve all three archives and preferences. Imported instances reuse the matching build. Both normal and uppercase CLI pack Play requests retain the ownership gate. No Minecraft resources were downloaded; existing privately prepared resources were copied into the isolated QA installation.

The first cold private-toolchain build takes 3,110.531 seconds, including provisioning. Native.dev7's incremental build takes 309.938 seconds, compiling the changed kernel and 14 downstream crates while reusing cached dependencies. These are individual build observations, not promised installation times.

The local index and QA pack are test fixtures. This does not establish an official registry listing. The current GitHub native-mod installer selects `.hnmod` assets, so a public combined `.hmod` must be placed whole in the instance's `horizon-native-mods` folder before `native-build`; renaming or extracting its contents is not part of the tested path.

## Actual-window native.dev6 baseline

The [immutable baseline export](../validation/horizon-native-launcher-dev6-v1/SUMMARY.md) includes the exact driver, plan, raw report, preference/camera audits, two save-reader replies, representative images and an independent review. Its TerraForged archive SHA-256 is `c9845ee3a3d036ef1f0dea379358c240efbb25a6c7156457c385166fd0dd235f`; the genuinely installed client is `50b71406d8dc2f661e4a783c4774d4cd6877d459b04ad3b8e9d0586a59e6f6ab`.

Both actual-window client processes exit zero. The run exercises:

- UI preset selection, seed 8675309, enabled structures and healthy natural survival spawn.
- Native HUD `/where` and off/on toggles through client chat, including persisted settings and visible changes.
- The installed Mods page and real 2×2 crafting, consuming the two ingredients and producing the custom item.
- Placement of that crafted block through the existing item-placement API in creative, with stone support supplied by a command. Its block light is seven and adjacent air is six.
- Fir forest, frozen marsh and shattered savanna scrub, then save/reopen, retained custom block/item/light/HUD state and distant terrain.

The historical save reader verifies four stored FULL chunks/6,144 quart values, then five/7,680 after reopening. These 13,824 comparisons are cross-revision compatibility checks using the older `1860b664` reader, not exact f43 reader qualification. The custom block occupies a separate chunk outside that reader's selected positions; reopening it in the actual new client supplies the custom-content persistence check.

### Preserved failures and corrections

The overall baseline report remains **FAILED**, SHA-256 `4dc73b50f5c165bce1993368c687f87f3b44defc910ba2608e0325db54da2369`. Its strict final byte guard rejects `horizon-mods.txt` because the game sorts its three unchanged enabled-mod lines. The separate audit verifies the exact original/actual bytes and line multisets, all other 25 locked files, and all 28,180 prepared-resource files. No setting changed, and the original verdict was not rewritten.

The original fir view's requested rotation initially worked, then native window input changed the camera during loading. The input label does not identify a person, device or application. A separate ordinary world copy, exact client and offscreen [corrected capture](../validation/horizon-native-launcher-dev6-v1/followup/fir-corrected/report.json) verify 135°/45° immediately before and after the image and exit zero. The original world and report remain unchanged. Independent inspection confirms textured forest terrain; the distance-six cutoff and a small leaf-like fragment at its far edge limit scenery conclusions.

The older visibility predicate required only 81 loaded columns. That proves bounded visible terrain, not complete view delivery. The new default-view check requires the integrated server's source-backed 637 tracked columns at distance 12, with live render/simulation option checks, settled queues and actual camera assertions. This differs from 533 draw columns and the standalone probe's 529 lit columns.

## Native.dev7 acceptance in progress

The source package SHA-256 is `ab511d1e0daa3670061a91d3ce3900127cb702ddfb60603d2d5dee9fe59fb355`. Genuine launcher compilation installs `native-f43eebf-9667ade2485e`, client SHA-256 `6a87351e5c85b83d728e55cfd6597cc90917b286a42fd16c8b819911fae6cd85`, for a fresh pack. The original pack and its pinned build stay unchanged. The [cache investigation](native-fir-investigation.md) records the measured capacity decision and memory tradeoff; the [current sampled-kernel regression](../validation/horizon-native-cache-dev7-sampled-v1.json) matches Java observations in both profiles.

Final default-view client/save testing has not yet completed. The originally tested launcher imports `VCRUNTIME140.dll`; a separate rebuild with upstream's static-CRT release flags is undergoing portability qualification before distribution. Its earlier successful launches do not prove runtime independence on another machine.

## Remaining scope

GUI Play is blocked by the computer-use runtime: both supported backends fail before initialization with a missing kernel-assets path (Windows error 3), including after resetting the JavaScript kernel. Direct client tests do not cover the GUI dispatch or authenticated Play. No account credentials or real player profiles are used.

These representative three-mod checks do not establish arbitrary modpack compatibility, sustained background-ring performance, whole-feature Java scenery parity, general frame rate or other operating systems' client behavior. The historical unexplained exit remains unrecoverable; later clean runs do not identify its cause. Exact failures, source/package identities and these boundaries remain part of the evidence.
