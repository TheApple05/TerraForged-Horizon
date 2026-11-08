# Native client exit investigation

The saved evidence confirms that the client exited during the shattered-savanna visibility check. It does not identify the cause, the exit code, or who ended the process. This failed run does not establish create/save/reopen acceptance.

All times below are UTC on **2026-11-08**. The game log uses local Pacific time on November 7, eight hours behind UTC. Paths are relative to `C:/Users/Main/Documents/Codex/TerraForged-Horizon-performance`.

Investigation date: November 7, 2026 (Pacific).

## Evidence inspected

- Failed report: `docs/validation/horizon-native-classic-ui-uniform-v2.json`; SHA-256 `075c8d244783c97bbf598220236b31e7f8b306460c36f8fcf92a65540a34eee0`.
- Runtime directory: `build/qa/horizon/native-uniform-carvers-v1/horizon-native-classic-ui-uniform-v2/`.
- Its `game-0.log`; SHA-256 `be50cb0bd7a8502b2ee20a9771d9d0cf13f4de0c51c07b2d50d775e1eaee12a6`.
- Its saved `verifier-source.py`; SHA-256 `3af8b24d3939a03a335ad94f3c7e3d193ed719de7580dde8b539048bfd9bdc04`, matching the report.
- Read-only metadata from its owned QA world, `homes/horizon_home/saves/TerraForged UI QA/`: compressed `level.dat` and `level.dat_old` LastPlayed fields, file timestamps, and dimension-region file metadata. The original world was not opened in a client or rewritten during historical inspection.

## Proven facts

1. The report started at `00:16:01.886848` and finished with status `failed` at `00:38:30.989112`. Its recorded Horizon revision is `1860b66439c6c0c07afd1a13252c1cf9405fb38e`.
2. The verifier reached natural spawn and recorded ten classic rendered views. Its last visibility check started at `00:38:27.820957` for `reterraforged:shattered_savanna_scrub`, target `[100428, 74, 42832]`, and failed with `Client exited while loading reterraforged:shattered_savanna_scrub`. `runs` is empty: the verifier did not reach its completed save-validation/reopen result.
3. `level.dat` records LastPlayed `00:36:49.326`; its filesystem write time is `00:36:49.337075`. The previous metadata save records LastPlayed `00:31:49.324`. These are consistent with periodic saves five minutes apart, not proof of a final shutdown save.
4. The log ends with the teleport to `100428.5, 122, 42832.5` at local `16:38:26`. The latest inspected overworld region write is `00:38:26.8935106` (`dimensions/minecraft/overworld/region/r.138.-81.mca`). Region writes can occur without a final metadata save.
5. The saved log contains no final-save completion, panic, or explicit crash message. The failure report says the checked original and copied resource files were unchanged. Neither observation excludes a crash or external termination.
6. The historical report contains **no** `clientExitCodeOnError`, `clientExitOnError`, `clientLaunches`, or `clientCleanup` field. Its saved verifier checked whether the child had exited, but did not persist the code in the error path or record cleanup actions. The process exit code is not recoverable from these artifacts. The report completion time bounds the observation; it is not an exact process-exit timestamp.

## Unknown and excluded conclusions

- There is no preserved exit code, dump, termination audit, or caller identity establishing whether this was a client fault, an operating-system action, or an external process ending the client.
- The earlier event check reported no Application 1000/1001 or System GPU events in its checked window. Security access was denied and Sysmon was absent. Those are prior-session observations supplied for the historical-artifact review, not event queries repeated here; absence of those records does not identify a cause.
- Evidence about another project's updater does not establish a causal connection to this client. No unrelated project was inspected for this draft.
- The last metadata save predates the observed exit. That supports “no final metadata save is evidenced”; it does not prove every region write was lost, that the world was corrupted, or that cleanup killed the client.

The new verifier exit capture improves future evidence. It cannot reconstruct the missing historical exit code or turn this failed run into a passed run. No new client, build, event query, or system-setting change was performed during the historical-artifact review.

## Copied-world reproduction

The [new read-only-source reproduction receipt](../validation/horizon-native-failed-world-reopen-v1.json) records an ordinary copy of the failed world, the exact qualified native.dev5 client and HMOD, and seven isolated homes. The original world was never opened in a client.

On November 8 at 02:06:32 UTC, PID 30532 reopened the copy, visited shattered savanna scrub and fir forest, captured both views, and quit through the control endpoint at 02:08:32 UTC with exit code 0 (`0x00000000`). The raw receipt SHA-256 is `2fcaa78cd2bb24e6d4fbd46635a2488b5ad7d0fd35416af4c8e4f66351adddc0`. Original-world hashes, checked prepared resources and pinned artifacts remain unchanged. The [separate review receipt](../validation/horizon-native-failed-world-reopen-review-v1.json) records both PNG hash checks and independent image inspection; the high camera and render-distance-six cutoffs limit the visual conclusion. This run did not compare full saved biome vectors.

The shattered target region was absent from the failed original and allocated in the saved copy after the successful visit. This is a region-header observation, not proof of complete chunk contents or recovery of unsaved data. The original evidence remains intact.

The copied world did not reproduce the exit. That result does not identify or fix its historical cause. A fresh cold-steppe-first all-17 create/save/reopen repetition is tracked separately. Both runs use explicit nonperformance labels because compilation may overlap them.

## Future exit evidence

The UI verifier now records each launch PID and command, the error-time child code with an unsigned hexadecimal representation, cleanup actions applied only to its own Popen child, and the final code after cleanup. An exit already observed before cleanup is kept separate from verifier-requested quit, termination or kill. Three small shutdown regressions and the existing fresh-stage fixture regression pass. Independent review also exercised an exit between polls and a termination failure. No global crash-handler, event-audit or security settings were changed.
