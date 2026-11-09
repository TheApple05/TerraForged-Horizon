# TerraForged for Horizon

An independent, **unofficial native Rust port of TerraForged** for [Horizon](https://github.com/TheApple05/horizon), targeting Minecraft **26.3**.

The **Minecraft Java 26.2 Fabric and NeoForge port** lives separately in [TerraForged-26.2](https://github.com/TheApple05/TerraForged-26.2).

## Windows 0.1.0

The first stable release targets **Windows x64 Vulkan, Minecraft 26.3, singleplayer and the bundled default preset, with TerraForged alone**. Download [TerraForged 0.1.0](https://github.com/TheApple05/TerraForged-Horizon/releases/tag/v0.1.0), then follow the [Windows installation guide](docs/horizon/windows-0.1.0-release.md). It includes the native source HMOD, compatible launcher, matching project source and checksums. Native compilation and your own Minecraft resources are required.

**Customize is disabled in 0.1.0.** A working [native Customize preview](docs/horizon/native-preset-customize.md) now follows this release; it is separate from the frozen stable assets. [Official Nightly compatibility work](docs/horizon/nightly-port.md) is in progress and the mod-page submission remains draft. Other operating systems, multiplayer/dedicated servers, arbitrary modpacks and complete historical Java feature/scenery parity remain unqualified; this release does not certify the whole Horizon client.

The exact installed candidate passed authenticated launcher Play, default survival creation/death/respawn, three additional seeds, preview-world upgrade and an intentionally interrupted generation/recovery case. A 45-minute exploration run visited all 17 classic targets and 156 fresh central regions, saved and reopened cleanly. Independent readers checked 84,480 saved biome values across these cases, including repeated origin checks. Windows GNU uses the system allocator after the earlier candidate's excessive private-commit growth. See the [selected final evidence](docs/validation/horizon-0.1.0-v2/SUMMARY.json) and [qualification history](docs/horizon/stable-release-readiness.md) for exact identities, camera limits and retained failed attempts. These are functional checks, not an isolated FPS or multi-hour benchmark.

See [classic runtime integration](docs/horizon/classic-runtime-integration.md), [native world selection](docs/horizon/native-world-selector.md), [current-engine client evidence](docs/horizon/current-engine-client.md), and the [component overview](horizon/README.md) for the exact scope. The older finite prepared-world bridge is retained separately from procedural generation.

The [reviewed issue and recovery report](docs/horizon/issues-2026-11-07.md) records CI recovery, loading observations, incomplete acceptance gates, and retained failed attempts.

The native.dev5 [carver performance update](docs/horizon/native-carver-performance.md) preserves six exact terrain snapshots and reduces median generation time for the measured batch from 5.98 to 1.85 seconds. Native.dev7's [fir-forest investigation](docs/horizon/native-fir-investigation.md) identifies tile-cache rebuilding and retains the distance-12 working set, at a default retained tile-payload cost of 75 MiB per sampler (56.25 MiB more than before). Controlled full-client performance and sustained background-ring overlap remain unqualified.

## Earlier preview

The [native.dev7 release](https://github.com/TheApple05/TerraForged-Horizon/releases/tag/v0.1.0-native.dev7) remains an experimental preview. Its [installation notes](docs/horizon/native-dev7-release.md) describe that older artifact; use the 0.1.0 guide for the stable release.

## Build and verify

With stable Rust installed, from this repository root:

```sh
cargo test --locked --manifest-path horizon/native-core/Cargo.toml --lib
cargo check --locked --manifest-path horizon/native-adapter/Cargo.toml --all-targets
python horizon/tools/verify_native_scalars.py
```

Native builds and fixture-only checks, including the scalar, utility, and classic-biome verifiers, do not require Java. Regenerating or capturing Java references, and checks that additionally validate Java producer source such as pillar math, require an explicit checkout of the [Java port](https://github.com/TheApple05/TerraForged-26.2):

```powershell
$env:TERRAFORGED_JAVA_ROOT = 'C:\path\to\TerraForged-26.2'
python horizon/tools/generate_noise_vectors.py
python horizon/tools/install_biome_table.py
```

Reference CI pins Java commit `c7a477a4a272ef34df9d3f55a95f185f264b40ec`. Java runtime captures also require that checkout's matching Java 25 build/classpath and the exact production JAR requested by the capture tool.

Full engine integration uses the pinned Horizon and horizon-mixins revisions documented by the staging tools. Use your own locally prepared Minecraft resources; game files and terrain snapshots are not included in this repository or its source packages.

## Layout and provenance

- `horizon/`: native code, content, tools, fixtures, and the earlier prepared prototype.
- `docs/horizon/`: design notes and integration checkpoints.
- `docs/validation/`: retained reports, including failed historical attempts.
- `tests/core/`: shared frozen Java reference observations, used only for verification.

The [repository split record](docs/REPOSITORY-SPLIT.md) explains the extracted history and Java reference boundary.

## Credits and license

Based on the original [TerraForged](https://github.com/TerraForged/TerraForged) by dags, Won-Ton, and contributors, and [ReTerraForged](https://github.com/racoonman2/ReTerraForged) by racoonman2 and contributors. This is not an official release of either project.

The native port is [MIT licensed](LICENSE). Original TerraForged, ReTerraForged, and Noise2D notices are retained under `licenses/`; Horizon and horizon-mixins notices remain with their integration components. The Java port's separate LGPL LanguageProvider implementation is not included here.
