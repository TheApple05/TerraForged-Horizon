# TerraForged for Horizon

An independent, **unofficial native Rust port of TerraForged** for [Horizon](https://github.com/TheApple05/horizon), targeting Minecraft **26.3**.

The **Minecraft Java 26.2 Fabric and NeoForge port** lives separately in [TerraForged-26.2](https://github.com/TheApple05/TerraForged-26.2).

## Development status

This is an experimental source-built port. All 17 classic variants occur in live queries and generated chunks. The earlier all-17 client/save test verifies 56,832 stored biome values. Native.dev7 completes genuine launcher installation/build and a final installed-client create/save/reopen run at render/simulation distance 12. Both clients exit zero; all 15 images are reviewed. Representative three-mod ZIP/MRPACK round trips pass with the preceding dev6 package. See the [launcher and modpack report](docs/horizon/native-launcher-modpack-validation.md) for exact artifact identities and limits. GUI/authenticated Play, arbitrary modpacks, controlled general performance and complete source-feature fidelity remain unqualified.

See [classic runtime integration](docs/horizon/classic-runtime-integration.md), [native world selection](docs/horizon/native-world-selector.md), [current-engine client evidence](docs/horizon/current-engine-client.md), and the [component overview](horizon/README.md) for the exact scope. The older finite prepared-world bridge is retained separately from procedural generation.

The [reviewed issue and recovery report](docs/horizon/issues-2026-11-07.md) records CI recovery, loading observations, incomplete acceptance gates, and retained failed attempts.

The native.dev5 [carver performance update](docs/horizon/native-carver-performance.md) preserves six exact terrain snapshots and reduces median generation time for the measured batch from 5.98 to 1.85 seconds. Native.dev7's [fir-forest investigation](docs/horizon/native-fir-investigation.md) identifies tile-cache rebuilding and retains the distance-12 working set, at a default retained tile-payload cost of 75 MiB per sampler (56.25 MiB more than before). Controlled full-client performance and sustained background-ring overlap remain unqualified.

## Experimental download

The [native.dev7 release](https://github.com/TheApple05/TerraForged-Horizon/releases/tag/v0.1.0-native.dev7) includes the tested source HMOD, compatible static Windows x64 launcher and checksums. All public downloads were checked against the local qualified bytes. Read the [installation notes and remaining limits](docs/horizon/native-dev7-release.md) before using it in a pack.

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
