"""Save-probe setup works on fresh stages and rejects conflicting QA inputs."""
import tempfile,tomllib,unittest
from pathlib import Path
from verify_native_ui import prepare_save_fixture

class SaveFixtureTests(unittest.TestCase):
    def test_fresh_stage_and_repeat_preserve_exact_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'probe.rs';source.write_text('fn main() {}\n',encoding='utf-8')
            manifest=root/'crates/horizon-client-lib/Cargo.toml';manifest.parent.mkdir(parents=True);manifest.write_text('[package]\nname = "fixture"\n',encoding='utf-8')
            prepare_save_fixture(root,source)
            dest=manifest.parent/'qa/terraforged_save_fixture.rs'
            self.assertEqual(dest.read_bytes(),source.read_bytes())
            self.assertEqual(tomllib.loads(manifest.read_text())['bin'],[{'name':'terraforged_save_fixture','path':'qa/terraforged_save_fixture.rs'}])
            before=manifest.read_bytes();prepare_save_fixture(root,source);self.assertEqual(manifest.read_bytes(),before)
            dest.write_text('conflict',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'probe differs'):prepare_save_fixture(root,source)
            self.assertEqual(dest.read_text(),'conflict')
            dest.write_bytes(source.read_bytes());manifest.write_text('[[bin]]\nname = "terraforged_save_fixture"\npath = "other.rs"\n',encoding='utf-8');before=manifest.read_bytes()
            with self.assertRaisesRegex(ValueError,'Conflicting fixture target'):prepare_save_fixture(root,source)
            self.assertEqual(manifest.read_bytes(),before)

if __name__=='__main__':unittest.main()
