"""MIG-33b: the platform API functions themselves (no MCP): envelopes, the RACI gate, the audit log and the store methods they rely on."""
import json
import tempfile
import unittest
from pathlib import Path

import test_ssot_wired_pipeline as S

from disciplines.electrical_lv.store import ProjectStore, StoreError
from epc_platform import api
from epc_platform.events import EventLog
from epc_platform.workflow import Workflow

CLOCK = lambda: "2026-01-01T00:00:00Z"  # noqa: E731
ORC = {"role": "orchestrator", "id": "o1"}
ENG = {"role": "engineer_of_record", "id": "e1"}
REV = {"role": "reviewing_engineer", "id": "r1"}
ANSWERS = dict(S.ANSWERS, project_code="API-1")


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def init(self, code="API-1", actor=ORC):
        return api.init_project(self.root, code, ANSWERS, clock=CLOCK, actor=actor)

    def log(self, code="API-1"):
        return EventLog.for_project(self.root / code, CLOCK)


class EnvelopeTests(Base):
    def test_every_function_returns_an_envelope_and_never_raises(self):
        self.assertEqual(sorted(api.ok(1)), ["data", "ok", "warnings"])
        self.assertEqual(api.fail("x", "m"), {"ok": False, "error": {"code": "x", "message": "m"}})
        results = [api.status(self.root / "nope", clock=CLOCK, actor=ORC), api.status(self.root, clock=None, actor=ORC),
                   api.run_pipeline(self.root, clock=CLOCK, actor="nobody"), api.review(self.root, ORC, [], clock=CLOCK),
                   api.issue(self.root, ORC, clock=CLOCK), api.engine_info(None), api.norm_records("epc_nope")]
        for result in results:
            self.assertFalse(result["ok"])
            self.assertIn("code", result["error"])

    def test_results_are_plain_json(self):
        self.init()
        for result in (api.status(self.root / "API-1", clock=CLOCK, actor=ORC), api.stage_table(), api.list_engines(), api.engine_info("sld")):
            self.assertEqual(json.loads(json.dumps(result)), result)


class InitTests(Base):
    def test_init_creates_the_project_with_the_answers_as_an_input_and_logs_it(self):
        result = self.init()
        self.assertEqual((result["ok"], result["data"]["workflow_state"]), (True, "init"))
        store = ProjectStore(self.root / "API-1")
        self.assertEqual(store.read_answers(), ANSWERS)
        self.assertEqual([(e["action"], e["result"]) for e in self.log().read()], [("create:inputs", "allowed"), ("init", "ok")])
        self.assertEqual(self.log().verify(), [])

    def test_the_answers_project_code_must_agree(self):
        result = api.init_project(self.root, "OTHER", ANSWERS, clock=CLOCK, actor=ORC)
        self.assertEqual(result["error"]["code"], "invalid_answers")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_d24_data_is_required(self):
        result = api.init_project(self.root, "API-2", {"client": {"name": "x"}}, clock=CLOCK, actor=ORC)
        self.assertEqual(result["error"]["code"], "invalid_answers")
        self.assertTrue(any("D24" in e for e in result["error"]["details"]["errors"]))


class ReviewTests(Base):
    def at_draft_ready(self):
        self.init()
        wf = Workflow(self.root / "API-1", self.log())
        for name in ("complete_intake", "start_run", "finish_run"):
            wf.transition(name, "orchestrator", "o1", "r1")

    def test_review_submits_a_draft_and_stores_the_corrections_below_reviews(self):
        self.at_draft_ready()
        result = api.review(self.root / "API-1", ENG, [{"note": "n"}], clock=CLOCK)
        self.assertTrue(result["ok"], result)
        self.assertEqual(ProjectStore(self.root / "API-1").list_reviews(), ["record_corrections-5.json"])
        self.assertEqual(result["data"]["review_file"], ".epc/reviews/record_corrections-5.json")
        history = [h["transition"] for h in Workflow(self.root / "API-1", self.log()).history()]
        self.assertEqual(history[-2:], ["submit_for_review", "record_corrections"])

    def test_a_reviewer_cannot_submit_a_draft_but_can_record_after_the_engineer_submitted(self):
        self.at_draft_ready()
        self.assertEqual(api.review(self.root / "API-1", REV, [{"note": "n"}], clock=CLOCK)["error"]["code"], "permission_denied")
        Workflow(self.root / "API-1", self.log()).transition("submit_for_review", "engineer_of_record", "e1", "r2")
        self.assertTrue(api.review(self.root / "API-1", REV, [{"note": "n"}], clock=CLOCK)["ok"])
        self.assertTrue(any(e["result"] == "denied" for e in self.log().read()))

    def test_the_store_refuses_a_review_file_outside_reviews_or_the_workflow_record(self):
        self.init()
        store = ProjectStore(self.root / "API-1")
        with store.pipeline_session("seed") as token:
            for name in ("workflow.json", "x.txt", "../ssot/x.json", "a/../../x.json"):
                with self.subTest(name=name), self.assertRaises(StoreError):
                    store.write_review(token, name, {})
            store.write_review(token, "ok.json", {"a": 1})
        self.assertEqual(store.list_reviews(), ["ok.json"])
        with self.assertRaises(PermissionError):
            store.write_review(token, "late.json", {})


class QueryTests(Base):
    def test_a_query_with_a_project_is_audited_there(self):
        self.init()
        result = api.list_engines(actor=ORC, project_dir=self.root / "API-1", clock=CLOCK)
        self.assertTrue(result["ok"])
        self.assertEqual(self.log().read()[-1]["action"], "read:harness_code")

    def test_unknown_engine_and_norm_records_of_every_engine(self):
        self.assertEqual(api.engine_info("zzz")["error"]["code"], "unknown_engine")
        everything = api.norm_records()["data"]
        self.assertEqual(len(everything["packages"]), 40)
        self.assertTrue(all(r["review_status"] in ("verified", "pending review", "rejected") for r in everything["records"]))


if __name__ == "__main__":
    unittest.main()


class SubmitTests(Base):
    """PRB-03: `submit` puts a finished run in review, so `approve` can be reached (the D21 guard still decides)."""

    def at(self, state):
        self.init()
        store = ProjectStore(self.root / "API-1")
        with store.pipeline_session("test") as token:
            store.write_workflow(token, {"state": state, "history": []})
        return store

    def test_a_finished_run_goes_to_review_and_then_approve_is_reachable(self):
        store = self.at("draft_ready")
        res = api.submit(self.root / "API-1", ENG, clock=CLOCK)
        self.assertEqual((res["ok"], res["data"]["workflow_state"]), (True, "in_review"))
        self.assertEqual(store.read_workflow()["state"], "in_review")
        refused = api.approve(self.root / "API-1", ENG, clock=CLOCK)
        self.assertEqual((refused["ok"], refused["error"]["code"]), (False, "blocked_d21"))          # reachable; the unreviewed norm values still block it
        self.assertEqual(store.read_workflow()["state"], "in_review")

    def test_only_a_draft_ready_project_can_be_submitted_and_a_stranger_cannot(self):
        self.at("running")
        self.assertFalse(api.submit(self.root / "API-1", ENG, clock=CLOCK)["ok"])
        self.at("draft_ready")
        denied = api.submit(self.root / "API-1", {"role": "stranger", "id": "x"}, clock=CLOCK)
        self.assertEqual((denied["ok"], denied["error"]["code"]), (False, "permission_denied"))
