# Stable release qualification

Target: Windows x64, Horizon / Minecraft 26.3, default TerraForged preset.
Status: **not yet qualified for stable**. A date is not an acceptance result.

The published native.dev7 remains an experimental preview. The smoothing and
terrace fixes on this branch are a candidate; existing client binaries and
reports identify their exact source/package hashes, not a future stable build.

## Required before publishing stable

- Download the final public launcher and HMOD into a clean installation. Follow
  only the public instructions, including resource preparation and native trust.
  Complete real sign-in and GUI Play, create a world, save and reopen it, and
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

The client benchmark now has an optional `--exclusive-clients` guard. It refuses
to start alongside another Horizon client and samples for new clients every
250 ms throughout the owned process. Detection or scan failure invalidates the
run; it never terminates unrelated processes. Self-tests run on Windows/Linux CI.
This reduces one known timing confounder; it does not control all host load.

## Current manual gate

Windows automation can now enumerate the isolated launcher window, but its
screenshot capture times out and accessibility exposes only the window frame.
Until observed otherwise, normal GUI and authenticated Play remain unverified.
Do not reuse the earlier missing-kernel explanation as the current failure.

The actual published static launcher also fails `account sign-in` with:
`This build of the launcher has no Microsoft sign-in (HORIZON_MSA_CLIENT_ID), so it can't start the game.`
Neither a user nor machine runtime client-ID override was configured when checked.
This is a product configuration blocker, separate from screen capture. The
project's own approved public-client registration must be configured in the
launcher build (or its supported runtime override), then genuine sign-in and
Play must pass. Do not borrow another launcher's OAuth application ID or claim
that an offline/direct-client test qualifies authentication.
