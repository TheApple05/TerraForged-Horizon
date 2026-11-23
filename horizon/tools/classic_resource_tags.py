"""Resolve references in the prepared biome and placed-feature tag bundles."""

from __future__ import annotations

import json


def resolve_tags(raw, known):
    # Invalid tags remain absent, so features referring to them fail derivation.
    definitions = {name: json.loads(value) for name, value in raw.items()}
    memo = {}
    active = set()
    invalid = {}

    def visit(name, depth=0):
        if depth > 128:
            raise ValueError("Tag depth exceeded")
        if name in active:
            raise ValueError("Cyclic tag " + name)
        if name in memo:
            return memo[name]
        if name not in definitions:
            raise ValueError("Missing tag " + name)
        active.add(name)
        try:
            values = set()
            for entry in definitions[name]["values"]:
                if isinstance(entry, str):
                    identifier, required = entry, True
                else:
                    identifier, required = entry["id"], entry.get("required", True)
                tag = identifier.startswith("#")
                identifier = identifier.removeprefix("#")
                if ":" not in identifier:
                    identifier = "minecraft:" + identifier
                if identifier not in (definitions if tag else known):
                    if required:
                        raise ValueError("Required tag member absent: " + identifier)
                    continue
                try:
                    values.update(visit(identifier, depth + 1) if tag else [identifier])
                except ValueError:
                    if required:
                        raise
            memo[name] = sorted(values)
            return memo[name]
        finally:
            active.remove(name)

    for name in definitions:
        try:
            visit(name)
        except ValueError as error:
            invalid[name] = str(error)
    return memo, invalid
