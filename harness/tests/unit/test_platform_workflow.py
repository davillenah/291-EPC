"""MIG-33a: the project workflow, its role guards, the D21 block and the store method behind `reviews/workflow.json`."""
import json
import tempfile
import unittest
from pathlib import Path

import test_manifest as TM

from disciplines.electrical_lv.store import ProjectStore, StoreError, workflow_problems
from epc_platform.events import EventLog
from epc_platform.permissions import PermissionDenied
from epc_platform.workflow import STATES, TRANSITIONS, Workflow, WorkflowBlocked, WorkflowError

ENG, ORC, REV, CC = "engineer_of_record", "orchestrator", "reviewing_engineer", "calc_check"
CLOCK = lambda: "2026-01-01T00:00:00Z"  # noqa: E731
HAPPY = [("complete_intake", ORC), ("start_run", ORC), ("finish_run", ORC), ("submit_for_review", ORC)]


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = Path(self._tmp.name) / "P1"
        self.project.mkdir()
        self.log = EventLog.for_project(self.project, CLOCK)
        self.wf = Workflow(self.project, self.log)

    def go(self, steps):
        for name, role in steps:
            self.wf.transition(name, role, "u1", "r1")

    def put_manifest(self, reader):
        store = ProjectStore(self.project)
        with store.pipeline_session("seed") as token:
            store.write_manifest(token, TM.build(norm_reader=reader))


class TransitionTests(Base):
    def test_the_table_covers_the_lifecycle(self):
        self.assertEqual(STATES[0], "init")
        self.assertEqual(STATES[-1], "issued")
        for src, dst in TRANSITIONS.values():
            self.assertIn(src, STATES)
            self.assertIn(dst, STATES)
        self.assertEqual({s for s in STATES if s not in {d for _, d in TRANSITIONS.values()}}, {"init"})

    def test_the_happy_path_to_approval_and_issue(self):
        self.put_manifest(TM.ALL_VERIFIED)
        self.go(HAPPY)
        self.assertEqual(self.wf.state, "in_review")
        self.go([("approve", ENG), ("issue", ENG)])
        self.assertEqual(self.wf.state, "issued")
        self.assertEqual([h["transition"] for h in self.wf.history()], [n for n, _ in HAPPY] + ["approve", "issue"])
        self.assertEqual(self.log.verify(), [])

    def test_corrections_lead_to_a_rerun_and_a_new_review(self):
        self.go(HAPPY + [("record_corrections", REV), ("rerun", ENG)])
        self.assertEqual(self.wf.state, "running")
        self.assertEqual(self.wf.allowed_transitions(), ["finish_run"])

    def test_a_corrected_draft_cannot_be_approved_without_a_rerun(self):
        self.put_manifest(TM.ALL_VERIFIED)
        self.go(HAPPY + [("record_corrections", REV)])
        with self.assertRaises(WorkflowError):
            self.wf.transition("approve", ENG, "u1")

    def test_a_wrong_state_or_unknown_name_is_refused_and_logged(self):
        for name in ("start_run", "issue", "nonsense"):
            with self.assertRaises(WorkflowError):
                self.wf.transition(name, ORC, "u1")
        self.assertEqual(self.wf.state, "init")
        self.assertEqual([r["result"] for r in self.log.read()], ["denied"] * 3)

    def test_the_state_file_is_small_deterministic_json_under_reviews(self):
        self.go(HAPPY[:1])
        path = self.project / "reviews" / "workflow.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["state"], "intake_done")
        self.assertEqual(data["history"][0]["role"], ORC)
        self.assertFalse(list((self.project / "reviews").glob(".*.tmp")))
        self.assertFalse((self.project / "master_project_state.json").exists())


