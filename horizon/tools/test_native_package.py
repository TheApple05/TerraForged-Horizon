import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import verify_native_package


class NativePackageTargetTest(unittest.TestCase):
    def test_build_and_probe_use_the_stage_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage = root / "build/qa/horizon/example"
            workspace = stage / "staged"
            package_dir = workspace / "crates/horizon-mods"
            (package_dir / "src/bin").mkdir(parents=True)
            (workspace / "Cargo.toml").write_text(
                '[workspace]\nresolver = "2"\nmembers = ["crates/horizon-mods"]\n', encoding="utf-8"
            )
            (package_dir / "Cargo.toml").write_text(
                '[package]\nname = "horizon-mods"\nversion = "0.1.0"\nedition = "2021"\n'
                '[features]\nindex = []\n', encoding="utf-8"
            )
            (package_dir / "src/lib.rs").touch()
            subprocess.run(
                ["cargo", "+stable", "generate-lockfile", "--offline", "--manifest-path", str(workspace / "Cargo.toml")],
                check=True,
            )
            (stage / "stage-result.json").write_text(json.dumps({
                "fullEngineSourceIncluded": True,
                "automaticWorldSelectionIncluded": True,
                "inputFiles": {},
                "horizonRevision": "test",
            }), encoding="utf-8")
            bundle = stage / "mods/terraforged_native"
            bundle.mkdir(parents=True)
            driver = root / "horizon/tests/rust/native_package_probe.rs"
            driver.parent.mkdir(parents=True)
            driver.write_text(
                'fn main() { println!("{{}}"); eprintln!("NATIVE_PACKAGE_READERS_OK"); }\n', encoding="utf-8"
            )
            archive = root / "temp.hmod"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("horizon-native.json", '{"version":"0.1.0"}')
            report = root / "result.json"
            other_target = root / "inherited-target"
            args = ["verify_native_package", "--workspace", str(workspace), "--report", str(report),
                    "--original", str(archive), "--package", str(archive)]
            with (patch.object(verify_native_package, "ROOT", root),
                  patch.object(sys, "argv", args),
                  patch.dict(os.environ, {"CARGO_TARGET_DIR": str(other_target)}),
                  contextlib.redirect_stdout(io.StringIO())):
                self.assertEqual(verify_native_package.main(), 0)
            receipt = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "passed-native-package-readers")
            self.assertFalse(other_target.exists())


if __name__ == "__main__":
    unittest.main()
