"""electrical_lv intake: form, profile, hashing, load list (synthetic data only, built in temp folders).

  PYTHONPATH=harness/src python -m pytest harness/tests/unit -q
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from disciplines.electrical_lv.intake.form import IntakeError, validate_answers
from disciplines.electrical_lv.intake.hashing import build_manifest, sha256_file, verify_inputs
from disciplines.electrical_lv.intake.loads import LoadListError, read_load_list
from disciplines.electrical_lv.intake.profile import build_profile, load_template
from disciplines.electrical_lv.intake.schema_check import validate

ANSWERS = {
    "project_code": "TEST-001",
    "client": {"name": "Synthetic Client"},
    "site": {"address": "Nowhere 1", "installation_type": "test"},
    "supply": {"earthing_system": "TT", "short_circuit_level": {"value": 6, "unit": "kA", "origin": "declared by test"}},
    "language": "en",
}
LOADS = {
    "schema_version": "1.0",
    "areas": [{"id": "A1", "name": "Area one"}],
    "loads": [{"id": "L1", "description": "lamp", "area": "A1", "kind": "lighting", "power": {"value": 100, "unit": "W"}, "phases": 1}],
}


class FormTests(unittest.TestCase):
    def test_valid_answers_have_no_errors(self):
        self.assertEqual(validate_answers(ANSWERS), [])

    def test_missing_earthing_and_short_circuit_are_explicit_d24_errors(self):
        bad = copy.deepcopy(ANSWERS)
        bad["supply"] = {}
        errors = validate_answers(bad)
        self.assertEqual(len([e for e in errors if "D24" in e]), 2)
        self.assertTrue(any("earthing_system" in e for e in errors))
        self.assertTrue(any("short_circuit_level" in e for e in errors))

    def test_unknown_field_and_bad_scheme_are_rejected(self):
        bad = copy.deepcopy(ANSWERS)
        bad["extra"] = 1
        bad["supply"]["earthing_system"] = "XX"
        errors = validate_answers(bad)
        self.assertTrue(any(e.startswith("extra") for e in errors))
        self.assertTrue(any("earthing_system" in e for e in errors))

    def test_validator_rejects_bool_as_number_and_integer(self):
        self.assertTrue(validate(True, {"type": "number"}))
        self.assertTrue(validate(True, {"type": "integer", "enum": [1, 3]}))
        self.assertEqual(validate(3, {"type": "integer", "enum": [1, 3]}), [])


class ProfileTests(unittest.TestCase):
    def test_profile_follows_the_template_and_keeps_its_normative_defaults(self):
        template = load_template()
        profile = build_profile(ANSWERS)
        self.assertEqual(set(profile), set(template))
        self.assertEqual(profile["normative_profile"], template["normative_profile"])
        self.assertEqual(profile["supply"]["earthing_system"], "TT")
        self.assertIsNone(profile["supply"]["source"])
        self.assertIsNone(profile["engineer_of_record"]["name"])
        self.assertEqual(profile["site"]["country"], "AR")

    def test_profile_without_d24_data_raises_with_every_reason(self):
        bad = copy.deepcopy(ANSWERS)
        del bad["supply"]["short_circuit_level"]
        with self.assertRaises(IntakeError) as ctx:
            build_profile(bad)
        self.assertTrue(any("short_circuit_level" in e for e in ctx.exception.errors))

    def test_building_does_not_modify_the_answers_or_the_template(self):
        before = copy.deepcopy(ANSWERS)
        build_profile(ANSWERS)
        self.assertEqual(ANSWERS, before)
        self.assertIsNone(load_template()["supply"]["earthing_system"])


class HashingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "plans").mkdir()
        (self.root / "b.txt").write_text("bbb", encoding="utf-8")
        (self.root / "plans" / "a.dxf").write_text("aaa", encoding="utf-8")

    def test_manifest_is_sorted_and_deterministic(self):
        first, second = build_manifest(self.root), build_manifest(self.root)
        self.assertEqual(first, second)
        self.assertEqual([f["path"] for f in first["files"]], ["b.txt", "plans/a.dxf"])
        self.assertEqual(first["files"][0]["sha256"], sha256_file(self.root / "b.txt"))

    def test_same_content_in_another_folder_gives_the_same_manifest_hash(self):
        with tempfile.TemporaryDirectory() as other:
            (Path(other) / "plans").mkdir()
            (Path(other) / "b.txt").write_text("bbb", encoding="utf-8")
            (Path(other) / "plans" / "a.dxf").write_text("aaa", encoding="utf-8")
            self.assertEqual(build_manifest(other)["manifest_sha256"], build_manifest(self.root)["manifest_sha256"])

    def test_untouched_inputs_verify_clean(self):
        self.assertEqual(verify_inputs(build_manifest(self.root), self.root), [])

    def test_changed_missing_and_added_files_are_detected(self):
        manifest = build_manifest(self.root)
        (self.root / "b.txt").write_text("changed", encoding="utf-8")
        (self.root / "plans" / "a.dxf").unlink()
        (self.root / "new.txt").write_text("n", encoding="utf-8")
        problems = {(p["path"], p["problem"]) for p in verify_inputs(manifest, self.root)}
        self.assertEqual(problems, {("b.txt", "changed"), ("plans/a.dxf", "missing"), ("new.txt", "added")})


class LoadListTests(unittest.TestCase):
    def _write(self, data):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "loads.json"
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return path

    def test_valid_list_is_read(self):
        self.assertEqual(read_load_list(self._write(LOADS)), LOADS)

    def test_unknown_field_is_rejected(self):
        bad = copy.deepcopy(LOADS)
        bad["loads"][0]["colour"] = "red"
        with self.assertRaises(LoadListError) as ctx:
            read_load_list(self._write(bad))
        self.assertTrue(any("colour" in e for e in ctx.exception.errors))

    def test_bad_values_and_bad_json_are_rejected(self):
        bad = copy.deepcopy(LOADS)
        bad["loads"][0].update(phases=2, kind="toaster")
        bad["loads"][0]["power"]["value"] = 0
        with self.assertRaises(LoadListError) as ctx:
            read_load_list(self._write(bad))
        self.assertEqual(len(ctx.exception.errors), 3)
        with self.assertRaises(LoadListError):
            read_load_list(self._write("{not json"))


class NoClientDataTests(unittest.TestCase):
    def test_discipline_folder_holds_only_code_and_readmes(self):
        base = Path(__file__).resolve().parents[2] / "src" / "disciplines"
        odd = [p.name for p in base.rglob("*") if p.is_file() and p.suffix not in (".py", ".md", ".pyc") and p.name != "preconditions.json"]
        self.assertEqual(odd, [])


if __name__ == "__main__":
    unittest.main()
