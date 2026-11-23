# TerraForged density functions for Horizon's native SDK

The SDK route starts with the bundled TerraForged kernel. A datapack density node can use
`{"type":"terraforged:cell","field":"height"}` or another name from `CellField`.
`"quantize_height":true` selects TerraForged's quantized height calculation.
The mod registers a type and only runs terrain sampling when a density graph calls it.

Verify the source against a clean checkout of Horizon `f1bb66f353cf67f2aa4665293fc75c8d91186fc7`.
Fetch the checkout's locked Cargo dependencies before running the offline check.

```sh
python horizon/tools/check_native_sdk.py --horizon /path/to/horizon --output build/qa/sdk-check
python horizon/tools/stage_native_sdk.py --resources /path/to/prepared/26.3 --output build/qa/sdk-mods/terraforged
horizon-launcher native-build build/qa/sdk-mods --version nightly-2026-11-22-f1bb66f --trust-native-code
```

`--resources` uses the local prepared 26.3 worldgen registries to add **TerraForged**
to the Create World type selector. The generated preset embeds its own Overworld
noise settings. Vanilla dimensions, biomes, and unaffected density functions
remain shared. Omit `--resources` for a source project containing only the density
adapter.

This preset is a development checkpoint for the default terrain. The legacy
continent-centered spawn, configurable biome selection, and classic pillar and
marsh decoration still need integration. Existing TerraForged worlds use the
legacy patched runtime until a migrated world passes independent saved-chunk and
generation checks.

## Classic biome resources

```sh
python horizon/tools/stage_classic_datapack.py --resources /path/to/prepared/26.3 --output build/qa/classic-data
```

This stages the classic biome definitions, biome tag additions, and feature
definitions under `data/` for SDK integration. It resolves inheritance against
the prepared vanilla registries. The generated `required-native-features.json`
lists the two native algorithms the integrating mod needs to register.
