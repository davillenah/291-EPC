"""OPT-09: the input schema of the RFQ engine and the engine's own check agree (a valid input passes both; each invalid one fails the schema and raises `RfqError` with an English and a Spanish text)."""
import copy
import json
import unittest
from pathlib import Path

import jsonschema

from epc_rfq import RfqError, build_rfq

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "src" / "epc_rfq" / "schema" / "input.schema.json").read_text(encoding="utf-8"))
VALID = {"board_name": "TS-1",
         "boq": {"items": [{"item_id": "B1", "category": "cable", "description": "cable", "unit": "m", "quantity": 12.5, "source": ["A"], "issues": [], "spec": {}}]},
         "suppliers": [{"name": "Alfa", "contact": "alfa@example.test"}, {"name": "Beta"}], "currency": "ARS", "response_deadline": "2026-12-15", "delivery_site": "Site", "validity_days": 30}
BREAKERS = {
    "no_suppliers": lambda d: d.update(suppliers=[]),
    "supplier_without_name": lambda d: d["suppliers"].__setitem__(0, {"contact": "x"}),
    "supplier_unknown_key": lambda d: d["suppliers"][0].update(phone="1"),
    "blank_currency": lambda d: d.update(currency=" "),
    "bad_deadline_format": lambda d: d.update(response_deadline="15/12/2026"),
    "zero_validity": lambda d: d.update(validity_days=0),
    "blank_site": lambda d: d.update(delivery_site=" "),
    "negative_quantity": lambda d: d["boq"]["items"][0].update(quantity=-1),
    "item_without_unit": lambda d: d["boq"]["items"][0].pop("unit"),
    "no_items": lambda d: d["boq"].update(items=[]),
    "empty_categories": lambda d: d.update(requestable_categories=[]),
}


class InputSchema(unittest.TestCase):
    def test_a_valid_input_passes_both(self):
        jsonschema.Draft202012Validator.check_schema(SCHEMA)
        jsonschema.validate(VALID, SCHEMA)
        build_rfq(**copy.deepcopy(VALID))

    def test_each_invalid_input_fails_both(self):
        for name, breaker in BREAKERS.items():
            doc = copy.deepcopy(VALID)
            breaker(doc)
            with self.subTest(case=name):
                self.assertFalse(jsonschema.Draft202012Validator(SCHEMA).is_valid(doc), "the schema accepts it")
                with self.assertRaises(RfqError) as caught:
                    build_rfq(**doc)
                self.assertTrue(caught.exception.en and caught.exception.es)

    def test_a_missing_term_is_named_by_the_engine_and_the_schema(self):
        for term in ("suppliers", "currency", "response_deadline", "delivery_site", "validity_days"):
            doc = copy.deepcopy(VALID)
            doc.pop(term)
            with self.subTest(term=term):
                self.assertFalse(jsonschema.Draft202012Validator(SCHEMA).is_valid(doc))
                with self.assertRaises(RfqError) as caught:
                    build_rfq(**doc)
                self.assertIn(term, caught.exception.en)


if __name__ == "__main__":
    unittest.main()
