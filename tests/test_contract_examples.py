import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest

from jsonschema import ValidationError

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE / "tools"))
from check_examples import load_json, validators, verify_files


class ContractExamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        contracts = Path(os.environ.get("CONTRACTS_DIR", CODE.parent / "spec/contracts/v0.1"))
        cls.schemas = validators(contracts)

    def test_invalid_commands(self):
        original = load_json(CODE / "examples/zeus/rotate.json")
        for params in [{"mode": "absolute-degrees", "degrees": 360}, {"mode": "relative-degrees", "degrees": 5, "slotNumber": 2}, {"mode": "unknown", "degrees": 5}]:
            with self.subTest(params=params):
                value = copy.deepcopy(original)
                value["parameters"] = params
                with self.assertRaises(ValidationError):
                    self.schemas["command-request.schema.json"].validate(value)

    def test_zero_slot_rejected(self):
        value = load_json(CODE / "examples/zeus/position-slot.json")
        value["parameters"]["slotNumber"] = 0
        with self.assertRaises(ValidationError):
            self.schemas["command-request.schema.json"].validate(value)

    def test_corrupt_bytes_rejected(self):
        item = load_json(CODE / "examples/hplcms/import.json")["files"][0]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / item["path"]
            target.parent.mkdir()
            target.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                verify_files(directory, [item])

    def test_unsafe_paths_rejected(self):
        item = load_json(CODE / "examples/hplcms/import.json")["files"][0]
        for name in ["../outside", "/absolute", "C:relative", "raw/../signal.txt", "raw\\signal.txt", "raw//signal.txt"]:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Unsafe"):
                verify_files(CODE / "examples/hplcms", [{**item, "path": name}])

    def test_duplicate_paths_rejected(self):
        item = load_json(CODE / "examples/hplcms/import.json")["files"][0]
        with self.assertRaisesRegex(ValueError, "colliding"):
            verify_files(CODE / "examples/hplcms", [item, {**item, "path": item["path"].upper()}])

    def test_nonfinite_json_rejected(self):
        for token in ["NaN", "Infinity", "1e400"]:
            with self.subTest(token=token), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "invalid.json"
                path.write_text(token, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_json(path)

    def test_invalid_timestamps_rejected(self):
        request = load_json(CODE / "examples/zeus/rotate.json")
        request["expiresAt"] = "not-a-timestamp"
        with self.assertRaises(ValidationError):
            self.schemas["command-request.schema.json"].validate(request)
        execution = load_json(CODE / "examples/zeus/execution.json")
        execution["evidence"][0]["observedAt"] = "2026-99-99T00:00:00Z"
        with self.assertRaises(ValidationError):
            self.schemas["command-execution.schema.json"].validate(execution)
