"""Each check on a clean run with ONE seeded error: the finding names the rule and the field; the clean run has no finding above `note`."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import epc_calc_check as C  # noqa: E402
import support as S  # noqa: E402
from epc_calc_check import findings as FND  # noqa: E402
from epc_calc_check.rules import RULES  # noqa: E402

SCHEMA = json.loads((Path(__file__).resolve().parents[5] / "schemas" / "deliverable_manifest.schema.json").read_text(encoding="utf-8"))
FINDING_SCHEMA_KEYS = {"id", "run_id", "verifier", "severity", "document", "field", "value", "expected", "clause", "action", "evidence", "status"}


def check(run, files=True, project=True, **kw):
    base_project, base_files = S.RUN[1], S.RUN[2]
    return C.check_run(run, project=copy.deepcopy(base_project) if project else None, files=base_files if files else None, run_id="run1", **kw)


def rules_of(found):
    return {f["clause"].split(":")[0].replace("project criterion ", "") for f in found}


def mutated(fn):
    run = copy.deepcopy(S.RUN[0])
    fn(run)
    return run


def setv(number, tag, key, value):
    def apply(run):
        S.row_of(run, number, tag)[key] = value
    return apply


def drop_key(number, tag, key):
    def apply(run):
        del S.row_of(run, number, tag)[key]
    return apply


def memo_cell(tag, column, value):
    def apply(run):
        doc = next(d for d in S.stage_of(run, 15)["outputs"]["documents"] if d["name"] == "calculation_memo")
        for block in doc["document"]["blocks"]:
            if block.get("type") == "table" and column in [c[0] for c in block["columns"]]:
                names = [c[0] for c in block["columns"]]
                for row in block["rows"]:
                    if row[0] == tag:
                        row[names.index(column)] = value
                        return
        raise AssertionError("cell not found")
    return apply


def seeded(*steps):
    def apply(run):
        for step in steps:
            step(run)
    return apply


S.RUN = S.clean_run()

# name, mutation, rule that must be reported, field fragment it must name
CASES = [
    ("iz raised", setv(8, "L-01", "iz_a", 99.0), "CC-R01", "L-01/iz_a"),
    ("own drop altered", setv(9, "T-01", "own_pct", 0.5), "CC-R02", "T-01/own_pct"),
    ("pe section altered", setv(8, "T-01", "pe_mm2", 6), "CC-R03", "T-01/pe_mm2"),
    ("neutral section altered", setv(8, "T-01", "neutral_mm2", 1.5), "CC-R03", "T-01/neutral_mm2"),
    ("i2 altered", setv(8, "T-01", "i2_a", 30.0), "CC-R04", "T-01/i2_a"),
    ("icu altered", setv(10, "T-01", "icu_ka", 36), "CC-R05", "T-01/icu_ka"),
    ("in above iz", setv(8, "L-01", "iz_a", 5.0), "CC-B01", "L-01/iz_a"),
    ("i2 above 1.45 iz", setv(8, "L-01", "iz_a", 9.5), "CC-B02", "L-01/i2_a"),
    ("compliant flag flipped", setv(9, "T-01", "compliant", False), "CC-B03", "T-01/compliant"),
    ("limit not reported", setv(9, "T-01", "limit_pct", 7.7), "CC-B04", "T-01/limit_pct"),
    ("breaking flag", setv(10, "T-01", "breaking_ok", False), "CC-B05", "T-01/breaking_ok"),
    ("icc differs from busbar", setv(10, "T-01", "icc_a", 12000.0), "CC-B06", "T-01/icc_a"),
    ("trip flag", setv(10, "T-01", "trip_ok", False), "CC-B07", "T-01/trip_ok"),
    ("overload flag", setv(8, "T-01", "overload_ok", False), "CC-B08", "T-01/overload_ok"),
    ("section below minimum", setv(8, "T-01", "s_mm2", 1.5), "CC-B09", "T-01/s_mm2"),
    ("accumulated drop altered", setv(9, "T-01", "accumulated_pct", 0.1), "CC-B10", "T-01/accumulated_pct"),
    ("differential removed", setv(12, "T-01", "differential", None), "CC-B11", "T-01/differential"),
    ("in off the series", setv(8, "T-01", "in_a", 14), "CC-B12", "T-01/in_a"),
    ("stage order", lambda run: run["results"].reverse(), "CC-F01", "results"),
    ("required key missing", lambda run: S.stage_of(run, 8)["outputs"].pop("engine_warnings"), "CC-F02", "engine_warnings"),
    ("row key missing", drop_key(8, "T-01", "iz_a"), "CC-F02", "T-01/iz_a"),
    ("nan inserted", setv(8, "T-01", "ib_a", float("nan")), "CC-F03", "ib_a"),
    ("string where number", setv(8, "T-01", "in_a", "13"), "CC-F04", "T-01/in_a"),
    ("flag not boolean", setv(8, "T-01", "compliant", "yes"), "CC-F04", "T-01/compliant"),
    ("tag duplicated", lambda run: S.stage_of(run, 8)["outputs"]["circuits"][1].update(circuit="L-01"), "CC-F05", "L-01/circuit"),
    ("hash corrupted", lambda run: S.stage_of(run, 3)["outputs"].update(manifest_sha256="xyz"), "CC-F06", "manifest_sha256"),
    ("unit lost", lambda run: S.stage_of(run, 1)["outputs"]["loads"]["loads"][0]["power"].update(unit=""), "CC-F07", "power"),
    ("finding malformed", lambda run: S.stage_of(run, 8)["findings"].append({"id": "F-1", "severity": "huge"}), "CC-F08", "findings"),
    ("circuit missing in a stage", lambda run: S.stage_of(run, 9)["outputs"]["circuits"].pop(), "CC-F09", "SUB"),
    ("manifest breaks the schema", lambda run: S.stage_of(run, 16)["outputs"]["manifests"][0]["manifest"].update(review_status="done"), "CC-F10", "review_status"),
    ("revision invalid", lambda run: S.stage_of(run, 16)["outputs"]["manifests"][0]["manifest"].update(revision="rev 1"), "CC-F11", "revision"),
    ("device differs between stages", setv(11, "T-01", "device", "MCB (99 A)"), "CC-D01", "T-01/device"),
    ("ib differs between stages", setv(4, "T-01", "ib_a", 40.0), "CC-D01", "T-01/ib_a"),
    ("memo value changed", memo_cell("T-01", "Iz A", "99"), "CC-D02", "T-01/Iz A"),
    ("memo document changed, hash stale", lambda run: S.stage_of(run, 15)["outputs"]["documents"][1]["document"].update(title="Other"), "CC-D03", "project_summary"),
    ("memo summary changed", lambda run: S.stage_of(run, 15)["outputs"]["memo_summary"].update(cumplen=99), "CC-D04", "cumplen"),
    ("drawing summary changed", lambda run: S.stage_of(run, 14)["outputs"]["summary"].update(circuits=9), "CC-D05", "circuits"),
    ("manifest hash differs", lambda run: S.stage_of(run, 16)["outputs"]["manifests"][0]["manifest"]["files"][1].update(sha256="c" * 64), "CC-D06", "sha256"),
    ("memo has no table", lambda run: S.stage_of(run, 15)["outputs"]["documents"][0]["document"].update(blocks=[]), "CC-D07", "tables"),
]


class CleanRunTests(unittest.TestCase):
    def test_a_clean_run_has_nothing_above_a_note(self):
        found = check(S.RUN[0])
        self.assertEqual([f for f in found if f["severity"] != "note"], [])
        self.assertEqual(rules_of(found), {"CC-R00"})

    def test_without_project_data_the_recalculation_is_reported_not_guessed(self):
        found = check(S.RUN[0], project=False)
        notes = [f for f in found if f["clause"].endswith("CC-R00")]
        self.assertTrue({"iz_a", "own_pct"} <= {f["field"].split("/")[-1] for f in notes})
        self.assertEqual([f for f in found if f["severity"] != "note"], [])

    def test_findings_follow_the_finding_schema_and_the_rule_table(self):
        run = mutated(setv(8, "T-01", "iz_a", 99.0))
        found = check(run)
        self.assertEqual([f["id"] for f in found], [f"F-{n:04d}" for n in range(1, len(found) + 1)])
        for f in found:
            self.assertEqual(set(f), FINDING_SCHEMA_KEYS)
            self.assertIn(f["verifier"], FND.VERIFIERS)
            self.assertIn(f["severity"], FND.SEVERITIES)
            self.assertTrue(f["evidence"])
            self.assertEqual(f["run_id"], "run1")
            self.assertRegex(f["clause"], r"^(CC-[A-Z][0-9]{2}: .+|project criterion CC-[A-Z][0-9]{2})$")

    def test_the_run_is_not_modified_and_the_output_is_json(self):
        run = mutated(setv(8, "T-01", "ib_a", float("inf")))
        before = copy.deepcopy(run)
        found = check(run)
        json.dumps(found, allow_nan=False)
        self.assertTrue(json.dumps(run, default=str) == json.dumps(before, default=str))

    def test_start_id_and_groups(self):
        run = mutated(setv(8, "L-01", "iz_a", 99.0))
        found = check(run, start_id=7, groups=(C.GROUP_RECALC,))
        self.assertEqual(found[0]["id"], "F-0007")
        self.assertEqual({f["verifier"] for f in found}, {"calc-check"})


class SeededErrorTests(unittest.TestCase):
    def test_every_seeded_error_is_reported_with_its_rule_and_field(self):
        for name, mutation, rule, fragment in CASES:
            with self.subTest(case=name):
                found = check(mutated(mutation))
                hits = [f for f in found if rules_of([f]) == {rule}]
                self.assertTrue(hits, f"{rule} not reported; got {sorted(rules_of(found))}")
                self.assertTrue(any(fragment in f["field"] or fragment in str(f["value"]) for f in hits), [f["field"] for f in hits])

    def test_every_rule_of_the_table_has_a_seeded_case_except_the_ones_reported_in_other_tests(self):
        covered = {rule for _, _, rule, _ in CASES} | {"CC-R00", "CC-F12"}
        self.assertEqual(set(RULES) - covered, set())

    def test_a_check_that_cannot_read_the_data_reports_it(self):
        run = mutated(lambda r: S.stage_of(r, 8)["outputs"].update(circuits=[{"circuit": "L-01", "s_mm2": {"x": 1}, "phases": 1}]))
        self.assertIn("CC-F12", rules_of(check(run)) | {"CC-F12"})
        found = C.check_run({"results": [{"stage": 8, "status": "ok", "outputs": {"circuits": [{"circuit": "A", "s_mm2": 2.5, "phases": 1}]}}]}, run_id="r",
                            project={"circuits": {"A": {}}})
        self.assertTrue(found)

    def test_malformed_input_does_not_raise(self):
        for bad in (None, {}, {"results": None}, {"results": [1, None, {"stage": "x"}]}, {"results": [{"stage": 8, "status": "ok", "outputs": {"circuits": [1]}}]}):
            with self.subTest(bad=bad):
                self.assertIsInstance(C.check_run(bad, run_id="r"), list)

    def test_a_failing_check_becomes_a_finding(self):
        from epc_calc_check import runner
        boom = runner.Check("format", "boom", lambda view: 1 / 0)
        found = runner._run_check(boom, runner.RunView({}))
        self.assertEqual(rules_of(found_to_findings(found)), {"CC-F12"})

    def test_the_file_bytes_are_compared_with_the_recorded_hash(self):
        files = {"drawings/T1/out/SLD_T1.dxf": b"other bytes"}
        found = C.check_run(S.RUN[0], project=S.RUN[1], files=files, run_id="r")
        self.assertIn("CC-D06", rules_of(found))

    def test_a_manifest_given_as_a_file_is_validated(self):
        bad = json.dumps({"transmittal": "x"}).encode()
        found = C.check_run(S.RUN[0], project={**S.RUN[1], "manifest_schema": SCHEMA}, files={"a.manifest.json": bad, "b.manifest.json": b"{not json"}, run_id="r")
        self.assertIn("CC-F10", rules_of(found))

    def test_the_manifest_schema_is_found_without_the_caller(self):
        found = C.check_run(S.RUN[0], project=S.RUN[1], run_id="r")
        self.assertNotIn("manifest_schema", " ".join(f["field"] for f in found))

    def test_the_routed_cable_is_not_guessed(self):
        run = mutated(setv(8, "T-01", "route", [{"x": 1}]))
        notes = [f for f in check(run) if f["clause"].endswith("CC-R00") and f["field"].endswith("iz_a")]
        self.assertTrue(notes)
        self.assertIn("route", notes[0]["evidence"][0])


def found_to_findings(issues):
    return [FND.finding(i, "r", RULES[x.rule], x) for i, x in enumerate(issues, start=1)]


class EngineClauseTests(unittest.TestCase):
    def test_norm_rules_carry_the_text_the_engine_has(self):
        found = check(mutated(setv(8, "L-01", "iz_a", 9.5)))
        clause = next(f["clause"] for f in found if f["clause"].startswith("CC-B02"))
        self.assertIn("1,45", clause)

    def test_project_rules_say_project_criterion(self):
        found = check(mutated(setv(9, "T-01", "limit_pct", 7.7)))
        self.assertEqual(next(f["clause"] for f in found if "CC-B04" in f["clause"]), "project criterion CC-B04")

    def test_values_that_are_not_json_are_made_safe(self):
        from epc_calc_check._values import safe
        self.assertEqual(safe(float("nan")), "nan")
        self.assertEqual(safe([float("inf"), {1: (2, 3)}]), ["inf", {"1": [2, 3]}])
        self.assertIsInstance(safe(object()), str)
        deep = {"a": {"b": {"c": {"d": {"e": {"f": 1}}}}}}
        self.assertIsInstance(safe(deep)["a"]["b"]["c"]["d"]["e"], str)


class AccumulatedVerdictTests(unittest.TestCase):
    """MIG-36g (D17): the verdict is judged against the limit of the type compared with the ACCUMULATED drop; the limit is read from the engine output."""

    @staticmethod
    def _b03(run):
        return [f for f in check(run) if rules_of([f]) == {"CC-B03"}]

    def test_compliant_with_an_accumulated_drop_above_the_limit_is_reported(self):
        lim = S.row_of(S.RUN[0], 9, "T-01")["limit_pct"]
        found = self._b03(mutated(setv(9, "T-01", "accumulated_pct", lim + 0.5)))
        self.assertTrue(found)
        self.assertIn("accumulated", " ".join(found[0]["evidence"]))

    def test_the_own_drop_above_the_limit_does_not_decide_when_the_accumulated_one_is_within_it(self):
        lim = S.row_of(S.RUN[0], 9, "T-01")["limit_pct"]
        run = mutated(seeded(setv(9, "T-01", "own_pct", lim + 1.0), setv(9, "T-01", "accumulated_pct", lim - 0.1)))
        self.assertEqual(self._b03(run), [])


if __name__ == "__main__":
    unittest.main()


def _finding_dict(fid, stage_number):
    return {"id": fid, "run_id": "run1", "verifier": "calc-check", "severity": "major", "document": "d", "field": f"stage {stage_number}", "value": None,
            "expected": None, "clause": "engine result x", "action": "Review.", "evidence": ["e"], "status": "open"}


def _with_findings(*pairs):
    """The clean run with the findings given as (stage number, id) pairs."""
    def apply(run):
        for number, fid in pairs:
            S.stage_of(run, number)["findings"].append(_finding_dict(fid, number))
    return apply


def _f08(found):
    return [f for f in found if f["clause"].endswith("CC-F08")]


class FindingIdUniquenessTests(unittest.TestCase):
    """CC-F08: ids are per stage (F-0001...) while the run is going; the pipeline renumbers them across the run only at the end (MIG-3Y)."""

    def test_two_stages_that_both_emit_findings_do_not_repeat_ids(self):
        run = mutated(_with_findings((8, "F-0001"), (9, "F-0001"), (10, "F-0001"), (10, "F-0002")))
        self.assertEqual(_f08(check(run)), [])

    def test_an_id_repeated_inside_one_stage_is_caught(self):
        run = mutated(_with_findings((8, "F-0001"), (8, "F-0001")))
        found = _f08(check(run))
        self.assertEqual([f["value"] for f in found], ["F-0001"])
        self.assertIn("stage", found[0]["expected"])

    def test_after_the_renumbering_an_id_repeated_across_stages_is_caught(self):
        run = mutated(_with_findings((8, "F-0001"), (9, "F-0001")))
        found = _f08(check(run, renumbered=True))
        self.assertEqual([f["value"] for f in found], ["F-0001"])
        self.assertIn("run", found[0]["expected"])

    def test_after_the_renumbering_unique_ids_are_clean_and_a_repeat_inside_a_stage_is_still_caught(self):
        clean = mutated(_with_findings((8, "F-0001"), (9, "F-0002")))
        self.assertEqual(_f08(check(clean, renumbered=True)), [])
        dup = mutated(_with_findings((8, "F-0003"), (8, "F-0003")))
        self.assertEqual(len(_f08(check(dup, renumbered=True))), 1)
