"""The input schema of the walls engine and the engine's own checks agree (a valid input passes both; each broken one fails the schema and raises `WallsError`)."""
import copy
import json
import unittest
from pathlib import Path

import jsonschema

from epc_walls import WallsError, outlines

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "src" / "epc_walls" / "schema" / "input.schema.json").read_text(encoding="utf-8"))
LAYERS = [{"mat": "finish", "t": 15, "function": "finish"}, {"mat": "block", "t": 185, "function": "structure", "priority": 850}]
VALID = {"tol": 1, "walls": [{"id": "A", "a": [0, 0], "b": [4000, 0], "t": 200}, {"id": "B", "a": [4000, 0], "b": [4000, 3000], "layers": LAYERS, "ext_side": "right"}],
         "styles": {"A:end|B:start": {"style": "butt", "through": "A"}}}
BREAKERS = {
    "no_tol": lambda d: d.pop("tol"),
    "zero_tol": lambda d: d.update(tol=0),
    "no_walls": lambda d: d.update(walls=[]),
    "wall_unknown_key": lambda d: d["walls"][0].update(color="red"),
    "wall_without_id": lambda d: d["walls"][0].pop("id"),
    "point_of_three": lambda d: d["walls"][0].update(a=[0, 0, 0]),
    "negative_thickness": lambda d: d["walls"][0].update(t=-1),
    "bad_ext_side": lambda d: d["walls"][0].update(ext_side="up"),
    "layer_bad_function": lambda d: d["walls"][1]["layers"][0].update(function="paint"),
    "layer_priority_out_of_range": lambda d: d["walls"][1]["layers"][0].update(priority=5000),
    "bad_style": lambda d: d["styles"].update({"A:end|B:start": "round"}),
}


class SchemaAgreesWithTheEngine(unittest.TestCase):
    def test_a_valid_input_passes_both(self):
        jsonschema.validate(VALID, SCHEMA)
        self.assertIn("A", outlines(**VALID)["walls"])

    def test_every_breaker_fails_both(self):
        for name, breaker in BREAKERS.items():
            with self.subTest(case=name):
                data = copy.deepcopy(VALID)
                breaker(data)
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate(data, SCHEMA)
                with self.assertRaises((WallsError, TypeError)):
                    outlines(**data)


if __name__ == "__main__":
    unittest.main()
