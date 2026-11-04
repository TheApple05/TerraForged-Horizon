# Horizon repository split

On 2026-11-04, the Horizon port was separated from [TheApple05/TerraForged-26.2](https://github.com/TheApple05/TerraForged-26.2). That repository continues the Java 26.2 Fabric and NeoForge mod; this repository owns the Horizon 26.3 native port.

The extraction starts from original commit [`c7a477a4a272ef34df9d3f55a95f185f264b40ec`](https://github.com/TheApple05/TerraForged-26.2/commit/c7a477a4a272ef34df9d3f55a95f185f264b40ec). Path-filtered history preserves native changes, authors, and commit messages. Commit IDs change because unrelated Java paths are excluded. [The commit map](SPLIT-COMMITS.txt) maps original IDs to extracted IDs; zero destinations are commits with no retained changes. Historical `#N` references refer to pull requests in the original repository.

## Ownership

Moved paths retain their original layout:

- `horizon/`
- `docs/horizon/`
- `docs/validation/horizon-*` and `docs/validation/server-horizon-*`
- `docs/validation/ci-native-noise-windows-fixture-failure.json`
- `.github/workflows/native-host.yml` and `native-noise.yml`

The two frozen `tests/core/reference-*` files and the TerraForged, ReTerraForged, and Noise2D MIT notices are shared reference/provenance inputs copied with their history. Java mod sources, Gradle builds, Java release assets, and ordinary Java tests remain in the Java repository.

The original [development log](https://github.com/TheApple05/TerraForged-26.2/blob/c7a477a4a272ef34df9d3f55a95f185f264b40ec/docs/DEVLOG.md) and [source provenance](https://github.com/TheApple05/TerraForged-26.2/blob/c7a477a4a272ef34df9d3f55a95f185f264b40ec/docs/SOURCE-PROVENANCE.json) remain available at that immutable source revision. Existing Java releases and evidence are unchanged.

## Reproduction boundary

Native Rust builds and frozen-fixture verification are self-contained. Reference capture and source regeneration tools read Java inputs only from the explicit `TERRAFORGED_JAVA_ROOT` checkout. Native CI pins the original Java reference commit above. Outputs remain in this repository's ignored build directories.

Historical fixture and validation report bytes are preserved. Their original machine paths, source-tree hashes, and checkpoint-specific limitations describe the recorded runs; moving the repository does not turn them into a new acceptance run. Follow the current documentation for the latest checkpoint.

No Minecraft game assets, prepared player resources, terrain snapshots, local caches, credentials, or test runtime binaries were added during extraction.
