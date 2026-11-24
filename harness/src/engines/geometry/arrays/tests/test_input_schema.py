"""The input schema of the arrays engine and the engine's own checks agree."""
import copy
import json
import unittest
from pathlib import Path

import jsonschema

from epc_arrays import ArraysError, polar, rectangular

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "src" / "epc_arrays" / "schema" / "input.schema.json").read_text(encoding="utf-8"))
RECT = {"kind": "rectangular", "base": [0, 0], "rows": 2, "cols": 3, "row_spacing": 5, "col_spacing": 4, "angle_deg": 0, "max_items": 100}
POLAR = {"kind": "polar", "center": [0, 0], "base": [10, 0], "count": 4, "fill_deg": 360, "rotate_items": True, "max_items": 100}


def run(data):
    args = {k: v for k, v in data.items() if k != "kind"}
    if data["kind"] == "polar":
        return polar(**args)
    return rectangular(args.pop("base"), args.pop("rows"), args.pop("cols"), args.pop("row_spacing"), args.pop("col_spacing"), **args)


BREAKERS = {
    "rect_no_rows": (RECT, lambda d: d.pop("rows")),
    "rect_zero_cols": (RECT, lambda d: d.update(cols=0)),
    "rect_no_limit": (RECT, lambda d: d.pop("max_items")),
    "rect_with_polar_key": (RECT, lambda d: d.update(count=3)),
    "rect_bad_point": (RECT, lambda d: d.update(base=[0])),
    "polar_no_fill": (POLAR, lambda d: d.pop("fill_deg")),
    "polar_fill_out_of_range": (POLAR, lambda d: d.update(fill_deg=400)),
    "polar_with_rect_key": (POLAR, lambda d: d.update(rows=2)),
    "unknown_kind": (RECT, lambda d: d.update(kind="path")),
}


class SchemaAgreesWithTheEngine(unittest.TestCase):
    def test_valid_inputs_pass_both(self):
        for data in (RECT, POLAR):
            with self.subTest(kind=data["kind"]):
                jsonschema.validate(data, SCHEMA)
                self.assertTrue(run(data))

    def test_every_breaker_fails_the_schema_and_the_engine(self):
        for name, (source, breaker) in BREAKERS.items():
            with self.subTest(case=name):
                data = copy.deepcopy(source)
                breaker(data)
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate(data, SCHEMA)
                if name in ("rect_with_polar_key", "polar_with_rect_key", "unknown_kind"):
                    continue          # extra keys / kinds are the schema's job; the functions simply have no such arguments
                with self.assertRaises((ArraysError, TypeError, KeyError)):
                    run(data)


if __name__ == "__main__":
    unittest.main()
