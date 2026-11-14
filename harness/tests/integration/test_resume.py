"""Re-run from a stage: `epc run --from-stage N` reuses the recorded stages before N and gives the same result as a full run.

The correction here touches only late inputs (the bill of quantities allowance, read by stage 11), so stages 1..10 are reused. The property that
matters is that the resumed project holds exactly what a full run with the same inputs would hold.
Run: python -m pytest harness/tests/integration/test_resume.py
"""
import json
import unittest

import synthetic_lv as S

from disciplines.electrical_lv.store import ProjectStore
from epc_platform.events import EventLog
from epc_platform.workflow import Workflow

DATE = "2026-03-04"


def corrected_inputs(work, allowance):
    path, doc = S.resolved_engine_inputs(work, DATE)
    doc["boq"] = dict(doc.get("boq") or {}, allowance_pct=allowance)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path


def run_again(run, inputs_file, run_id, revision, *extra):
    return S.envelope(run.root, "run", S.CODE, "--loads", str(S.GOLDEN / "loads.json"), "--engine-inputs", str(inputs_file), "--run-id", run_id,
                      "--revision", revision, "--detail", *extra, *S.ORCHESTRATOR)


def open_correction(run):
    """The engineer submits the draft and records a correction, which is what lets the project run again (state `corrected`)."""
    Workflow(run.project, EventLog.for_project(run.project, S.clock), ProjectStore(run.project)).transition("submit_for_review", "engineer_of_record", "eng-1", run_id="review")
    note = run.work / "correction.json"
    note.write_text(json.dumps([{"note": "late input corrected"}]), encoding="utf-8")
    code, _answer = S.envelope(run.root, "review", S.CODE, "--corrections", str(note), *S.ENGINEER)
    assert code == 0


def outputs(run, number):
    path = next(p for p in run.stage_files() if p.name.startswith(f"stage_{number:02d}_"))
    return S.read_json(path)["outputs"]


class ResumeFromStage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.first = S.SyntheticRun(drawing_date=DATE).start()                      # R0, full run, default allowance
        open_correction(cls.first)
        cls.resumed_file = corrected_inputs(cls.first.work, 7.5)
        cls.code, cls.answer = run_again(cls.first, cls.resumed_file, "synth-run-2", "R1", "--from-stage", "11")
        cls.reference = S.SyntheticRun(run_id="synth-run-2", drawing_date=DATE)    # the same correction, run from the start
        cls.reference.init()
        cls.reference_file = corrected_inputs(cls.reference.work, 7.5)
        cls.reference_code, cls.reference_answer = run_again(cls.reference, cls.reference_file, "synth-run-2", "R1")

    @classmethod
    def tearDownClass(cls):
        cls.first.cleanup()
        cls.reference.cleanup()

    def test_both_runs_finish(self):
        self.assertEqual((self.code, self.reference_code), (0, 0), (self.answer, self.reference_answer))

    def test_stages_before_11_are_reused_and_11_12_run(self):
        summary = self.answer["data"]["run"]["summary"]
        self.assertEqual(summary["reused"], list(range(1, 11)))
        self.assertEqual(summary["stages_run"], 12)
        self.assertTrue(summary["ok"])

    def test_the_resumed_project_holds_what_a_full_run_holds(self):
        for number in range(1, 12):
            with self.subTest(stage=number):
                self.assertEqual(outputs(self.first, number), outputs(self.reference, number))

    def test_the_correction_reached_the_stage_that_reads_it(self):
        text = json.dumps(outputs(self.first, 11))
        self.assertIn("7.5", text)

    def test_the_progress_file_says_which_stages_were_reused(self):
        lines = (self.first.project / ".epc" / "epc-progress.txt").read_text(encoding="utf-8").splitlines()
        reused = [ln for ln in lines if "run synth-run-2" in ln and "| reused |" in ln]
        self.assertEqual(len(reused), 10)

    def test_the_state_lists_all_twelve_stages(self):
        state = S.read_json(self.first.project / ".epc" / "master_project_state.json")
        self.assertEqual([e["number"] for e in state["stages"]], list(range(1, 13)))


class ResumeIsRefusedWhenUnsafe(unittest.TestCase):
    def test_a_project_that_never_ran_cannot_resume(self):
        run = S.SyntheticRun(drawing_date=DATE)
        self.addCleanup(run.cleanup)
        run.init()
        code, answer = run_again(run, run.engine_inputs_file, "r-x", "R0", "--from-stage", "5")
        self.assertEqual(code, 1)
        self.assertEqual(answer["error"]["code"], "cannot_resume")

    def test_from_stage_must_be_between_2_and_12(self):
        run = S.SyntheticRun(drawing_date=DATE).start()
        self.addCleanup(run.cleanup)
        open_correction(run)
        for bad in ("1", "13", "0"):
            with self.subTest(bad=bad):
                code, answer = run_again(run, run.engine_inputs_file, "r-" + bad, "R1", "--from-stage", bad)
                self.assertEqual((code, answer["error"]["code"]), (1, "cannot_resume"))

    def test_a_different_load_list_cannot_reuse_the_intake(self):
        run = S.SyntheticRun(drawing_date=DATE).start()
        self.addCleanup(run.cleanup)
        open_correction(run)
        loads = S.read_json(S.GOLDEN / "loads.json")
        loads["loads"] = loads["loads"][:-1]
        changed = run.work / "loads.changed.json"
        changed.write_text(json.dumps(loads), encoding="utf-8")
        code, answer = S.envelope(run.root, "run", S.CODE, "--loads", str(changed), "--engine-inputs", str(run.engine_inputs_file), "--run-id", "r-y",
                                  "--revision", "R1", "--from-stage", "5", *S.ORCHESTRATOR)
        self.assertEqual((code, answer["error"]["code"]), (1, "cannot_resume"))


if __name__ == "__main__":
    unittest.main()
