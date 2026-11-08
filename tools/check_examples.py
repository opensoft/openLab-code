"""Offline draft-contract checks; does not execute commands or import data."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


def load_json(path):
    def reject_constant(value):
        raise ValueError("Non-JSON numeric constant: " + value)
    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("Numeric value exceeds finite float range")
        return parsed
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject_constant, parse_float=finite_float)


def validators(contracts):
    schemas = [load_json(p) for p in Path(contracts).glob("*.schema.json")]
    registry = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in schemas)
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
    return {s["$id"].rsplit("/", 1)[1]: Draft202012Validator(s, registry=registry, format_checker=FormatChecker()) for s in schemas}


def verify_files(root, entries):
    """Verify a static fixture, not a race-safe production transfer."""
    root = Path(root).resolve()
    seen = set()
    for item in entries:
        name = item["path"]
        parts = name.split("/")
        if not name or "\\" in name or ":" in name or any(p in ("", ".", "..") for p in parts) or PurePosixPath(name).is_absolute():
            raise ValueError("Unsafe relative path: " + name)
        if name.casefold() in seen:
            raise ValueError("Duplicate/case-colliding path: " + name)
        seen.add(name.casefold())
        target = root
        for part in parts:
            target = target / part
            if target.is_symlink():
                raise ValueError("Symlink path: " + name)
        if not target.resolve().is_relative_to(root):
            raise ValueError("Path escapes root: " + name)
        data = target.read_bytes()
        if len(data) != item["sizeBytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError("Size/hash mismatch: " + name)


def main():
    code = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contracts", type=Path, default=Path(os.environ.get("CONTRACTS_DIR", code.parent / "spec/contracts/v0.1")))
    args = parser.parse_args()
    checks = validators(args.contracts)
    fixtures = [("zeus/rotate.json", "command-request"), ("zeus/position-slot.json", "command-request"), ("zeus/execution.json", "command-execution"), ("hplcms/import.json", "import-request"), ("hplcms/artifact.json", "artifact")]
    for path, schema in fixtures:
        checks[schema + ".schema.json"].validate(load_json(code / "examples" / path))
    imported = load_json(code / "examples/hplcms/import.json")
    artifact = load_json(code / "examples/hplcms/artifact.json")
    verify_files(code / "examples/hplcms", imported["files"])
    if imported["files"] != artifact["files"]:
        raise ValueError("Artifact does not match import manifest")
    canonical = json.dumps(sorted(imported["files"], key=lambda f: f["path"]), sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != artifact["manifestDigest"]:
        raise ValueError("Artifact manifest digest mismatch")
    print("PASS: 5 fixtures, schemas and synthetic file integrity; no device operations performed")


if __name__ == "__main__":
    main()
