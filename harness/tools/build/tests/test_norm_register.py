"""Tests of harness/tools/build/norm_register.py on a small synthetic repository in a temp dir.

  python3 -m unittest harness/tools/build/tests/test_norm_register.py   (or: python3 harness/tools/build/tests/test_norm_register.py)
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "harness" / "tools" / "build"))
import norm_register as nr  # noqa: E402

SCHEMA = REPO / "harness" / "schemas" / "norm-register.schema.json"
DATA = {"tabla": {"a": 1, "b/c": [10, 20]}}
CODE = '﻿"""x"""\nLIMIT = 3.5\nNAMES = ("a", "b")\nVAL: int = 7\nDYN = len("abc")\n'


def record(id, location, **over):
    r = {"id": id, "kind": "constant", "title": {"es": "t", "en": "t"}, "norm": "AEA 90364-7-771", "edition": "2006", "clause": "771.1", "page": {"printed": 5, "pdf": 9},
         "unit": None, "applies_to": None, "provenance": "norm", "verification": "text", "confidence": "medium", "location": location, "review_point": None,
         "status": "pending", "verified_by": None, "verified_at": None, "issues": [], "note": None}
    r.update(over)
    return r


def jloc(pointer, file="harness/src/engines/validation/e1/src/epc_e1/data.json"):
    return {"type": "json", "file": file, "pointer": pointer}


def cloc(symbol, line, file="harness/src/engines/validation/e1/src/epc_e1/mod.py"):
    return {"type": "code", "file": file, "symbol": symbol, "line": line}


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        pkg = self.root / "harness" / "src" / "engines" / "validation" / "e1" / "src" / "epc_e1"
        (pkg / "norm_register").mkdir(parents=True)
        (pkg / "data.json").write_text(json.dumps(DATA), encoding="utf-8")
        (pkg / "mod.py").write_bytes(CODE.encode("utf-8"))
        self.reg_file = pkg / "norm_register" / "t.json"
        self.write([record("e1.json.a", jloc("/tabla/a")), record("e1.code.limit", cloc("LIMIT", 2), value=3.5)])

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, records, **top):
        doc = {"schema_version": "1.0", "engine": "e1", "topic": "t", "records": records}
        doc.update(top)
        self.reg_file.write_text(json.dumps(doc), encoding="utf-8")

    def run_reg(self):
        return nr.Register(self.root, SCHEMA)


class ValidationTests(Base):
    def test_valid_register_has_no_errors(self):
        reg = self.run_reg()
        self.assertEqual(reg.errors, [])
        self.assertEqual(len(reg.records), 2)

    def test_duplicate_id(self):
        self.write([record("e1.x", jloc("/tabla/a")), record("e1.x", jloc("/tabla/b~1c"))])
        self.assertTrue(any("duplicate id" in e for e in self.run_reg().errors))

    def test_json_pointer_resolves_escapes_and_indexes(self):
        self.write([record("e1.x", jloc("/tabla/b~1c/1"))])
        self.assertEqual(self.run_reg().errors, [])

    def test_json_pointer_missing(self):
        self.write([record("e1.x", jloc("/tabla/zzz"))])
        self.assertTrue(any("does not resolve" in e for e in self.run_reg().errors))

    def test_json_file_missing(self):
        self.write([record("e1.x", jloc("/a", file="harness/src/engines/validation/e1/src/epc_e1/nope.json"))])
        self.assertTrue(any("file not found" in e for e in self.run_reg().errors))

    def test_value_forbidden_for_json(self):
        self.write([record("e1.x", jloc("/tabla/a"), value=1)])
        self.assertTrue(self.run_reg().errors)

    def test_value_required_for_code(self):
        self.write([record("e1.x", cloc("LIMIT", 2))])
        self.assertTrue(self.run_reg().errors)

    def test_code_value_mismatch(self):
        self.write([record("e1.x", cloc("LIMIT", 2), value=4.0)])
        self.assertTrue(any("value differs" in e for e in self.run_reg().errors))

    def test_code_tuple_equals_list_and_annotated_assignment(self):
        self.write([record("e1.a", cloc("NAMES", 3), value=["a", "b"]), record("e1.b", cloc("VAL", 4), value=7)])
        self.assertEqual(self.run_reg().errors, [])

    def test_code_symbol_missing(self):
        self.write([record("e1.x", cloc("NOPE", 2), value=1)])
        self.assertTrue(any("no module-level assignment" in e for e in self.run_reg().errors))

    def test_code_non_literal_is_a_warning(self):
        self.write([record("e1.x", cloc("DYN", 5), value=3)])
        reg = self.run_reg()
        self.assertEqual(reg.errors, [])
        self.assertTrue(any("not a plain literal" in w for w in reg.warnings))

    def test_code_line_drift_is_a_warning(self):
        self.write([record("e1.x", cloc("LIMIT", 4), value=3.5)])
        reg = self.run_reg()
        self.assertEqual(reg.errors, [])
        self.assertTrue(any("record says 4" in w for w in reg.warnings))

    def test_same_location_twice(self):
        self.write([record("e1.a", jloc("/tabla/a")), record("e1.b", jloc("/tabla/a"))])
        self.assertTrue(any("same location" in e for e in self.run_reg().errors))

    def test_bad_enum_and_review_point_format(self):
        self.write([record("e1.a", jloc("/tabla/a"), provenance="made-up")])
        self.assertTrue(self.run_reg().errors)
        self.write([record("e1.a", jloc("/tabla/a"), review_point="nonsense")])
        self.assertTrue(any("review_point" in e for e in self.run_reg().errors))

    def test_topic_must_match_file_name(self):
        self.write([], topic="other")
        self.assertTrue(any("topic" in e for e in self.run_reg().errors))

    def test_pointer_helper(self):
        self.assertEqual(nr.resolve_pointer({"a": [1, 2]}, "/a/1"), (True, 2))
        self.assertFalse(nr.resolve_pointer({"a": [1]}, "/a/01")[0])
        self.assertFalse(nr.resolve_pointer({"a": 1}, "/a/b")[0])


class IndexAndReportTests(Base):
    def make_rules(self):
        aea = self.root / nr.P.engine_src_rel("aea90364") / "epc_aea90364"
        norm = self.root / nr.P.NORM_DATA_REL["aea90364"]            # the AEA rules are norm data in the normative folder (MIG-37a)
        (norm / "rules").mkdir(parents=True)
        (aea / "data").mkdir(parents=True)
        rule = {"id": "g.r1", "tema": "T", "fuente": {"norma": "AEA 90364-7-771", "edicion": "2006", "clausula": "771.1", "pagina_impresa": 4, "pagina_pdf": 8, "verificacion": "visual"}}
        rule2 = {"id": "g.r2", "tema": "U", "fuente": {"norma": "AEA 90364-7-771", "edicion": "2006", "clausula": "", "pagina_impresa": 5}}
        (norm / "rules" / "g.json").write_text(json.dumps({"grupo": "g", "reglas": [rule, rule2]}), encoding="utf-8")
        (norm / "rules" / "_indice.json").write_text("{}", encoding="utf-8")
        review = {"schema_version": "1.0", "points": {"rule:aea-90364-7-771-2006|g.r1": {"status": "approved"}}}
        (aea / "data" / "review.json").write_text(json.dumps(review), encoding="utf-8")
        light = self.root / nr.P.engine_src_rel("lighting") / "epc_lighting" / "rules"
        light.mkdir(parents=True)
        (light / "N.rules.json").write_text(json.dumps({"norm": "N-1", "rules": [{"id": "N-A1", "clause": "Annex", "summary": "s", "value": 100, "unit": "lx", "norm": "N-1"}]}), encoding="utf-8")

    def test_auto_index(self):
        self.make_rules()
        reg = self.run_reg()
        by = {a["id"]: a for a in reg.auto}
        self.assertEqual(set(by), {"aea90364.rule.g-r1", "aea90364.rule.g-r2", "lighting.rule.n-a1"})
        self.assertEqual(by["aea90364.rule.g-r1"]["verification"], "visual")
        self.assertEqual(by["aea90364.rule.g-r1"]["review"], "approved")
        self.assertEqual(by["aea90364.rule.g-r2"]["verification"], "text")
        self.assertEqual(by["aea90364.rule.g-r2"]["review"], "pending")
        self.assertEqual(by["lighting.rule.n-a1"]["clause"], "Annex")
        self.assertIn("aea90364.rule.g-r2", [i for i, _, _ in reg.no_clause()])

    def test_report_is_deterministic_and_check_detects_staleness(self):
        self.make_rules()
        args = ["--root", str(self.root), "--schema", str(SCHEMA)]
        self.assertEqual(nr.main(args + ["--report", "--check"]), 1)          # no report yet
        self.assertEqual(nr.main(args + ["--report"]), 0)
        target = self.root / "harness" / "docs" / "NORM_REGISTER.md"
        text = target.read_text(encoding="utf-8")
        self.assertIn("## Sin cláusula", text)
        self.assertIn("e1.code.limit", text)
        self.assertEqual(nr.main(args + ["--report", "--check"]), 0)
        target.write_text(text + "x\n", encoding="utf-8")
        self.assertEqual(nr.main(args + ["--report", "--check"]), 1)

    def test_check_exit_code(self):
        args = ["--root", str(self.root), "--schema", str(SCHEMA), "--check"]
        self.assertEqual(nr.main(args), 0)
        self.write([record("e1.x", jloc("/nope"))])
        self.assertEqual(nr.main(args), 1)


class SchemaTests(unittest.TestCase):
    def test_schema_is_draft7_json(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "http://json-schema.org/draft-07/schema#")

    def test_record_with_extra_field_is_rejected(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        doc = {"schema_version": "1.0", "engine": "e1", "topic": "t", "records": [dict(record("e1.a", jloc("/a")), surprise=1)]}
        self.assertTrue(list(jsonschema.Draft7Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).iter_errors(doc)))


class RegisterGlobTests(unittest.TestCase):
    def test_every_engine_group_is_searched(self):
        import epc_paths
        for name, rel in epc_paths.ENGINE_FOLDERS_REL.items():
            self.assertTrue(any(rel.startswith(g + "/") for g in nr.ENGINE_GROUPS), name)

    def test_src_index_is_the_last_src_folder(self):
        parts = ("harness", "src", "engines", "cad", "dxf", "src", "epc_dxf", "norm_register", "x.json")
        self.assertEqual(parts[nr._src_index(parts) - 1], "dxf")


if __name__ == "__main__":
    unittest.main()
