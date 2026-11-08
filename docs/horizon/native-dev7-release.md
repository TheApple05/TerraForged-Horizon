> 🤖 Opened by TheApple05's AI agent (Codex), not by TheApple05 personally.

Experimental native Rust TerraForged for **Horizon / Minecraft 26.3**. The Java 26.2 Fabric/NeoForge port remains in [its separate repository](https://github.com/TheApple05/TerraForged-26.2).

This update retains the distance-12 terrain working set instead of repeatedly rebuilding fir-forest tiles. Four simultaneous builds remain unchanged. Default retained tile backing is 75 MiB per sampler, 56.25 MiB more than the previous eight-tile cache; other allocations are additional.

### Downloads and installation

- `terraforged-horizon-26.3-0.1.0-native.dev7.hmod`: combined native source/content package. Keep it whole and place it in your instance game folder's `horizon-native-mods` directory. Keep other native source archives alongside it, then use `native-build` with explicit native-code trust. Select `terraforged:default` in world creation.
- `terraforged-horizon-launcher-windows-x64-native.dev7.zip`: the compatible Windows x64 launcher, built with upstream static-CRT release flags, with MIT notices. Extract it and use `Start-TerraForged-Horizon.cmd`; the wrapper disables upstream self-update for this fork process. Direct GUI execution of the EXE retains upstream updater behavior.
- `SHA256SUMS`: checksums for both artifacts.

Use your own prepared Minecraft Java 26.3 resources/base and Minecraft ownership. Native compilation requires the launcher-provisioned Rust toolchain. The qualified prepared base was privately copied from an existing installation; a fresh public install/sign-in has not been qualified. No Minecraft resources, compiled game client, saved worlds, accounts, HUD mod or QA fixture are distributed.

CLI example, replacing both placeholders with your prepared base and pack ID:

```text
horizon-launcher.exe native-build --instance "pack:<id>" --version "<prepared-base-version>" --profile performance --trust-native-code
```

The GitHub native-mod installer currently selects `.hnmod` assets. Use manual whole-HMOD placement or your own checked pack registry for this package. This is not an official registry listing.

### Verified scope

The genuine launcher installs/builds dev7 and pins the resulting client. Its offscreen client test passes UI creation, healthy natural survival spawn, full distance-12 loading in six views including fir forest/frozen marsh/shattered savanna scrub, native HUD commands/toggles, actual crafting and item placement, then custom block/item/light persistence after reopen. Both clients exit zero. All 15 images were inspected; 40 camera assertions, 30 locked-input checks and 28,180 prepared-resource checks pass. The historical save reader verifies 13,824 stored biome values as bounded cross-revision evidence.

The preceding dev6 package passes three-mod ZIP/MRPACK round trips and actual-window Vulkan presentation. Dev7 is a separate final artifact test; its run selects three classic variants. The earlier dev5 all-17 run checks 56,832 stored values. The historical failed run, failed preference-order guard, CRT diagnostic and their separate corrections remain preserved.

All seven source CI jobs pass. The static launcher passes 607 tests with eight intentional ignores, cached native-build and strict ownership-gate checks. Launcher/client import checks pass with system DLLs only. Sampled Java terrain observations match in debug and release profiles. These checks do not establish general frame rate or a controlled full-client speedup.

### Known limits

GUI Play is blocked by the computer-use runtime failing before initialization; authenticated Play is untested. Arbitrary modpacks, dedicated servers, other OS clients, old-save runtime upgrades, sustained background-ring overlap and complete Java feature/scenery parity are unqualified. The original unexplained exit did not recur in later completed runs, but its historical cause remains unknown. The long TerraForged Mods row clips warning text, while name/version/ON remain readable. Treat this as a preview rather than a general modpack-ready release.

Exact source pins: native `ed818ecc0371e1627192e1abdccb0a744f51f890`, Horizon `f43eebfc04b73f0c2bbf5048f7a3ab36c240f21d` (merged through host PR13), horizon-mixins `e8cd0aa38cffef49cb2e088ef716baa107148c02`.

Read the [reviewed launcher/modpack report](https://github.com/TheApple05/TerraForged-Horizon/blob/main/docs/horizon/native-launcher-modpack-validation.md), [immutable final evidence](https://github.com/TheApple05/TerraForged-Horizon/tree/main/docs/validation/horizon-native-launcher-dev7-v1), [fir investigation](https://github.com/TheApple05/TerraForged-Horizon/blob/main/docs/horizon/native-fir-investigation.md) and [exit investigation](https://github.com/TheApple05/TerraForged-Horizon/blob/main/docs/horizon/native-exit-investigation.md).

Based on TerraForged and ReTerraForged; independent and unofficial. Native port and launcher are MIT licensed; retained upstream notices accompany their sources/packages.

🤖 Generated with [Codex](https://openai.com/codex/)
