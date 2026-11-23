"""GEN-09: the contract tables come from the schema (fields, required, limits, list items)."""
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("engine_contracts", Path(__file__).resolve().parents[2] / "tools" / "build" / "engine_contracts.py")
EC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EC)

SCHEMA = {"type": "object", "required": ["spaces"], "properties": {
    "spaces": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["id"], "properties": {
        "id": {"type": "string"}, "kind": {"enum": ["wall", "roof"]}, "code": {"type": "string", "pattern": "a|b"}}}}}}


class Contracts(unittest.TestCase):
    def test_fields_required_and_limits(self):
        got = {r[0]: r for r in EC.rows(SCHEMA)}
        self.assertEqual(got["spaces"][1:4], ("array", "yes", "minItems 1"))
        self.assertEqual(got["spaces[].id"][2], "yes")
        self.assertEqual(got["spaces[].kind"][1], "one of `wall`, `roof`")

    def test_a_pipe_does_not_split_the_cell(self):
        line = next(l for l in EC.table(SCHEMA) if "spaces[].code" in l)
        self.assertIn("a\\|b", line)

    def test_the_file_is_fresh(self):
        self.assertEqual(EC.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
