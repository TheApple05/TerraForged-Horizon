# Marsh material sampler

`MarshSampler` reproduces the source swamp feature's fixed Simplex/White-warp
material graph and clay/gravel/dirt selection. The source compares a float noise
value with double literals: the exact float representation of 0.6 is greater
than double 0.6. The native selector preserves that promotion, including NaNs,
infinities, signed zero and adjacent float threshold values.

Two actual Minecraft 26.2 / Fabric 0.20.1 server processes captured 122,832
observations from the exact qualified dev.23 production JAR. They agree byte for
byte; relevant loaded class origins and artifact hashes are recorded in the
frozen metadata. Material noise and the private getMaterial method are invoked
from the packaged feature. Injected-value threshold expressions follow its Java
source; this is not an execution of the whole feature loop.

[Native debug and release](../validation/horizon-native-marsh-material-sampler-v2.json)
match all 81,934 material/noise/threshold observations. The remaining 40,898
observations cover Minecraft's fixed biome-information noise and its sign, and
are explicitly outside the native-core comparison. The separate host verifier
checks those rows using the engine's double-valued primitive.

Frozen verification is standalone and requires no Java checkout or game files.
Capturing a new reference requires the explicit `TERRAFORGED_JAVA_ROOT`, existing
production JAR/classpath and a copied local server installation. The producer
uses a separate QA companion, invokes no installer, and downloads no game files.
Captured paths and hashes from before the repository split remain historical
evidence and are not rewritten.

This qualifies numerical material selection. Exact chunk-heightmap access,
fluid checks, biome eligibility, writes, natural placement, scenery and native
performance/modpack compatibility remain integration work.
