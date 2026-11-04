"""Locate the separate Java port used to capture or check Java references.

Frozen native verifiers do not need this checkout. Source and capture tools
require an explicit path so an unrelated sibling checkout is never selected.
"""
from __future__ import annotations

import os
from pathlib import Path


def java_reference_root() -> Path:
    value = os.environ.get("TERRAFORGED_JAVA_ROOT")
    if not value:
        raise SystemExit(
            "Set TERRAFORGED_JAVA_ROOT to the separate TerraForged-26.2 Java "
            "checkout for this Java-reference operation. Frozen native "
            "verification does not require a Java checkout."
        )
    root = Path(value).expanduser().resolve()
    if not (root / "common/src/main/java/raccoonman/reterraforged").is_dir():
        raise SystemExit(
            "TERRAFORGED_JAVA_ROOT does not contain the TerraForged Java source: "
            + str(root)
        )
    return root


def source_reference_key(path: Path, native_root: Path) -> str:
    """Keep repository-relative provenance keys for native and Java sources."""
    path = path.resolve()
    java_root = java_reference_root()
    try:
        return path.relative_to(java_root).as_posix()
    except ValueError:
        return path.relative_to(native_root.resolve()).as_posix()
