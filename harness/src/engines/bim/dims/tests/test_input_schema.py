"""The input schema of the dimensions engine and the engine's own checks agree."""
import copy
import json
import unittest
from pathlib import Path

import jsonschema

from epc_dims import DimsError, dimensions

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "src" / "epc_dims" / "schema" / "input.schema.json").read_text(encoding="utf-8"))
VALID = {"tol": 1, "gap": 900, "step": 600, "min_wall": 1,
         "walls": [{"id": "S", "a": [0, 0], "b": [8000, 0], "t": 200, "ext_side": "right"}, {"id": "E", "a": [8000, 0], "b": [8000, 5000], "t": 200, "ext_side": "right"}],
         "openings": [{"id": "V1", "wall": "S", "from": 1000, "width": 1500}], "existing": [{"p1": [0, 0], "p2": [1, 0]}]}
BREAKERS = {
    "no_gap": lambda d: d.pop("gap"),
    "no_step": lambda d: d.pop("step"),
    "zero_tol": lambda d: d.update(tol=0),
    "no_walls": lambda d: d.update(walls=[]),
    "wall_without_thickness": lambda d: d["walls"][0].pop("t"),
    "wall_unknown_key": lambda d: d["walls"][0].update(color="red"),
    "bad_ext_side": lambda d: d["walls"][0].update(ext_side="up"),
    "opening_without_width": lambda d: d["openings"][0].pop("width"),
    "opening_negative_from": lambda d: d["openings"][0].update({"from": -1}),
    "existing_without_p2": lambda d: d["existing"][0].pop("p2"),
}


class SchemaAgreesWithTheEngine(unittest.TestCase):
    def test_a_valid_input_passes_both(self):
        jsonschema.validate(VALID, SCHEMA)
        self.assertTrue(dimensions(**VALID)["dims"])

    def test_every_breaker_fails_both(self):
        for name, breaker in BREAKERS.items():
            with self.subTest(case=name):
                data = copy.deepcopy(VALID)
                breaker(data)
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate(data, SCHEMA)
                with self.assertRaises((DimsError, TypeError)):
                    dimensions(**data)


if __name__ == "__main__":
    unittest.main()
