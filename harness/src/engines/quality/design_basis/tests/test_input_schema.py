"""OPT-09: the input schema of the design-basis engine and the engine's own check agree: a valid input passes both; each invalid one fails the schema and raises `DesignBasisError` with an English and a Spanish text."""
import copy
import json
import unittest
from pathlib import Path

import jsonschema

from epc_design_basis import DesignBasisError, build_design_basis_document

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "src" / "epc_design_basis" / "schema" / "input.schema.json").read_text(encoding="utf-8"))
PROFILE = {"project_code": "P-1", "language": "en", "client": {"name": "Client"}, "site": {"address": "Street 1", "country": "AR", "installation_type": "office"},
           "supply": {"source": "utility", "voltage": {"value": 400, "unit": "V"}, "earthing_system": "TT", "short_circuit_level": {"value": 10, "unit": "kA", "origin": "utility letter"}}}
VALID = {"profile": PROFILE, "assumptions": [{"text": "Ambient 40 C", "reason": "typical"}], "norm_status": {"AEA-1": "pending review"}}
BREAKERS = {
    "no_profile_supply": lambda d: d["profile"].pop("supply"),
    "no_earthing_system": lambda d: d["profile"]["supply"].pop("earthing_system"),
    "no_short_circuit_level": lambda d: d["profile"]["supply"].pop("short_circuit_level"),
    "assumption_without_reason": lambda d: d["assumptions"][0].update(reason=" "),
    "unknown_norm_status": lambda d: d["norm_status"].update({"AEA-1": "approved"}),
    "insulation_rules_not_text": lambda d: d.update(insulation_rules={"power": 5}),
}


class InputSchema(unittest.TestCase):
    def test_a_valid_input_passes_both(self):
        jsonschema.Draft202012Validator.check_schema(SCHEMA)
        jsonschema.validate(VALID, SCHEMA)
        self.assertEqual(build_design_basis_document(**copy.deepcopy(VALID))["status"], "draft")

    def test_each_invalid_input_fails_both(self):
        for name, breaker in BREAKERS.items():
            doc = copy.deepcopy(VALID)
            breaker(doc)
            with self.subTest(case=name):
                self.assertFalse(jsonschema.Draft202012Validator(SCHEMA).is_valid(doc), "the schema accepts it")
                with self.assertRaises(DesignBasisError) as caught:
                    build_design_basis_document(**doc)
                self.assertTrue(caught.exception.en and caught.exception.es)


if __name__ == "__main__":
    unittest.main()
