# SSD native-client world generation checks

The [SSD evidence](../validation/horizon-native-client-ssd-worldgen-v2.json)
qualifies targeted Windows Horizon 26.3 client stability for the local smoothing
optimization and Terrace NaN guard. It does not establish a consistent
whole-client speedup. The earlier
[filter-only benchmark](../validation/horizon-worldgen-speed-stability-v1.json)
measures about half the smoothing time; that result must not be presented as a
whole-world generation improvement.

The comparison uses native.dev7 baseline `ed818ec` and patched `3770a60`, both
optimized `fast` builds of host `f43eebfc` and mixins `e8cd0aa`. Their 84 staged
inputs and packaged mod sources differ only in `graph.rs` and
`tile_filters_basic.rs`. Executables, packages, prepared resources, scratch homes,
saves, logs and temporary files use ordinary files on C: NVMe SSD. The earlier
D: HDD benchmark driver and client were stopped; other clients were left alone.
No compiler runs overlap these tests. Existing game resources are copied;
game assets and test worlds are not committed.

Four fresh structures-disabled spectator worlds run in baseline, patched,
patched, baseline order. Each uses seed 8675309, four shared workers, render
distance 12, simulation distance 5, a 60 FPS cap and the actual offscreen
1280x720 Vulkan renderer on an RTX 3090. Each world visits cold fir forest,
cold steppe and Bryce destinations, saves, exits, reopens in a fresh process,
and generates a previously absent distant region.

Median teleport-to-settled-view waits, with two observations per build, are:

- Fir forest: baseline 25.34 s; patched 27.98 s.
- Cold steppe: baseline 25.36 s; patched 22.48 s.
- Bryce: baseline 33.55 s; patched 32.84 s.

Initial process-launch-to-settled-view observations are also retained: baseline
114.34/110.61 s and patched 131.53/139.61 s. The candidate was slower in both
startup observations. Other Horizon clients and host load were uncontrolled;
these small samples cannot attribute a speed change to the patch. Generation
and lighting quiet, target residence, server quiet and settled rendering are
recorded separately. Readiness requires the requested position and loaded block,
at least 361 resident chunks, two fresh quiet server samples and stable client
counts for at least one second. Retained proto chunks outside the view can
persist; this is not an exact map-coverage proof. `generated_chunks` includes received/disk-loaded
columns and is never used as a fresh-generation throughput counter.

Two further fresh worlds are created through Horizon's real UI, one per build,
with TerraForged selected, structures ON and bonus chest OFF. These use Horizon's
default workers, render distance 12, simulation distance 3 and a 30 FPS cap.
They are a separate cohort with one observation per build. Healthy grounded
survival spawn, all three biome destinations, origin, clean save/reopen and
distant terrain pass. Time from Create to observed healthy grounded spawn is
25.30 s baseline and 44.56 s patched; confirmed view is 51.64 s and 65.20 s.
The JSON retains every structures-enabled teleport wait. A desert village is
visible after reopening the patched world; full placement correctness remains
unqualified.

All six accepted worlds pass twelve clean client exits. All twelve game logs
are free of error, panic and warning markers. Complete stored biome vectors
match the native factory and differ from vanilla across 18 distinct FULL chunks
(27,648 stored quart entries). Both UI worlds retain structures enabled in saved
settings. The patched second comparison world also passes six rapid teleports,
queue drain, save/reopen and saved-vector checks; this extra stress is excluded
from speed summaries. Peak working sets are retained per process, without a
long-running memory-leak claim.

All 39 captures were reviewed: 38 pass their scoped UI or rendering smoke check.
One patched comparison reopen-initial frame has a white cloud-like overlay and
cannot qualify detailed materials. Clear primary and post-stress Bryce views
cover that location. Camera height and fog limit seam and underground inspection.

The first SSD structures baseline attempt is preserved as a failed harness run:
the timing helper reused the resource-hash variable for game status. Independent
checks found the original and copied 29 resource files unchanged. After mutation
and invalid-map regression checks, both UI variants were rerun into fresh v2
homes; the accepted runs preserve all checked input and artifact hashes. Failed
HDD and harness attempts are excluded, not relabeled as passes.

`horizon/tools/benchmark_native_client.py --self-test` checks readiness gates,
stale server samples, meshing separation and transient Windows report locks.
Its normal CLI accepts prebuilt baseline/candidate clients, a control executable,
fixture reader, copied packages, prepared resources and fresh work/report paths.
The receipt retains executable, source-stage, package, verifier, log and image
hashes, plus the local UI verifier snapshot. Long soaks, multiplayer, broader
modpacks/shader packs, all presets/biomes, whole-world Java parity, complete
structure placement and standard launcher installation remain outside this run.
