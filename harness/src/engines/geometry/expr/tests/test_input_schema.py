"""The input schema of the expression engine and the engine's own checks agree."""
import copy
import json
import unittest
from pathlib import Path

import jsonschema

from epc_expr import ExprError, evaluate

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "src" / "epc_expr" / "schema" / "input.schema.json").read_text(encoding="utf-8"))
VALID = {"expression": "w*h/2", "variables": {"w": 4, "h": 3}}
BREAKERS = {
    "no_expression": lambda d: d.pop("expression"),
    "empty_expression": lambda d: d.update(expression="   "),
    "number_expression": lambda d: d.update(expression=5),
    "too_long": lambda d: d.update(expression="1+" * 600),
    "bad_variable_name": lambda d: d.update(variables={"1x": 1}),
    "text_variable_value": lambda d: d.update(variables={"w": "4"}),
    "unknown_key": lambda d: d.update(units="mm"),
}


class SchemaAgreesWithTheEngine(unittest.TestCase):
    def test_a_valid_input_passes_both(self):
        jsonschema.validate(VALID, SCHEMA)
        self.assertEqual(evaluate(**VALID), 6.0)

    def test_every_breaker_fails_both(self):
        for name, breaker in BREAKERS.items():
            with self.subTest(case=name):
                data = copy.deepcopy(VALID)
                breaker(data)
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate(data, SCHEMA)
                with self.assertRaises((ExprError, TypeError)):
                    evaluate(**data)


if __name__ == "__main__":
    unittest.main()
