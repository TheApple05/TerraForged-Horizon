# TerraForged 0.1.0 for Horizon: Windows candidate

**Qualification is in progress. This is not a published stable release.**
The version number freezes the proposed package identity; it does not certify it.

The intended scope is Windows x64, Vulkan, Minecraft 26.3, singleplayer and the
bundled `terraforged:default` overworld preset. This independent, unofficial
native Rust port is separate from the Java 26.2 Fabric/NeoForge version.

## Candidate downloads

- `terraforged-horizon-26.3-0.1.0.hmod`: whole native source/content package.
- `terraforged-horizon-launcher-windows-x64-0.1.0.zip`: compatible fork launcher,
  start wrapper and license notices.
- `terraforged-horizon-0.1.0-source.zip`: matching native-project source.
- `SHA256SUMS`: SHA-256 hashes of those files.

No Minecraft assets, compiled game client, worlds, accounts or QA mods belong in
these downloads. The final public bytes and their installed native build still
need qualification. See [the current gates](stable-release-readiness.md).

## Installation procedure being qualified

Use your own Minecraft Java ownership and a Prism installation containing
Minecraft 26.3. Extract the launcher ZIP into a new folder and open Command
Prompt there. Use the included wrapper for these commands and for opening the
window; it disables upstream self-update for this fork process.

1. Refresh your Minecraft account in Prism, then import its current session:

   ```bat
   Start-TerraForged-Horizon.cmd account import-prism "%APPDATA%\PrismLauncher\accounts.json"
   ```

   Use the actual accounts-file path if Prism is portable or installed elsewhere.
   Import checks Minecraft ownership and the matching profile. The fork has no
   approved Microsoft application ID, so its own `account sign-in` flow is not
   available. It does not borrow Prism's OAuth ID or Microsoft refresh token.

2. Install the prepared base version and extract resources from your installation:

   ```bat
   Start-TerraForged-Horizon.cmd install v0.2.97
   Start-TerraForged-Horizon.cmd prepare --version v0.2.97 --minecraft "%APPDATA%\PrismLauncher"
   ```

   Preparation may fetch Mojang's matching metadata and server jar. Keep the
   resulting private game resources on your machine.

3. Create a separate instance and find its game folder:

   ```bat
   Start-TerraForged-Horizon.cmd instance create TerraForged
   Start-TerraForged-Horizon.cmd instance list
   ```

4. Place the **whole HMOD** in that instance's `horizon-native-mods` folder,
   creating the folder if needed. Do not extract or rename the archive. The
   GitHub native-mod installer currently selects `.hnmod` downloads, so use
   this manual placement for the combined `.hmod`.

   In the same instance's `horizon-mods.txt`, add this line, keeping any existing
   settings for other mods:

   ```text
   mod.terraforged_native:true
   ```

   Manually copied native archives start off. The CLI `mods enable` command only
   handles browser-installed entries; manual installation needs this explicit
   opt-in before `native-build`.

5. Compile and select the instance:

   ```bat
   Start-TerraForged-Horizon.cmd native-build --instance TerraForged --version v0.2.97 --profile performance --trust-native-code
   Start-TerraForged-Horizon.cmd instance select TerraForged
   ```

   Native mods execute with your computer's permissions. Use the trust flag only
   for source you trust. The launcher provisions its own pinned compiler; a cold
   native build can take much longer than an incremental rebuild.

6. Open `Start-TerraForged-Horizon.cmd`, choose Play, and select the TerraForged
   world type when creating a world. Keep a backup before opening an existing
   preview world. Upgrade support is pending the copied-world acceptance test.

When the imported Minecraft session expires, refresh it in Prism and repeat the
import command. Horizon cannot renew that session through Prism's Microsoft
registration.

## Scope and remaining acceptance

The candidate retains the dev7 distance-12 terrain cache and adds the tested
bit-identical smoothing optimization and nonfinite terrace guard. Retained
tile payload is 75 MiB per sampler; other memory use is additional.

Three source-built seeds, six clean exits, stored native biome comparisons,
death/respawn state checks and copied metadata recovery pass. Those observations
do not qualify a different final installed artifact. Sustained exploration,
preview upgrade/interrupted-session checks and exact installed Play are pending.

Other operating systems, dedicated servers/multiplayer, arbitrary modpacks,
Java's preset editor/custom settings, and complete historical Java feature or
scenery parity are outside the intended first stable scope. Vanilla, Nether and
End retain the pinned engine's behavior. This mod does not certify the whole
Horizon client or every upstream Minecraft feature.

Native source pins: Horizon `f43eebfc04b73f0c2bbf5048f7a3ab36c240f21d`,
horizon-mixins `e8cd0aa38cffef49cb2e088ef716baa107148c02`. The compatible
launcher source is [fork commit 62e533e](https://github.com/TheApple05/horizon/commit/62e533e009eb2fa58cbe10948f2e453fa00b94f2).
