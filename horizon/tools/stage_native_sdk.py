"""Assemble the TerraForged density adapter as a source project for the stock SDK."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

from check_native_sdk import HORIZON_REVISION, ROOT

MIXINS_REVISION = "e59da9094f0c2fdda6c627fe9eff22dec6a906f0"


def stage(output: Path, resources: Path | None = None) -> None:
    root = ROOT / "horizon"
    preset = None
    if resources is not None:
        adapter = root / "native-adapter"
        preset = json.loads(subprocess.check_output([
            "cargo", "run", "--quiet", "--offline", "--locked",
            "--manifest-path", str(adapter / "Cargo.toml"),
            "--target-dir", str(adapter / "target"),
            "--bin", "stock_preset", "--", str(resources),
        ]))
    output.mkdir(parents=True, exist_ok=False)
    source = output / "src"
    shutil.copytree(root / "native-core/src", source, ignore=shutil.ignore_patterns("bin", "data"))
    tables = source / "data"
    tables.mkdir()
    for name in ("biome-types", "noiseutil-sine"):
        table = (root / f"native-core/src/data/{name}.bin").read_bytes()
        rows = (
            "    " + ", ".join(map(str, table[offset:offset + 32])) + ",\n"
            for offset in range(0, len(table), 32)
        )
        (tables / f"{name}.rs").write_text("[\n" + "".join(rows) + "]\n", encoding="utf-8")
    for name in ("biome", "math_table"):
        path = source / f"{name}.rs"
        text = path.read_text(encoding="utf-8")
        text = text.replace('include_bytes!("data/', '&include!("data/').replace('.bin");', '.rs");')
        path.write_text(text, encoding="utf-8")

    for name, target in (
        ("noise_registry", "noise_registry"),
        ("preset", "preset_input"),
        ("preset_editor", "preset_editor"),
    ):
        text = (root / f"native-adapter/src/{name}.rs").read_text(encoding="utf-8")
        text = text.replace("terraforged_native_core::", "crate::").replace("serde_json::", "mod_api::serde_json::")
        (source / f"{target}.rs").write_text(text, encoding="utf-8")

    fixtures = root / "tests/fixtures/kernel-v1"
    for name in ("preset", "noise-registry"):
        json_text = (fixtures / f"{name}.json").read_text(encoding="utf-8")
        (tables / f"{name}.rs").write_text(f'r###"{json_text}"###\n', encoding="utf-8")
    sdk = (root / "native-sdk/src/lib.rs").read_text(encoding="utf-8")
    sdk = sdk.replace("use terraforged_native_adapter::{", "use crate::{").replace(
        "preset::CellPresetInput", "preset_input::CellPresetInput"
    )
    sdk = sdk.replace("use terraforged_native_core::", "use crate::").replace("serde_json::", "mod_api::serde_json::")
    for name in ("preset", "noise-registry"):
        sdk = sdk.replace(f'include_str!("../../tests/fixtures/kernel-v1/{name}.json")', f'include!("data/{name}.rs")')
    (source / "sdk.rs").write_text(sdk, encoding="utf-8")

    lib = source / "lib.rs"
    text = lib.read_text(encoding="utf-8").replace("#![forbid(unsafe_code)]", "#![deny(unsafe_code)]")
    lib.write_text(
        text + "\nmod noise_registry;\nmod preset_input;\npub mod preset_editor;\nmod sdk;\npub use sdk::hooks;\n",
        encoding="utf-8",
    )
    for original, name in ((root / "LICENSE", "LICENSE"), (ROOT / "licenses/ReTerraForged-MIT.txt", "LICENSE-RETERRAFORGED"),
                           (ROOT / "licenses/TerraForged-MIT.txt", "LICENSE-TERRAFORGED")):
        shutil.copyfile(original, output / name)
    (output / "Cargo.toml").write_text("""[package]
name = "mod-terraforged"
version = "0.1.1"
edition = "2024"
publish = false

[dependencies]
horizon-mod-api = { path = ".horizon/sdk/api/crates/horizon-mod-api" }
""", encoding="utf-8")
    (output / "horizon-mod.toml").write_text(f"""id = "terraforged"
name = "TerraForged for Horizon"
version = "0.1.1-sdk.dev1"
description = "TerraForged terrain for the native Horizon SDK."
authors = ["TerraForged Revival contributors"]
api = "0.2"
side = "both"
capabilities = ["registries"]

[native]
game = "26.3"
horizon = "{HORIZON_REVISION}"
mixins = "{MIXINS_REVISION}"
""", encoding="utf-8")
    if preset is not None:
        files = {
            "data/terraforged/worldgen/world_preset/default.json": preset,
            "data/minecraft/tags/worldgen/world_preset/normal.json": {
                "values": ["terraforged:default"],
            },
        }
        for relative, data in files.items():
            path = output / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        shutil.copytree(root / "native-content/assets", output / "assets")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resources", type=Path, help="Prepared Horizon 26.3 resources, to include the default preset")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Choose a fresh output directory")
    stage(output, args.resources.resolve() if args.resources is not None else None)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
