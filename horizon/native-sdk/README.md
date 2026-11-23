# TerraForged density functions for Horizon's native SDK

The SDK route starts with the bundled TerraForged kernel. A datapack density node can use
`{"type":"terraforged:cell","field":"height"}` or another name from `CellField`.
`"quantize_height":true` selects TerraForged's quantized height calculation.
The mod registers a type and only runs terrain sampling when a density graph calls it.

Verify the source against a clean checkout of Horizon `f1bb66f353cf67f2aa4665293fc75c8d91186fc7`.
Fetch the checkout's locked Cargo dependencies before running the offline check.

```sh
python horizon/tools/check_native_sdk.py --horizon /path/to/horizon --output build/qa/sdk-check
python horizon/tools/stage_native_sdk.py --output build/qa/sdk-mods/terraforged
horizon-launcher native-build build/qa/sdk-mods --version nightly-2026-11-22-f1bb66f --trust-native-code
```

This package is a development checkpoint. A playable preset also needs a port of
the terrain router, per-world settings and biome selection. TerraForged's classic
pillar and marsh features still need a native configured-feature type API.
Existing TerraForged worlds use the legacy patched runtime until a migrated world
passes independent saved-chunk and generation checks.
