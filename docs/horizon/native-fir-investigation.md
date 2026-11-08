# Fir-forest loading investigation

Investigation date: November 7, 2026 (Pacific). Native.dev5 reaches visible fir forest, but earlier all-17 sequences recorded roughly 180–184 seconds at this target. Those are live-client observations, not isolated generation times. Subsequent tracing establishes repeated tile construction in the measured streaming pipeline. Native.dev7 raises the bounded cache from eight to 32 completed tiles; updated-client acceptance remains separate from these diagnostics.

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

The actual game also starts a background stronghold-ring search, which the original batch and pipeline probe omit. That search can query remote mapped biomes through the same sampler. The subsequent QA copy can enable this search only for its measured generator. At capacity eight its trace includes remote keys, but the faster 16/32-tile trials contain only local keys. Those trials do not establish sustained background-search overlap or its full live-client cost.

A separate source-only QA workspace adds bounded miss/eviction/wait tracing and optional background-ring/capacity experiments. These overrides and trace code are absent from the production package. The [unaltered evidence export](../validation/horizon-native-fir-cache-v1/SUMMARY.md) retains 30 exact logs, three compact run summaries, source/runner diffs, provenance and hashes for all 15 child processes. Its [independent review](../validation/horizon-native-fir-cache-review-v1.json) checks the metrics and raw logs. Full raw reports and fingerprint inventories remain locally preserved under their recorded hashes.

## Capacity decision

At radius six, three fresh alternating 8/16-tile pairs take 20.351/6.446, 20.290/6.402 and 21.363/6.386 seconds. Capacity eight completes 70, 65 and 73 tile builds for the same 20 keys; capacity 16 completes 20 each, with no repeated misses. Every run matches the prior stock block/light checksum `d5f67a39776cb08d`.

The host's default viewing distance is 12, and the probe sets the same streaming radius. A separate larger workload produces 529 lit columns:

- Eight tiles: 183.768 seconds; at least 266 completed builds and 237 repeated misses. Its 2,000-event trace limit makes cache counts and wait sums lower bounds.
- 16 tiles: 35.228 seconds; 127 completed builds and 90 repeated misses.
- 32 tiles: 13.383 seconds; 40 completed builds and three repeated misses.

All three exit zero and match the radius-12 capacity-eight observation checksum `15e9296ae1b6c062`. This is cross-capacity consistency, not an independent Java reference or byte-for-byte world comparison. Source, executable and checked resource hashes remain unchanged. Their own-process peak working sets are approximately 925–927 MiB; that observation does not imply the larger cache costs no memory.

These are ordered observations on a shared, uncontrolled host, with meshing disabled. Radius 12 has one observation per capacity. The repeated smaller workload and measured rebuild counts support choosing the existing supported maximum of 32 rather than tuning only for radius six. They do not establish a general speedup, frame rate, complete loading time or broad modpack performance. Concurrency remains four; no worker cap, generation algorithm, saved preset or schema changes.

## Memory and correctness checks

The [compiler-layout receipt](../validation/horizon-native-cell-layout-v1.json) verifies a 96-byte `Cell` with the actual Rust 1.99.1 GNU compiler/target and the exact packaged source. At factor three with the builtin one-chunk border, 32 tiles retain at most 75 MiB of cell backing, 56.25 MiB more than eight. Four simultaneous builds add at most 9.375 MiB of backing. Two-chunk-border presets retain 108 MiB plus 13.5 MiB building. These are per-sampler payload calculations; caller-retained Arcs, allocator/map overhead, filter scratch and river caches are additional.

The [existing lifecycle checks](../validation/horizon-native-cache-dev7-lifecycle-v1.json) pass five tests in each debug/release profile: failed/unwound work retries, LRU ownership/eviction, same-key construction sharing, clear during construction and bounded distinct-key concurrency. Generated-cell and genuine new-package client/save qualification are tracked separately.

The diagnostic build's raw input guard remains failed because one explicitly approved measured-only-background correction happened during dependency compilation. Cargo exited zero, and the separate reconciliation records exact before/after hashes and timing. The failed raw receipt was preserved. No failed runtime result was relabeled as passing.

## Installed native.dev7 follow-through

The [final launcher/client report](native-launcher-modpack-validation.md) now records a genuine source build and two clean installed-client exits. At live render/simulation distance 12, fir forest reaches all 637 tracked columns and settled queues in 26.313 seconds. The other selected targets, save/reopen and custom-content persistence pass. This one observation includes the real client; it does not convert the diagnostic series into controlled full-client performance evidence. All 15 final images were inspected. The sampled Java kernel regression matches in both debug/release profiles.
