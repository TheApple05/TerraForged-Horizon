# Stable release qualification

Target: Windows x64, Horizon / Minecraft 26.3, default TerraForged preset.
Status: **not yet qualified for stable**. A date is not an acceptance result.

The published native.dev7 remains an experimental preview. The smoothing and
terrace fixes on this branch are a candidate; existing client binaries and
reports identify their exact source/package hashes, not a future stable build.

## Required before publishing stable

- Download the final public launcher and HMOD into a clean installation. Follow
  only the public instructions, including resource preparation and native trust.
  Complete ownership-checked sign-in/session import and GUI Play, create a world, save and reopen it, and
  exit cleanly. Privately copied prepared resources and direct-client runs do
  not satisfy this gate.
- Freeze the final source revisions, build profile, launcher, HMOD and SHA-256
  checksums. Qualify those exact artifacts; downloading the published bytes must
  reproduce their hashes. Source-built candidate tests alone do not qualify a
  differently built release.
- Run default survival creation with structures on across multiple seeds,
  distant exploration and biome boundaries, repeated saves/reopens, death and
  respawn, and an extended generation session. Preserve logs, screenshots,
  process exits and save checks; investigate crashes or generation stalls.
- Exercise interrupted-save recovery only on disposable copies. Check upgrades
  from each preview declared supported, preserving backups and checking world
  settings, terrain, inventory and modified blocks after reopening.
- Record client loading, memory and frame-pacing behavior on the supported
  configuration. Comparisons must exclude other Horizon clients throughout
  the run and report other host load. Kernel timings are separate evidence.
- Pass source CI and final installed-client tests with the supported companion
  mods. Review actual images and resolve defects affecting normal play.

Dedicated servers/multiplayer, other operating systems and particular modpacks
must each be qualified before being advertised as supported. Full historical
Java scenery parity is not a stable prerequisite, but differences must be
documented. Do not silently exclude save reliability or sustained exploration.

## Evidence already available

- [native.dev7 installation and client scope](native-launcher-modpack-validation.md):
  installed client, distance-12 views, crafting and block/item/light persistence.
- [Prior all-biome and current client evidence](current-engine-client.md).
- [Candidate SSD client observations](ssd-worldgen-client.md): six worlds and
  twelve clean exits; host contention prevents a controlled performance claim.
- [Smoothing and terrace evidence](../validation/horizon-worldgen-speed-stability-v1.json).
- [New client-isolation qualification](../validation/horizon-stable-client-isolation-v1.json):
  four fresh worlds, eight zero exits and 12,288 saved biome values. All eight
  processes were observed without another Horizon client. Root reviewed the
  25-image contact sheet; three cloud-obscured views cannot qualify detailed
  scenery. Launcher compilation overlapped the later comparison worlds, so
  this is functional reliability evidence, not a controlled speedup result.
- [Fresh targeted source regressions](../validation/horizon-stable-source-v1/SUMMARY.json):
  eight core tests in each profile, final-noise and tile-filter Java references,
  196,608 sampled columns per profile, and cache lifecycle checks all pass in
  debug and release.

The client benchmark now has an optional `--exclusive-clients` guard. It refuses
to start alongside another Horizon client and samples for new clients every
250 ms throughout the owned process. Detection or scan failure invalidates the
run; it never terminates unrelated processes. Self-tests run on Windows/Linux CI.
This reduces one known timing confounder; it does not control all host load.

## Historical launcher blocker

Earlier launcher capture attempts timed out; computer use is now off at the
user's request. The published dev7 static launcher also rejects
`account sign-in` because no `HORIZON_MSA_CLIENT_ID` is configured. No approved
project-owned application ID is available. Horizon's own Microsoft sign-in
flow therefore remains unqualified. Do not borrow another launcher's OAuth ID.
The supported candidate alternative is the explicit Prism session import below.

## Verified Prism session path (new launcher candidate)

