# Official Nightly compatibility work

The Customize preview is **not yet qualified for the stock official Nightly**.
The mod-page submission stays [draft](https://github.com/horizon-rust/horizon-mods/pull/471)
until that qualification passes. Published stable 0.1.0 and Customize dev1 assets
are unchanged.

The latest published game Nightly checked on November 8, 2026 (Pacific) is
[`fdc87aec`](https://github.com/horizon-rust/horizon/releases/tag/nightly).
The local development candidate builds from that source plus explicit engine
patches at `TheApple05/horizon@c01c08b7b80f21e76915cfdbf70b85a05b273ad7`.
That patched build is supporting integration evidence, not a substitute for
testing the actual published Nightly.

## Changes submitted for upstream review

The linked [API specification (#13637)](https://github.com/horizon-rust/horizon/issues/13637)
is claimed for this work and awaits maintainer approval under upstream's
[large-PR process](https://github.com/horizon-rust/horizon/blob/4bff97d0084752794bcbc304f5219a6283d2f36d/CONTRIBUTING.md#large-pull-requests).
The implementation drafts were written before spec approval and may need to
change or wait. No approval or merge is implied by their passing checks.

- [#13581: bounded native preset catalog and saved settings](https://github.com/horizon-rust/horizon/pull/13581).
  Static metadata and function pointers; editor choices and saved stems remain
  local to a world. Invalid settings must not overwrite an existing save.
- [#13587: world-owned biome mapping and lazy feature decoding](https://github.com/horizon-rust/horizon/pull/13587).
  Declare possible biome results before catalogs are built, retain decoder
  owners through lazy reads, and preserve ordinary generation paths.
- [#13589: creation-menu editor](https://github.com/horizon-rust/horizon/pull/13589),
  stacked on #13581. Reuse registering widgets, translations and keyboard
  navigation; preserve Done, Cancel, Reset and Re-Create.

Combined native content also depends on the installation/loading path covered
by the existing [#11083](https://github.com/horizon-rust/horizon/pull/11083).
The first real-menu check on the Nightly-based API candidate found untranslated
Customize labels because its combined native content was not discovered.
The local candidate includes the earlier bounded content-discovery fix and
passes the translated native-menu checks. That proves this candidate's path;
it does not qualify the different implementation in #11083.
No duplicate upstream content-loader PR was opened.

The engine API port retains current upstream generation optimizations and
new-world data-pack defaults. The catalog, pipeline construction and title
state definitions move to small child modules where required by upstream's
large-file growth check. Public paths remain available through re-exports.
The Nightly-based runtime candidate additionally retains a Windows GNU
system-allocator selection and a platform-specific TCP keepalive lint fix.
Current upstream already contains the latter. Its allocator behavior still
needs separate runtime qualification; the API reviews do not change that policy.

## Qualification gates

The initial frozen Nightly-based API branch passed public-tree checks,
formatting, Clippy, 720 Python tests, 6,024 game tests and 752 launcher tests.
Those results apply to engine `592c3fed`, before the content-discovery correction.
Current-main PR checks and the corrected candidate are tracked separately;
their pending runs are not counted as passes.
Local review worktrees now use distinct build directories after a shared
directory reused a stale dependency from another tree. Those affected local
Rust results are excluded from qualification and are being repeated.

The corrected `c01c08b7` candidate has passed native-menu creation of three
worlds in one process (edited settings, classic variants off, and defaults),
Done/Cancel/Reset, Re-Create and clean reopen. An independently built MSVC
reader compared 15,360 stored quart biomes against the selected settings;
the game was built with GNU performance. Both client exits were clean.
The combined `.hnmod` alias loads correctly, and changing GUI scale preserves
the editor draft. Original screenshots were inspected at automatic scale
and scale 2. These are Windows x64 Vulkan single-player checks.

The current-main API integration at `ddf761d0` and its native adapter at
`d5110a77` pass all five Linux native integration modes and the noise
foundation workflow. That includes the latest pipeline's saved-structure
callback. It is source/injection qualification, not a current-main runtime
qualification. The candidate above remains separately pinned.

The current registry checker accepts both archive files, the submission
metadata and its downloaded-file digest. That checks package structure and
listing consistency; it does not establish official Nightly compatibility.

Required remaining evidence includes:

- Green source checks for the exact upstream review heads and the complete
  injected native bundle, including the smaller developer staging modes.
- A disposable dev1 QA-world upgrade with committed block/inventory fixtures,
  saved Customize settings and new distant generation; controlled malformed
  settings and old-client refusal without changing protected saved files.
- Visual inspection and a bounded runtime soak of the corrected candidate.
- Re-pin and rebuild against an actual published official Nightly containing
  the necessary APIs and content path. Run its required native compatibility
  and combination checks, plus the current registry file/metadata checks.
- Publish a new immutable version and update the registry entry to that exact
  download and digest before requesting mod-page review.

Testing uses fresh private homes and disposable QA saves. It does not modify
player worlds, import account data, or use desktop automation. A native source
build, a successful package check, and a working patched engine each prove
different things; none alone establishes stock Nightly compatibility.
