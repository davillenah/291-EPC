"""electrical_lv requirements: design basis and input verification (synthetic data)."""
import copy
import unittest

from disciplines.electrical_lv.intake.form import IntakeError
from disciplines.electrical_lv.intake.hashing import manifest_hash
from disciplines.electrical_lv.intake.profile import build_profile
from disciplines.electrical_lv.intake.schema_check import load_schema, validate
from disciplines.electrical_lv.requirements.design_basis import build_design_basis
from disciplines.electrical_lv.requirements.verify_inputs import verify_inputs

ANSWERS = {
    "project_code": "TEST-001",
    "client": {"name": "Synthetic Client"},
    "site": {"address": "Nowhere 1", "installation_type": "test"},
    "supply": {"earthing_system": "TN", "short_circuit_level": {"value": 10, "unit": "kA", "origin": "declared by test"}},
    "criteria": {"set": "set-a", "exceptions": ["x1"]},
    "language": "en",
}
REQS = {"schema_version": "1.0", "items": [{"id": "R-001", "text": "keep it simple", "source": "minutes", "status": "open"}]}
FINDING_REQUIRED = ("id", "run_id", "verifier", "severity", "document", "field", "value", "expected", "clause", "action", "evidence")
SEVERITIES = ("blocking", "major", "minor", "note")


def loads(**over):
    data = {
        "schema_version": "1.0",
        "areas": [{"id": "A1", "name": "One", "plan": "plans/a1.dxf"}],
        "loads": [{"id": "L1", "description": "lamp", "area": "A1", "kind": "lighting", "power": {"value": 1, "unit": "kW"}, "phases": 3}],
    }
    data.update(over)
    return data


def manifest(*paths):
    files = [{"path": p, "sha256": "0" * 64} for p in paths]
    return {"algorithm": "sha256", "files": files, "manifest_sha256": manifest_hash(files)}


class DesignBasisTests(unittest.TestCase):
    def test_copies_profile_merges_criteria_and_records_assumptions(self):
        profile = build_profile(ANSWERS)
        basis = build_design_basis(
            profile, criteria={"exceptions": ["x2"]},
            assumptions=[{"text": "ambient as site", "reason": "no data given"}], requirements=REQS)
        self.assertEqual(basis["normative_profile"], profile["normative_profile"])
        self.assertEqual(basis["supply"], profile["supply"])
        self.assertEqual(basis["criteria"], {"set": "set-a", "exceptions": ["x1", "x2"]})
        self.assertEqual(basis["assumptions"], [{"id": "A-01", "text": "ambient as site", "reason": "no data given"}])
        self.assertEqual(basis["requirements"], REQS["items"])
        basis["supply"]["earthing_system"] = "IT"
        self.assertEqual(profile["supply"]["earthing_system"], "TN")

    def test_assumption_without_reason_is_refused(self):
        with self.assertRaises(ValueError):
            build_design_basis(build_profile(ANSWERS), assumptions=[{"text": "something"}])

    def test_profile_without_d24_data_is_refused(self):
        profile = build_profile(ANSWERS)
        profile["supply"]["earthing_system"] = None
        with self.assertRaises(IntakeError):
            build_design_basis(profile)

    def test_requirements_schema_accepts_the_sample_and_rejects_a_bad_status(self):
        schema = load_schema("requirements.schema.json")
        self.assertEqual(validate(REQS, schema), [])
        bad = copy.deepcopy(REQS)
        bad["items"][0]["status"] = "maybe"
        self.assertTrue(validate(bad, schema))


class VerifyInputsTests(unittest.TestCase):
    def rules(self, findings):
        return [f["clause"].split()[-1] for f in findings]

    def test_consistent_inputs_have_no_findings(self):
        self.assertEqual(verify_inputs(loads(), manifest("plans/a1.dxf")), [])

    def test_empty_loads_unknown_area_missing_plan_and_duplicates(self):
        self.assertEqual(self.rules(verify_inputs(loads(loads=[]), manifest("plans/a1.dxf"))), ["IV-01"])
        data = loads()
        data["loads"].append(dict(data["loads"][0], id="L2", area="ZZ"))
        data["loads"].append(dict(data["loads"][0]))
        found = verify_inputs(data, manifest())
        self.assertEqual(self.rules(found), ["IV-02", "IV-03", "IV-04"])

    def test_findings_have_the_finding_shape(self):
        found = verify_inputs(loads(loads=[]), manifest(), run_id="run-7")
        self.assertEqual(len(found), 2)
        for n, f in enumerate(found, start=1):
            for key in FINDING_REQUIRED:
                self.assertIn(key, f)
            self.assertEqual(f["id"], f"F-{n:04d}")
            self.assertEqual(f["run_id"], "run-7")
            self.assertEqual(f["verifier"], "input-verifier")
            self.assertIn(f["severity"], SEVERITIES)
            self.assertTrue(f["evidence"])


if __name__ == "__main__":
    unittest.main()
