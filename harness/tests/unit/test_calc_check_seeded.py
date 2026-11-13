"""MIG-35a, PRD section 21 criterion 6 (seed): every error seeded in a copy of the real pipeline result is caught by calc_check.

The synthetic project of `test_pipeline_wiring` is run through the whole pipeline with a project store (so stage 16 builds manifests), the result is
round-tripped through JSON, and ONE field at a time is changed. A clean run has no finding above `note`. Also checks how stages 13 and 16 use the engine.

Needs the engine packages on PYTHONPATH (the gate's `harness-tests` environment has them, `calc_check` included).
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import epc_calc_check as C
import test_pipeline_wiring as W
from test_manifest import CLOCK, new_store
from test_ssot_wired_pipeline import ANSWERS

from disciplines.electrical_lv.intake.profile import build_profile
from disciplines.electrical_lv.pipeline import STAGES, run
from disciplines.electrical_lv.stages.calc_check_stage import engine_inputs_for_check

RUN_ID = "seed-run"


def rules_of(found):
    return {f["clause"].split(":")[0].replace("project criterion ", "") for f in found}


def stage(run_dict, number):
    return next(r for r in run_dict["results"] if r["stage"] == number)


def row(run_dict, number, tag):
    return next(r for r in stage(run_dict, number)["outputs"]["circuits"] if r["circuit"] == tag)


def memo_cell(tag, column, value):
    def apply(rd):
        doc = next(d for d in stage(rd, 15)["outputs"]["documents"] if d["name"] == "calculation_memo")["document"]
        for block in doc["blocks"]:
            if block.get("type") == "table" and column in [c[0] for c in block["columns"]]:
                names = [c[0] for c in block["columns"]]
                for r in block["rows"]:
                    if r[0] == tag:
                        r[names.index(column)] = value
                        return
        raise AssertionError("cell not found")
    return apply


def set_row(number, tag, key, value):
    return lambda rd: row(rd, number, tag).__setitem__(key, value)


def pop_row(number, tag, key):
    return lambda rd: row(rd, number, tag).pop(key)


def manifest(rd, index=0):
    return stage(rd, 16)["outputs"]["manifests"][index]["manifest"]


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        holder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(holder.cleanup)
        store = new_store(holder.name)
        cls.ctx = W.context(profile=build_profile(ANSWERS), store=store)
        cls.res = run(cls.ctx, run_id=RUN_ID, clock=CLOCK)
        cls.result = json.loads(json.dumps(cls.res.to_dict()))
        cls.project = engine_inputs_for_check(cls.ctx)
        out14 = stage(cls.result, 14)["outputs"]
        work = Path(cls.ctx.work_dir) if cls.ctx.work_dir else Path(store.root) / ".epc" / "runs" / RUN_ID
        cls.files = {f"{out14['directory']}/{f['path']}": (work / out14["directory"] / f["path"]).read_bytes() for f in out14["files"] if f["path"].endswith(".dxf")}

    def check(self, mutation=None, files=True):
        rd = copy.deepcopy(self.result)
        if mutation:
            mutation(rd)
        return C.check_run(rd, project=copy.deepcopy(self.project), files=self.files if files else None, run_id=RUN_ID)


class CleanRunTests(Base):
    def test_the_real_run_is_clean(self):
        found = self.check()
        self.assertEqual([f for f in found if f["severity"] != "note"], [], [(f["clause"], f["field"]) for f in found])

    def test_stage_13_ran_and_reported_without_blocking(self):
        s13 = self.res.results[12]
        self.assertEqual(s13.status, "ok")
        self.assertEqual(s13.outputs["findings_count"], len(s13.findings))
        self.assertEqual(sum(s13.outputs["by_severity"].values()), len(s13.findings))
        self.assertTrue(all(f["verifier"] in ("calc-check", "format-check") for f in s13.findings))
        self.assertEqual([r.status for r in self.res.results][-4:], ["ok"] * 4)
        self.assertEqual(s13.engine_calls[0]["function"], "epc_calc_check.check_run")

    def test_stage_16_checked_documents_and_manifests_and_manifests_carry_the_findings(self):
        s16 = self.res.results[15]
        self.assertEqual(s16.status, "ok")
        self.assertIn("calc_check", s16.outputs)
        carried = {f["id"] for f in manifest(self.result)["findings"]}
        in_run = {f["id"] for r in self.result["results"] if r["stage"] <= 15 for f in r["findings"]}
        self.assertTrue(in_run <= carried)

    def test_the_project_data_is_what_the_chain_used(self):
        self.assertEqual(set(self.project["circuits"]), {r["circuit"] for r in stage(self.result, 8)["outputs"]["circuits"]})
        self.assertEqual(self.project["voltage_v"], stage(self.result, 7)["outputs"]["board"]["voltage_v"])

    def test_wired_stage_table_has_stage_13(self):
        self.assertTrue(STAGES[12].wired)


# mutation, rule that must be reported, text the field or value must contain
CASES = {
    "section lowered": (set_row(8, "T-01", "s_mm2", 1.5), "CC-B09", "T-01/s_mm2"),
    "section lowered (recalculated Iz)": (set_row(8, "T-01", "s_mm2", 1.5), "CC-R01", "T-01/iz_a"),
    "section lowered (neutral)": (set_row(8, "T-01", "s_mm2", 1.5), "CC-R03", "T-01/neutral_mm2"),
    "iz raised": (set_row(8, "T-01", "iz_a", 99.0), "CC-R01", "T-01/iz_a"),
    "iz raised (memo disagrees)": (set_row(8, "T-01", "iz_a", 99.0), "CC-D02", "T-01/Iz A"),
    "voltage drop altered": (set_row(9, "T-01", "own_pct", 0.2), "CC-R02", "T-01/own_pct"),
    "voltage drop flag flipped": (set_row(9, "T-01", "compliant", False), "CC-B03", "T-01/compliant"),
    "voltage drop flag flipped (stage 8 disagrees)": (set_row(9, "T-01", "compliant", False), "CC-D01", "T-01/compliant"),
    "tag duplicated": (lambda rd: stage(rd, 8)["outputs"]["circuits"][1].__setitem__("circuit", "L-01"), "CC-F05", "L-01/circuit"),
    "hash corrupted": (lambda rd: stage(rd, 15)["outputs"]["documents"][0].__setitem__("sha256", "0" * 63 + "g"), "CC-F06", "documents/0/sha256"),
    "document value changed": (memo_cell("T-01", "In A", "63"), "CC-D02", "T-01/In A"),
    "document changed but hash kept": (lambda rd: stage(rd, 15)["outputs"]["documents"][1]["document"].__setitem__("title", "Other"), "CC-D03", "project_summary"),
    "nan inserted": (set_row(8, "T-01", "ib_a", float("nan")), "CC-F03", "ib_a"),
    "key missing": (pop_row(8, "T-01", "iz_a"), "CC-F02", "T-01/iz_a"),
    "stage key missing": (lambda rd: stage(rd, 9)["outputs"].pop("limits_pct"), "CC-F02", "limits_pct"),
    "protection flag flipped": (set_row(8, "T-01", "overload_ok", False), "CC-B08", "T-01/overload_ok"),
    "device changed in stage 11": (set_row(11, "T-01", "device", "MCB (99 A)"), "CC-D01", "T-01/device"),
    "breaking capacity lowered": (set_row(10, "T-01", "icu_ka", 6), "CC-B05", "T-01/breaking_ok"),
    "differential removed": (set_row(12, "T-01", "differential", None), "CC-B11", "T-01/differential"),
    "manifest hash corrupted": (lambda rd: manifest(rd, 0).__setitem__("output_sha256", "e" * 64), "CC-D06", "output_sha256"),
    "manifest revision invalid": (lambda rd: manifest(rd, 0).__setitem__("revision", "R 0"), "CC-F10", "revision"),
    "manifest key missing": (lambda rd: manifest(rd, 0).pop("findings"), "CC-F10", "findings"),
    "drawing summary changed": (lambda rd: stage(rd, 14)["outputs"]["summary"].__setitem__("circuits", 99), "CC-D05", "circuits"),
    "memo summary changed": (lambda rd: stage(rd, 15)["outputs"]["memo_summary"].__setitem__("global", True), "CC-D04", "global"),
}


class SeededErrorTests(Base):
    def test_one_seeded_error_at_a_time_is_caught(self):
        for name, (mutation, rule, fragment) in CASES.items():
            with self.subTest(case=name):
                found = self.check(mutation)
                hits = [f for f in found if rules_of([f]) == {rule}]
                self.assertTrue(hits, f"{rule} not reported; got {sorted(rules_of(found))}")
                self.assertTrue(any(fragment in f["field"] or fragment in str(f["value"]) for f in hits), [f["field"] for f in hits])
                self.assertTrue(any(f["severity"] in ("major", "blocking") for f in found))

    def test_a_changed_drawing_file_is_caught_from_its_bytes(self):
        key = next(iter(self.files))
        changed = dict(self.files, **{key: self.files[key] + b" "})
        found = C.check_run(copy.deepcopy(self.result), project=self.project, files=changed, run_id=RUN_ID)
        self.assertIn("CC-D06", rules_of(found))

    def test_the_seeded_errors_are_found_in_the_stage_findings_of_a_rerun(self):
        # stage 13 itself is deterministic: re-running the checks of its groups on the clean result reports exactly what the stage reported
        again = C.check_run(copy.deepcopy(self.result), project=self.project, run_id=RUN_ID, groups=("recalc", "invariants", "format"))
        shown = [(f["clause"], f["field"], f["severity"]) for f in again]
        reported = [(f["clause"], f["field"], f["severity"]) for f in self.res.results[12].findings]
        self.assertEqual(shown, reported)

    def test_findings_of_two_stages_numbered_per_stage_are_not_a_duplicated_id(self):
        # MIG-3Y: during a run every stage numbers its own findings from F-0001; the pipeline renumbers them across the run only at the end
        def two_stages(rd):
            for number in (8, 9):
                f = dict(self.res.results[12].findings[0]) if self.res.results[12].findings else {
                    "id": "F-0001", "run_id": RUN_ID, "verifier": "calc-check", "severity": "major", "document": "d", "field": "x", "value": None,
                    "expected": None, "clause": "engine result x", "action": "Review.", "evidence": ["e"], "status": "open"}
                f["id"] = "F-0001"
                stage(rd, number)["findings"] = [f]
        found = self.check(two_stages)
        self.assertEqual([f for f in found if rules_of([f]) == {"CC-F08"}], [])

    def test_a_duplicated_finding_id_is_still_caught(self):
        def duplicated(rd):
            f = {"id": "F-0001", "run_id": RUN_ID, "verifier": "calc-check", "severity": "major", "document": "d", "field": "x", "value": None,
                 "expected": None, "clause": "engine result x", "action": "Review.", "evidence": ["e"], "status": "open"}
            stage(rd, 8)["findings"] = [f, dict(f)]
        self.assertIn("CC-F08", rules_of(self.check(duplicated)))
        def across(rd):
            for number in (8, 9):
                stage(rd, number)["findings"] = [{"id": "F-0001", "run_id": RUN_ID, "verifier": "calc-check", "severity": "major", "document": "d", "field": "x",
                                                  "value": None, "expected": None, "clause": "engine result x", "action": "Review.", "evidence": ["e"], "status": "open"}]
        rd = copy.deepcopy(self.result)
        across(rd)
        self.assertIn("CC-F08", rules_of(C.check_run(rd, project=self.project, run_id=RUN_ID, renumbered=True)))

    def test_the_final_result_of_the_pipeline_is_clean_when_declared_renumbered(self):
        found = C.check_run(copy.deepcopy(self.result), project=self.project, files=self.files, run_id=RUN_ID, renumbered=True)
        self.assertNotIn("CC-F08", rules_of(found))


if __name__ == "__main__":
    unittest.main()
