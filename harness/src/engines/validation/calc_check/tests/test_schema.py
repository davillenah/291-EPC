"""The small draft-07 validator: each keyword it supports, with one bad value each."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from epc_calc_check.schema import validate  # noqa: E402


class SchemaTests(unittest.TestCase):
    def test_type_and_enum(self):
        self.assertEqual(validate("a", {"type": "string", "enum": ["a", "b"]}), [])
        self.assertTrue(validate(1, {"type": "string"}))
        self.assertTrue(validate(True, {"type": "integer"}))
        self.assertTrue(validate("c", {"enum": ["a"]}))
        self.assertEqual(validate(None, {"type": ["object", "null"]}), [])

    def test_strings(self):
        self.assertTrue(validate("", {"minLength": 1}))
        self.assertTrue(validate("ab", {"pattern": "^[0-9]+$"}))
        self.assertEqual(validate("12", {"pattern": "^[0-9]+$"}), [])

    def test_objects(self):
        schema = {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}, "additionalProperties": False}
        self.assertEqual(validate({"a": 1}, schema), [])
        self.assertTrue(validate({}, schema))
        self.assertTrue(validate({"a": 1, "b": 2}, schema))
        self.assertTrue(validate({"a": "x"}, schema))
        self.assertTrue(validate({"a": 1, "b": "x"}, {"properties": {"a": {}}, "additionalProperties": {"type": "integer"}}))

    def test_arrays(self):
        schema = {"type": "array", "minItems": 1, "items": {"type": "number"}}
        self.assertEqual(validate([1, 2.5], schema), [])
        self.assertTrue(validate([], schema))
        self.assertTrue(validate([1, "x"], schema))

    def test_if_then_else(self):
        schema = {"if": {"properties": {"k": {"enum": ["x"]}}, "required": ["k"]}, "then": {"required": ["y"]}, "else": {"required": ["z"]}}
        self.assertTrue(validate({"k": "x"}, schema))
        self.assertEqual(validate({"k": "x", "y": 1}, schema), [])
        self.assertTrue(validate({"k": "w"}, schema))
        self.assertEqual(validate({"k": "w", "z": 1}, schema), [])
        self.assertEqual(validate({}, {"if": {"required": ["k"]}, "then": {"required": ["y"]}}), [])

    def test_unknown_things_are_ignored(self):
        self.assertEqual(validate(1, {"$comment": "x", "type": "weird"}), [])
        self.assertEqual(validate(1, "not a schema"), [])


if __name__ == "__main__":
    unittest.main()
