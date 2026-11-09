import tomllib
import unittest

from stage_native_host import pruned_workspace


class NativeHostWorkspaceTest(unittest.TestCase):
    def test_pruned_stages_keep_the_pinned_compiler_requirement(self):
        for version in ("1.94", "1.99"):
            package = {"edition": "2024", "license": "MIT", "rust-version": version}
            manifest = tomllib.loads(pruned_workspace(package))
            self.assertEqual(manifest["workspace"]["package"], package)
            self.assertEqual(manifest["workspace"]["members"], ["crates/horizon-core", "crates/horizon-world"])
            self.assertEqual(manifest["workspace"]["lints"]["clippy"]["too_many_arguments"], "allow")