[Horizon PR14](https://github.com/TheApple05/horizon/pull/14) adds an explicit
Prism session import without using Prism's Microsoft refresh token or OAuth app
ID. The active session passes Minecraft's live ownership and matching-profile
checks and the launcher's forced Play authentication check. The user confirms
normal GUI Play reached an in-game world. This is user-reported launcher Play
acceptance; the world preset was not independently inspected, and this does not
qualify a final packaged TerraForged candidate or Horizon's own OAuth flow.

The static Windows candidate passes 512 library tests and 97 executable tests
(eight intentional ignores total), warnings-denied Clippy and the system-DLL
import check. The generated command reference is updated. Session expiry still
requires refresh in Prism and reimport. No account files or identifiers belong
in published evidence. Computer use was stopped at the user's request.

## Exploration attempts and coordination

The first extended run was rejected when another Horizon client started. A
later cold-region harness incorrectly rejected intentional revisits; its raw
failure is preserved. The next two attempts lost their game/control connection.
One cleanup initially obscured the natural exit code by terminating the process
too soon; the helper now allows five seconds to observe natural completion.
Five shutdown/UI regression tests pass, including a real child exiting after
its control connection closes.

The repeat captures exit **0** without forced termination. Inspection of the
active chat **Improve Horizon world gen** then establishes external cancellation:
that chat explicitly issued `quit` to the exploration-v3 and exploration-v4
control endpoints to run exclusive measurements, and parked the v2 test EXEs.
Its `live-runtime-v3/setup/closed-other-client.json` independently records the
v3 PID, endpoint, successful quit and timestamp. These are cancelled tests, not
evidence of a reproduced runtime crash. Raw failed verdicts remain unchanged;
the older historical unexplained exit is not resolved by this finding.

Do not launch competing clients or restore parked binaries while that exclusive
job is active. A completed extended exploration/save/reopen test, multiple
seeds, interrupted-save recovery, supported preview upgrades and final exact
release-artifact qualification remain open.

## Multi-seed and metadata recovery diagnostics

[Three-seed candidate checks](../validation/horizon-seed-recovery-v1/SUMMARY.json)
pass for seeds 0, -123456789 and 9223372036854775807. Real world-creation controls
select TerraForged with structures enabled and healthy natural survival spawn.
All six client processes exit zero; 13,824 stored-quart comparisons match the
exact staged native generator. Every selected vector distinguishes it from vanilla. Each seed has a distinct saved
fingerprint tuple. The negative seed also passes death-screen and healthy,
grounded survival respawn state checks. All 13 images were reviewed. Its fixed
distant camera is underground, its respawn image retains a loading overlay, and
foliage obscures the signed-max spawn's distant view; those images do not qualify
surface scenery. These are functional source-built diagnostics, not final
installed-package or performance acceptance.

A copied baseline scratch save passes real metadata recovery: refusal when both
metadata files are invalid; rollback when Windows locks the valid backup; then
successful restoration preserving the corrupt current file. The original save
is unchanged, and the exact-host reader verifies the recovered preset, seed and
saved FULL biome vectors. This does not simulate a power loss or interrupted
region-sector writes.

A separate clean installation successfully downloads public base v0.2.97,
imports a live ownership-checked Prism session, prepares resources through
`prepare --minecraft` using the user's own Prism installation, and provisions
the pinned Rust toolchain. No privately prepared-resource tree is copied into
that installation. Its [safe preparation receipt](../validation/horizon-seed-recovery-v1/public-install-preparation.json)
records the unrecognized sound-index warning and successful per-file validation.
The final HMOD, exact installed native build and Play gates remain pending.

## Frozen 0.1.0 candidate and manual-install correction

The [0.1.0 qualification candidate](https://github.com/TheApple05/TerraForged-Horizon/releases/tag/v0.1.0-rc.1)
contains the frozen HMOD, compatible launcher ZIP, native source ZIP and
checksums. All four public downloads match their local hashes. The new HMOD's
entry set is unchanged from the tested source candidate; every generation-code
and content byte matches. Only four metadata entries change version/display
text and the README heading. This is not final installed-client acceptance.

The fresh public installation exposed an omitted manual-setup step. A copied
native archive remains off until `horizon-mods.txt` explicitly contains
`mod.terraforged_native:true`. The CLI `mods enable` only resolves entries the
browser installed, so it cannot enable this manually placed archive. The
[Windows instructions](windows-0.1.0-release.md) now include that line while
preserving other preferences. Both the original refused build and rejected CLI
enable attempt remain recorded. The next attempt passes the trust refusal,
compiles the actual downloaded HMOD and installs native version
`native-f43eebf-99bd42e244c2`. Its record contains only TerraForged 0.1.0 with the
intended engine and mixin pins. The installed client SHA-256 is
`011349e00fd1918c62cf23a9a5dabc342cce4ecac131710c0788a79e99b7b8ce`.

Public `prepare --minecraft` exits zero for that version too. The QA wrapper
then rejects an obsolete development-only `horizon-prepare.json` requirement.
That raw failure is preserved; a separate validation uses the launcher's actual
`horizon-resources.json`, verifies the manifest's facts digest and hashes the
required facts/worldgen files. The shared QA resource check now accepts public
preparation while still hashing an optional development receipt when present.
Eight UI/setup/shutdown regression tests and the readiness self-test pass.
Installed world creation, sustained generation, upgrade and Play acceptance are
now running or pending; the successful build alone does not qualify them.

Authenticated CLI Play then creates a default TerraForged survival world with
structures enabled, a healthy grounded player and a clean exit. Its first-run
accessibility Continue action and image review are recorded. The user also
confirms normal GUI Play and new-world entry with this exact candidate profile,
while reporting the disabled Customize button. The native preset editor is
unimplemented; the Windows guide now states that limit prominently.

The first final-client classic tour is deliberately cancelled by its owner
after reaching fourteen views: its strict readiness predicate waits for all
client meshing to stop at stone forest, despite complete generation and 637
resident columns. The pinned engine explicitly includes block/light/fluid
remeshing of already drawn sections in that counter. This is an unaccepted
attempt, with the raw failure, clean quit and cancellation explanation retained.
The benchmark still requires full mesh idleness by default. A separate explicit
functional policy permits ongoing client remeshing while requiring complete
residence, quiet server generation/lighting, stable visible renderer residence,
and no pending chunks/uploads; it records the actual meshing count. Self-tests
verify that active generation, missing target residence and pending uploads
still refuse readiness. A fresh all-classic/extended run uses this policy.

The first interruption scenario also remains unaccepted: generation becomes
quiet before its fresh region is saved, so it times out without killing the
client. The replacement first saves one corner of a distant region, checks
that the intended next chunk's Anvil header slot is empty, then interrupts new
generation in that region. Neither scenario claims to simulate torn sector
writes or a power loss.

The fresh functional tour renders all seventeen targets and completes fifty-one
new central regions. It is then deliberately stopped for Windows commit
headroom, before the required forty-five minutes. The owned test process has
19,714,428,928 private bytes, 3,581,722,624 resident bytes and 63 threads at the
stop. Its raw failure and explicit owner-stop receipt remain unchanged; it is
not a spontaneous crash or an accepted sustained run. Growth continues across
a structure-cache rollover, so bounded chunk/cache entry counts do not establish
safe memory use. A title-only diagnostic attributes a smaller increase to new
control connections; stationary-world connection reuse and a diagnostic-only
live-allocation census are being checked. Stable promotion remains held until
the growth is explained or fixed and sustained qualification completes.

The [selected final-package results](../validation/horizon-0.1.0-v1/SUMMARY.json)
already retain the bounded installed multi-seed, Play and copied-world recovery
checks without publishing account files, resources or worlds. Their overall
status explicitly keeps this memory gate open.
