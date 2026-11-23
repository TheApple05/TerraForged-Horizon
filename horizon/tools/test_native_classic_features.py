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

import verify_classic_features


class NativeClassicFeatureTargetTest(unittest.TestCase):
    def test_build_and_probe_use_the_stage_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage = root / "build/qa/horizon/example"
            workspace = stage / "staged"
            (workspace / "crates/horizon-world/src/bin").mkdir(parents=True)
            manifest = workspace / "Cargo.toml"
            manifest.write_text(
                '[package]\nname = "horizon-world"\nversion = "0.1.0"\nedition = "2021"\n'
                '[[bin]]\nname = "terraforged_classic_features"\n'
                'path = "crates/horizon-world/src/bin/terraforged_classic_features.rs"\n',
                encoding="utf-8",
            )
            subprocess.run(
                ["cargo", "+stable", "generate-lockfile", "--offline", "--manifest-path", str(manifest)],
                check=True,
            )
            (stage / "stage-result.json").write_text(
                '{"horizonRevision":"test","inputFiles":{}}', encoding="utf-8"
            )
            source = root / "horizon/tests/rust/classic_feature_runtime_probe.rs"
            source.parent.mkdir(parents=True)
            source.write_text(
                'fn main() { println!(r#"{{"status":"passed-real-native-geology-placement"}}"#); }\n',
                encoding="utf-8",
            )
            for name in ("host-density-v1/inputs.json", "classic-runtime-v1/targets.json"):
                fixture = root / "horizon/tests/fixtures" / name
                fixture.parent.mkdir(parents=True)
                fixture.write_text("{}", encoding="utf-8")
            resources = root / "resources"
            resources.mkdir()
            (resources / "facts.json").write_text("{}", encoding="utf-8")
            report = root / "result.json"
            other_target = root / "configured-target"
            args = [
                "verify_classic_features", "--workspace", str(workspace),
                "--resources", str(resources), "--report", str(report),
            ]
            with (patch.object(verify_classic_features, "ROOT", root),
                  patch.object(sys, "argv", args),
                  patch.dict(os.environ, {"CARGO_BUILD_TARGET_DIR": str(other_target)}),
                  contextlib.redirect_stdout(io.StringIO())):
                os.environ.pop("CARGO_TARGET_DIR", None)
                self.assertEqual(verify_classic_features.main(), 0)
            receipt = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "passed-real-native-geology-placement")
            self.assertTrue(receipt["freshProcessesAgree"])
            self.assertFalse(other_target.exists())


if __name__ == "__main__":
    unittest.main()
