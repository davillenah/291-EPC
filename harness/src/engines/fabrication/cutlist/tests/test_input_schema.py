"""The input schema of the cut-list engine and the engine's own check agree (a valid input passes both; each invalid one fails the schema and raises `CutlistError` with an English and a Spanish text)."""
import copy
import json
import unittest
from pathlib import Path

import jsonschema

from epc_cutlist import CutlistError, build_cutlist

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "src" / "epc_cutlist" / "schema" / "input.schema.json").read_text(encoding="utf-8"))
VALID = {"kerf_mm": 3, "stock": {"steel": [6000, {"length_mm": 3000, "count": 2}]},
         "parts": [{"id": "A", "material": "steel", "length_mm": 1200, "quantity": 2, "size": "L50", "angle_1_deg": 45, "angle_2_deg": -45, "angle_source": "given"}]}
BREAKERS = {
    "no_kerf": lambda d: d.pop("kerf_mm"),
    "negative_kerf": lambda d: d.update(kerf_mm=-1),
    "no_stock": lambda d: d.update(stock={}),
    "empty_material_stock": lambda d: d["stock"].update(steel=[]),
    "zero_stock_length": lambda d: d["stock"].update(steel=[0]),
    "zero_count": lambda d: d["stock"].update(steel=[{"length_mm": 3000, "count": 0}]),
    "no_parts": lambda d: d.update(parts=[]),
    "part_without_id": lambda d: d["parts"][0].pop("id"),
    "part_without_length": lambda d: d["parts"][0].pop("length_mm"),
    "zero_length": lambda d: d["parts"][0].update(length_mm=0),
    "fractional_quantity": lambda d: d["parts"][0].update(quantity=1.5),
    "angle_out_of_range": lambda d: d["parts"][0].update(angle_1_deg=120),
    "bad_angle_source": lambda d: d["parts"][0].update(angle_source="guess"),
    "part_unknown_key": lambda d: d["parts"][0].update(colour="red"),
}


class InputSchema(unittest.TestCase):
    def test_a_valid_input_passes_both(self):
        jsonschema.Draft202012Validator.check_schema(SCHEMA)
        jsonschema.validate(VALID, SCHEMA)
        build_cutlist(**copy.deepcopy(VALID))

    def test_each_invalid_input_fails_both(self):
        for name, breaker in BREAKERS.items():
            doc = copy.deepcopy(VALID)
            breaker(doc)
            with self.subTest(case=name):
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate(doc, SCHEMA)
                with self.assertRaises(CutlistError) as ctx:
                    build_cutlist(**doc) if "kerf_mm" in doc else build_cutlist(**doc, kerf_mm=None)
                self.assertTrue(ctx.exception.en and ctx.exception.es)


if __name__ == "__main__":
    unittest.main()
