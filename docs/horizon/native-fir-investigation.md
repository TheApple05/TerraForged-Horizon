# Fir-forest loading investigation

Investigation date: November 7, 2026 (Pacific). The slow live-client waits remain unresolved. Native.dev5 generation reaches visible fir forest, but earlier all-17 sequences recorded roughly 180–184 seconds at this target. Those are live-client observations, not isolated generation times.

## Generation and lighting probe

The [diagnostic receipt](../validation/horizon-native-fir-pipeline-v1.json) records a QA-only copy of the pinned engine's existing `gen_light_bench`. Only its generator factory selects `terraforged:default` with structures enabled; `--vanilla` keeps the original factory. No production algorithm, cache capacity or concurrency was changed. The copied source and manifest hashes are retained.

Each separate process uses seed `8675309`, center chunk `(0, -2731)`, radius six, 15 workers and seven isolated homes. The stock probe warms a separate area first, then streams generation, decoration, final columns and light. Meshing is disabled.

- Native, coordinator period 2 ms: 28.114 seconds wall time, 149 lit columns, 285 generation jobs. Aggregate estimated worker time: generation 51.619 s, decoration 1.165 s, light 0.231 s.
- Native, coordinator period 50 ms: 30.579 seconds wall time, the same column/generation counts. Aggregate estimated worker time: generation 49.092 s, decoration 1.397 s, light 0.248 s.
- Vanilla factory, coordinator period 2 ms: 0.846 seconds wall time, the same column/generation counts. Aggregate estimated worker time: generation 3.589 s, decoration 0.420 s, light 0.242 s.

Both native settings report block-and-light checksum `d5f67a39776cb08d`. This is the existing probe's 64-bit checksum, not a byte-for-byte saved-world comparison. Every child exits zero and its executable, source and checked prepared-resource hashes remain unchanged. Original stdout/stderr logs are retained beside the receipt.

On Windows the probe's process `cpu_s` is unavailable and prints zero. Coordinator and job times are calibrated thread-cycle estimates; worker values sum across threads rather than measuring elapsed loading time. Each setting has one observation, and other project workloads were not stopped. These measurements identify generation as the main measured worker cost; they do not establish a general speed comparison, statistical improvement, modpack frame rate or live-client loading acceptance.

## What differs from the live game

The earlier 19-by-19 proto batch generated 361 protos in row order before decoration. Streaming requests 285 closest-first and overlaps stages, with at most 45 generation jobs queued/running for these 15 workers. Its biome halo has a geographic upper bound of 12 direct native tile keys, while the shared native sampler retains eight completed tiles and allows four builds. Structure-candidate queries can extend that footprint; the geographic bound is not a measured cache-miss count.

The actual game also starts a background stronghold-ring search, which the batch and pipeline probe omit. That search can query remote mapped biomes through the same sampler. Request order, cache rebuilding/waits and background searches are hypotheses for the remaining cost; none has yet been established as the cause.

A separate source-only QA workspace is being prepared for bounded cache-miss, eviction and wait tracing, with optional background-ring and cache-capacity experiments. Those overrides do not exist in the production package. The production cache remains eight tiles/four builds. Changes require measured evidence, output checks and a reviewed memory tradeoff.
