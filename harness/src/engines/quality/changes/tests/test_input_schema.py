"""The input schema of the changes engine and the engine's own checks agree."""
import copy
import json
import unittest
from pathlib import Path

import jsonschema

from epc_changes import ChangesError, compare

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "src" / "epc_changes" / "schema" / "input.schema.json").read_text(encoding="utf-8"))
GOOD = {"previous": [{"id": "C1", "a": 1}], "current": [{"id": "C1", "a": 2}], "id_field": "id", "ignore": [], "max_changes": 10}
BREAKERS = {
    "no_previous": lambda d: d.pop("previous"),
    "no_ignore": lambda d: d.pop("ignore"),
    "no_limit": lambda d: d.pop("max_changes"),
    "zero_limit": lambda d: d.update(max_changes=0),
    "empty_id_field": lambda d: d.update(id_field=""),
    "records_not_a_list": lambda d: d.update(current={"id": 1}),
    "ignore_not_names": lambda d: d.update(ignore=[1]),
    "unknown_key": lambda d: d.update(extra=1),
}


class SchemaAgreesWithTheEngine(unittest.TestCase):
    def test_valid_input_passes_both(self):
        jsonschema.validate(GOOD, SCHEMA)
        self.assertEqual(compare(**GOOD)["summary"]["changed"], 1)

    def test_every_breaker_fails_the_schema_and_the_engine(self):
        for name, breaker in BREAKERS.items():
            with self.subTest(case=name):
                data = copy.deepcopy(GOOD)
                breaker(data)
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate(data, SCHEMA)
                with self.assertRaises((ChangesError, TypeError)):
                    compare(**data)


if __name__ == "__main__":
    unittest.main()
