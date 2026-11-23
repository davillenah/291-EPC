"""OPT-09: the input schema of the descriptive-report engine and the engine's own check agree: a valid input passes both; each invalid one fails the schema and raises `DescriptiveReportError` with English and Spanish texts."""
import copy
import json
import sys
import unittest
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parent))
from epc_descriptive_report import DescriptiveReportError, build_descriptive_report   # noqa: E402
from test_descriptive_report import circuits, design_basis                              # noqa: E402

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "src" / "epc_descriptive_report" / "schema" / "input.schema.json").read_text(encoding="utf-8"))


def valid():
    return {"design_basis": design_basis(), "circuits": circuits(), "terminals": {"totals": {"terminals": 12}}, "boq": {"totals": {"lines": 7}},
            "pending_documents": [{"name": "specification", "status": "planned"}], "unreviewed_norm_records": 9}


BREAKERS = {
    "design_basis_without_sections": lambda d: d["design_basis"].pop("sections"),
    "no_circuits": lambda d: d.update(circuits=[]),
    "circuit_without_tag": lambda d: d["circuits"][0].pop("tag"),
    "blank_tag": lambda d: d["circuits"][0].update(tag=" "),
    "negative_section": lambda d: d["circuits"][0].update(s_mm2=-1),
    "pending_document_without_name": lambda d: d["pending_documents"][0].pop("name"),
    "negative_unreviewed": lambda d: d.update(unreviewed_norm_records=-1),
    "terminals_not_object": lambda d: d.update(terminals=[1]),
}


class InputSchema(unittest.TestCase):
    def test_a_valid_input_passes_both(self):
        jsonschema.Draft202012Validator.check_schema(SCHEMA)
        jsonschema.validate(valid(), SCHEMA)
        self.assertEqual(build_descriptive_report(**copy.deepcopy(valid()))["status"], "draft")

    def test_each_invalid_input_fails_both(self):
        for name, breaker in BREAKERS.items():
            doc = valid()
            breaker(doc)
            with self.subTest(case=name):
                self.assertFalse(jsonschema.Draft202012Validator(SCHEMA).is_valid(doc), "the schema accepts it")
                with self.assertRaises(DescriptiveReportError) as caught:
                    build_descriptive_report(**doc)
                self.assertTrue(caught.exception.en and caught.exception.es)


if __name__ == "__main__":
    unittest.main()
