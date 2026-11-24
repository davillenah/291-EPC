"""The input schema of the select engine and the engine's own checks agree."""
import copy
import json
import unittest
from pathlib import Path

import jsonschema

from epc_select import SelectError, select

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "src" / "epc_select" / "schema" / "input.schema.json").read_text(encoding="utf-8"))
GOOD = {"records": [{"a": 1}, {"a": 2}], "conditions": [{"field": "a", "op": "gt", "value": 1}], "match": "all", "max_results": 10}
BREAKERS = {
    "no_records": lambda d: d.pop("records"),
    "no_conditions": lambda d: d.pop("conditions"),
    "no_match": lambda d: d.pop("match"),
    "no_limit": lambda d: d.pop("max_results"),
    "bad_match": lambda d: d.update(match="some"),
    "zero_limit": lambda d: d.update(max_results=0),
    "unknown_op": lambda d: d["conditions"][0].update(op="like"),
    "no_field": lambda d: d["conditions"][0].pop("field"),
    "records_not_objects": lambda d: d.update(records=[1]),
    "unknown_key": lambda d: d.update(extra=1),
}
# the schema cannot say that an operator needs a value, so these are the engine's own check
ENGINE_ONLY = {"missing_value": lambda d: d["conditions"][0].pop("value")}


class SchemaAgreesWithTheEngine(unittest.TestCase):
    def test_valid_input_passes_both(self):
        jsonschema.validate(GOOD, SCHEMA)
        self.assertEqual(select(**GOOD)["count"], 1)

    def test_every_breaker_fails_the_schema_and_the_engine(self):
        for name, breaker in BREAKERS.items():
            with self.subTest(case=name):
                data = copy.deepcopy(GOOD)
                breaker(data)
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate(data, SCHEMA)
                with self.assertRaises((SelectError, TypeError)):
                    select(**data)

    def test_the_engine_refuses_what_the_schema_cannot_say(self):
        data = copy.deepcopy(GOOD)
        ENGINE_ONLY["missing_value"](data)
        jsonschema.validate(data, SCHEMA)
        with self.assertRaises(SelectError):
            select(**data)


if __name__ == "__main__":
    unittest.main()
