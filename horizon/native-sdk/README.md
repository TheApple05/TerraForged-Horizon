# TerraForged terrain and classic biome mapper for the Horizon SDK candidate

The SDK route starts with the bundled TerraForged kernel. A datapack density node can use
`{"type":"terraforged:cell","field":"height"}` or another name from `CellField`.
`"quantize_height":true` selects TerraForged's quantized height calculation.
An optional `"preset"` object applies validated settings to that node's terrain
sampler. Its keys are the configuration pointers supported by the legacy editor.
For example, `"preset":{"/world/continent/continentScale":750}` sets the continent
scale to 750. Omitted settings use the bundled preset. Nodes with the same settings
share a sampler, and nodes with different settings can coexist for the same seed.

This branch requires the [per-world biome mapping API](https://github.com/horizon-rust/horizon/issues/20256).
Verify the source against a clean checkout of candidate Horizon `09d03862ee21197a45eaab65e23032fcc3570e77`.
Fetch the checkout's locked Cargo dependencies before running the offline check.

```sh
python horizon/tools/check_native_sdk.py --horizon /path/to/horizon --output build/qa/sdk-check
python horizon/tools/stage_native_sdk.py --resources /path/to/prepared/26.3 --output build/qa/sdk-mods/terraforged
```

On a build containing the mapper API, a biome source of type `terraforged:classic`
accepts a base source and a configuration object with the same settings as
`terraforged:cell`. The generated default preset uses its vanilla biome source
until the classic feature types can also be registered.

`--resources` uses the local prepared 26.3 worldgen registries to add **TerraForged**
to the Create World type selector. The generated preset embeds its own Overworld
noise settings. Vanilla dimensions, biomes, and unaffected density functions
remain shared. Omit `--resources` for a source project containing only the density
adapter.

The **Customize** editor writes settings into the new world's Overworld
density nodes. Use Horizon's **Done** to commit or **Cancel** to discard them.
This candidate predates the upstream fix for restoring custom
preset identity in Re-Create. [Horizon Re-Create fix](https://github.com/horizon-rust/horizon/pull/20244)

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
