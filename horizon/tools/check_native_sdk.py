"""Compile and exercise TerraForged density nodes against the pinned public Horizon SDK."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HORIZON_REVISION = "09d03862ee21197a45eaab65e23032fcc3570e77"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--horizon", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    horizon = args.horizon.resolve()
    output = args.output.resolve()
    if output.exists():
        parser.error("Choose a fresh output directory")
    head = subprocess.check_output(["git", "-C", str(horizon), "rev-parse", "HEAD"], text=True).strip()
    if head != HORIZON_REVISION:
        parser.error(f"Check out Horizon {HORIZON_REVISION} first")
    if subprocess.check_output(["git", "-C", str(horizon), "status", "--porcelain", "--untracked-files=no"], text=True):
        parser.error("Use a Horizon checkout with clean tracked files")

    def toml_path(path: Path) -> str:
        return json.dumps(path.as_posix(), ensure_ascii=False)

    output.mkdir(parents=True)
    shutil.copyfile(horizon / "Cargo.lock", output / "Cargo.lock")
    (output / "Cargo.toml").write_text(f"""[package]
name = "terraforged-native-sdk-check"
version = "0.1.0"
edition = "2024"
publish = false

[lib]
path = {toml_path(ROOT / 'horizon/native-sdk/src/lib.rs')}

[dependencies]
horizon-mod-api = {{ path = {toml_path(horizon / 'crates/horizon-mod-api')} }}
terraforged-native-core = {{ path = {toml_path(ROOT / 'horizon/native-core')} }}
terraforged-native-adapter = {{ path = {toml_path(ROOT / 'horizon/native-adapter')} }}
serde_json = "=1.0.151"
""", encoding="utf-8")
    return subprocess.call(["cargo", "test", "--offline", "--target-dir", str(output / "target")], cwd=output)


if __name__ == "__main__":
    raise SystemExit(main())