class RoleGuardTests(Base):
    def test_a_role_that_may_not_trigger_is_refused_and_logged_once(self):
        with self.assertRaises(PermissionDenied):
            self.wf.transition("complete_intake", CC, "c1")
        self.assertEqual(self.wf.state, "init")
        recs = self.log.read()
        self.assertEqual([r["result"] for r in recs], ["denied"])

    def test_only_the_engineer_approves(self):
        self.put_manifest(TM.ALL_VERIFIED)
        self.go(HAPPY)
        for role in (ORC, REV, CC, "electrical_lv"):
            with self.subTest(role=role):
                with self.assertRaises(PermissionDenied):
                    self.wf.transition("approve", role, "x")
        self.assertEqual(self.wf.state, "in_review")
        self.wf.transition("approve", ENG, "e1")
        self.assertEqual(self.wf.state, "approved")

    def test_issue_by_the_orchestrator_is_allowed_and_by_a_checker_is_not(self):
        self.put_manifest(TM.ALL_VERIFIED)
        self.go(HAPPY + [("approve", ENG)])
        with self.assertRaises(PermissionDenied):
            self.wf.transition("issue", CC, "c")
        self.wf.transition("issue", ORC, "o")
        self.assertEqual(self.wf.state, "issued")

    def test_the_allowed_decision_of_a_guarded_transition_is_logged(self):
        self.put_manifest(TM.ALL_VERIFIED)
        self.go(HAPPY + [("approve", ENG)])
        results = [(r["action"], r["result"]) for r in self.log.read() if r["action"].startswith(("sign", "transition:approve"))]
        self.assertEqual(results, [("sign:deliverables", "allowed"), ("transition:approve", "ok")])


class D21Tests(Base):
    def test_approval_is_blocked_by_an_unreviewed_record(self):
        self.put_manifest(TM.ONE_PENDING)
        self.go(HAPPY)
        with self.assertRaises(WorkflowBlocked) as cm:
            self.wf.transition("approve", ENG, "e1")
        self.assertIn("x.2", str(cm.exception))
        self.assertEqual(self.wf.state, "in_review")
        self.assertEqual(self.log.read()[-1]["result"], "denied")

    def test_issue_is_blocked_too_if_a_new_manifest_has_an_unreviewed_record(self):
        self.put_manifest(TM.ALL_VERIFIED)
        self.go(HAPPY + [("approve", ENG)])
        store = ProjectStore(self.project)
        with store.pipeline_session("seed2") as token:
            store.write_manifest(token, TM.build(deliverable_id="TEST-001-DOC-MC", norm_reader=TM.ONE_PENDING))
        with self.assertRaises(WorkflowBlocked):
            self.wf.transition("issue", ENG, "e1")
        self.assertEqual(self.wf.state, "approved")

    def test_a_superseded_manifest_does_not_count(self):
        old = TM.build(norm_reader=TM.ONE_PENDING)
        new = TM.build(revision="R1", norm_reader=TM.ALL_VERIFIED)
        old2, new2 = TM.M.supersede(old, new)
        store = ProjectStore(self.project)
        with store.pipeline_session("seed") as token:
            store.write_manifest(token, old)
            store.write_manifest(token, new2)
            store.update_manifest(token, old2)
        self.go(HAPPY)
        self.wf.transition("approve", ENG, "e1")
        self.assertEqual(self.wf.state, "approved")

    def test_no_manifest_blocks_approval(self):
        self.go(HAPPY)
        with self.assertRaises(WorkflowBlocked):
            self.wf.transition("approve", ENG, "e1")


class StoreMethodTests(Base):
    def test_write_needs_the_token_and_a_valid_record(self):
        store = ProjectStore(self.project)
        good = {"state": "init", "history": []}
        with self.assertRaises(PermissionError):
            store.write_workflow(None, good)
        with store.pipeline_session("w1") as token:
            for bad in ({"state": "flying", "history": []}, {"state": "init"}, {"state": "init", "history": [{"from": "init"}]},
                        {"state": "init", "history": "x"}, [], {"state": "init", "history": [], "extra": 1}):
                with self.subTest(bad=bad):
                    with self.assertRaises(StoreError):
                        store.write_workflow(token, bad)
            store.write_workflow(token, good)
        self.assertEqual(store.read_workflow(), good)
        with self.assertRaises(PermissionError):
            store.write_workflow(token, good)

    def test_read_without_a_file_is_none(self):
        self.assertIsNone(ProjectStore(self.project).read_workflow())
        self.assertEqual(workflow_problems({"state": "init", "history": []}), [])


if __name__ == "__main__":
    unittest.main()
