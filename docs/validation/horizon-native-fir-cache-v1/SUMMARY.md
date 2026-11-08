Cache diagnostic evidence prepared for review; nothing published. All 15 children exited zero with unchanged inputs. Production defaults at measurement stayed capacity 8 / max-in-flight 4. No executable, world, account or prepared-resource files are included.

Radius 12 used capacity 8 checksum `15e9296ae1b6c062` as its observation baseline. Capacities 16 and 32 matched; this establishes cross-capacity consistency only, not independent Java parity. Shared host workload was uncontrolled.

- Radius 12 capacity 8: 183.7678288s pipeline, 189.781s child; at least 266 builds, at least 237 repeated misses, at least 257 evictions; peak RSS 970907648 bytes (925.930 MiB).
- Radius 12 capacity 16: 35.2284698s pipeline, 40.875s child; 127 builds, 90 repeated misses, 111 evictions; peak RSS 970350592 bytes (925.398 MiB).
- Radius 12 capacity 32: 13.3830625s pipeline, 19.781s child; 40 builds, 3 repeated misses, 8 evictions; peak RSS 971587584 bytes (926.578 MiB).

Capacity 8 radius 12 reached the 2,000-event trace cap. All its cache counts/wait sums are lower bounds; wall time, checksum and RSS remain complete. Capacity 16 and 32 traces did not truncate. See per-run JSON for MISS/build/wait counts, exit codes and ordered records.

Radius 6 confirmation ran three alternating pairs 8/16. Ordered pipeline seconds: 20.351406, 6.4460086, 20.2901111, 6.4017758, 21.3626987, 6.3859671. Builds: 70, 20, 65, 20, 73, 20. Descriptive medians: capacity 8 20.351406s / 70 builds; capacity 16 6.4017758s / 20 builds. All matched prior stock checksum `d5f67a39776cb08d`. The unchanged raw runner retained legacy compiler-contention labels; active compilers were not assumed for confirmation.

No sustained background-ring acceptance is claimed. The flag was measured-generator-only; fast capacity 16/32 background trials showed only the local 20 miss keys. Mesh was disabled. New-package client/default-view validation remains required.

The build raw guard remains failed because a single approved measured-only-background source amendment occurred during dependency compilation; Cargo exited zero. A separate reviewed reconciliation records the amendment and final input hashes. Its raw receipt was preserved, not rewritten.

The provenance JSON gives exact executable/runner/diff/report/inventory hashes and safe workload/build recipes. Full raw report/fingerprint inventories remain local. Exact stdout/stderr copies are under logs/ and their hashes are recorded in summaries and SHA256SUMS.txt.
