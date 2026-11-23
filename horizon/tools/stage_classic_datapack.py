"""Generate classic biome resources for integration with Horizon's native SDK."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PureWindowsPath
import re
import subprocess
import tempfile

from check_native_sdk import ROOT
from classic_resource_tags import resolve_tags


def read_bundle(path: Path) -> dict[str, str]:
    limit = 16 << 20
    with path.open("rb") as resource:
        data = resource.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"{path} exceeds 16 MiB")
    return json.loads(data)


def derive(resources: Path) -> dict:
    worldgen = resources / "worldgen"
    bundles = {
        name: read_bundle(worldgen / f"{name}.json")
        for name in ("biomes", "features", "placed_features")
    }
    biome_tags = read_bundle(worldgen / "biome_tags.json")
    feature_tags = {}
    for filename in ("placed_feature_tags.json", "feature_tags.json"):
        path = worldgen / filename
        if path.is_file():
            feature_tags = read_bundle(path)
            break
    bundles["biome_tags"], _ = resolve_tags(biome_tags, bundles["biomes"])
    bundles["feature_tags"], _ = resolve_tags(feature_tags, bundles["placed_features"])

    adapter = ROOT / "horizon/native-adapter"
    with tempfile.TemporaryDirectory() as temp:
        inputs = Path(temp) / "bundles.json"
        inputs.write_text(json.dumps(bundles), encoding="utf-8")
        return json.loads(subprocess.check_output([
            "cargo", "run", "--quiet", "--offline", "--locked",
            "--manifest-path", str(adapter / "Cargo.toml"),
            "--target-dir", str(adapter / "target"),
            "--bin", "classic_biome_data_probe", "--", str(inputs),
        ]))


def resource_path(kind: str, identifier: str) -> Path:
    namespace, _, path = identifier.partition(":")
    allowed = {"minecraft", "reterraforged"} if kind == "tags/worldgen/biome" else {"reterraforged"}
    if namespace not in allowed or not all(
        re.fullmatch(r"[a-z0-9_.-]{1,250}", part)
        and not part.endswith(".")
        and not PureWindowsPath(part).is_reserved()
        for part in path.split("/")
    ):
        raise ValueError(f"Invalid classic resource ID {identifier!r}")
    return Path("data", namespace, kind, f"{path}.json")


def stage(resources: Path, output: Path) -> None:
    data = derive(resources)
    resources_by_path = {
        resource_path(kind, identifier): json.loads(text)
        for key, kind in (
            ("biomes", "worldgen/biome"),
            ("placed_features", "worldgen/placed_feature"),
            ("configured_features", "worldgen/feature"),
        )
        for identifier, text in data[key].items()
    }
    for identifier, values in data["biome_tags"].items():
        path = resource_path("tags/worldgen/biome", identifier)
        resources_by_path[path] = {"replace": False, "values": values}
    resources_by_path[Path("required-native-features.json")] = data["required_custom_algorithms"]

    output.mkdir(parents=True, exist_ok=False)
    for relative, value in resources_by_path.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Choose a fresh output directory")
    stage(args.resources.resolve(), output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
