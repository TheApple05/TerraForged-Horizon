# Native.dev7 reviewed local acceptance

November 7, 2026 Pacific (November 8 UTC). Experimental Horizon 26.3, distinct from the Java 26.2 Fabric/NeoForge project.

The exact installed native.dev7 package passes local offscreen create/save/reopen acceptance with Coordinates HUD 2.0.0 and QA Glow. Both clients exit zero. All 15 raw images were inspected by Codex root and their hashes checked. Forty camera assertions pass. See [review.json](review.json), the unchanged [raw report](report.json), [driver](verify_installed_native_ui.py) and [plan](plan.json).

- All six views reach the source-backed 637 tracked columns at live render/simulation distance 12, with settled streaming/upload queues and actual geometry. Fir forest, frozen marsh and shattered savanna scrub are included.
- UI-selected TerraForged preset creates a healthy, grounded survival player with structures enabled and no supplied QA spawn.
- HUD chat/toggles, actual crafting and item placement work. Custom block/item/light state survives reopen.
- Historical reader checks 6,144 then 7,680 quart biome values. This proves bounded cross-revision reading, not exact current-engine reader qualification. The custom-content chunk is checked by the actual new client.
- Final integrity verifies 30 locked inputs and 28,180 prepared-resource files. Only the exact known preference-line sorting is allowed. The earlier failed dev6 guard remains separate and unchanged.
- Static launcher and actual game client import only system DLLs. Static launcher tests pass 607 with eight intentional ignores; genuine cached native-build and strict owner-gated Play checks pass.

The [copied-world fir close-up](fir-detail/fir-structure-close.png) shows textured white-wool stairs and three magenta cushions. The client's entity list identifies all three as magenta `minecraft:cushion`. Its client exits zero and source world/report hashes remain unchanged. This closes the visual question without changing production code. The long TerraForged Mods row clips warning text; name/version/ON remain readable.

Source preparation initially finds an existing private HUD directory; [preparation-recovery.json](preparation-recovery.json) retains this failure and recovery. The complete integrity preflight repeats before launch. The original launcher portability failure (`VCRUNTIME140.dll`) is retained under [static-launcher](static-launcher/); the qualified static rebuild uses upstream release flags.

The genuine incremental build, import and pin receipts are under [preparation](preparation/). Native package SHA-256: `ab511d1e0daa3670061a91d3ce3900127cb702ddfb60603d2d5dee9fe59fb355`. Client: `6a87351e5c85b83d728e55cfd6597cc90917b286a42fd16c8b819911fae6cd85`. Static launcher: `0d5f250705896eeded0e6800c03de961835bcd389f96d6ba908fe2bdb598f468`.

GUI Play remains blocked by missing computer-use kernel assets, before initialization. Authenticated Play, fresh public installation/sign-in, other OS clients, dedicated servers, arbitrary modpacks, sustained ring overlap, general FPS and whole-feature Java scenery parity are unqualified. The original unexplained exit cause remains unknown; later clean exits cannot recover it. No runtime old-save upgrade test was performed. Exact source/package scopes matter: the earlier all-17 test used dev5; this dev7 run selects three variants.

Minecraft resources, saves, executables and account files are excluded. Raw metadata and source drivers retain local QA paths. `SHA256SUMS` covers the frozen export; `SUMMARY.md` is explanatory documentation added after that snapshot. The exporter verifies raw statuses, hashes, camera/visibility predicates, save fingerprints and copy bytes before producing a separate review receipt; raw reports are never relabeled.
