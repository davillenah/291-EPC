"""ADR-0035: the modes of a run. `production` (the default) is the strict behaviour of always; `edit` lets a package reach approve and issue with norm records that are not verified, and says so everywhere."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_pipeline_wiring as W  # noqa: E402
import test_platform_api as A  # noqa: E402
from disciplines.electrical_lv import resume as RS  # noqa: E402
from disciplines.electrical_lv.store import ProjectStore, StoreError  # noqa: E402
from epc_platform import api  # noqa: E402
from epc_platform.cli.main import main  # noqa: E402

ENG = A.ENG
TRAFO = {"demand_kva": 40, "reserve_pct": 20, "secondary_v": 400}


def loads():
    return json.loads(json.dumps(W.loads_doc()))


def inputs(**extra):
    return dict(W.inputs_doc(), transformer=dict(TRAFO), **extra)


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        api.init_project(self.root, "API-1", A.ANSWERS, clock=A.CLOCK, actor=A.ORC)
        self.project = self.root / "API-1"
        self.store = ProjectStore(self.project)

    def run_it(self, **kw):
        return api.run_pipeline(self.project, loads=loads(), engine_inputs=inputs(), clock=A.CLOCK, actor=A.ORC, **kw)

    def manifest(self):
        (m,) = [m for _, m in self.store.read_manifests() if m.get("superseded_by") is None]
        return m


class ProductionIsTheDefault(Base):
    def test_a_default_run_has_no_trace_of_the_modes(self):
        res = self.run_it()
        self.assertTrue(res["ok"], res)
        self.assertNotIn("mode", res["data"])
        self.assertNotIn("mode", self.manifest())
        self.assertFalse((self.project / ".epc" / "reviews" / "mode.json").exists())
        self.assertEqual(self.store.read_mode(), "production")
        self.assertNotIn("mode", json.loads((self.project / ".epc" / "runs" / res["data"]["pipeline_run_id"] / RS.FILE).read_text(encoding="utf-8")))

    def test_approve_stays_blocked_by_d21_in_production(self):
        self.run_it()
        self.assertTrue(api.submit(self.project, ENG, clock=A.CLOCK)["ok"])
        refused = api.approve(self.project, ENG, clock=A.CLOCK)
        self.assertEqual((refused["ok"], refused["error"]["code"]), (False, "blocked_d21"))

    def test_an_unknown_mode_is_an_invalid_argument(self):
        res = self.run_it(mode="sandbox")
        self.assertEqual((res["ok"], res["error"]["code"]), (False, "invalid_arguments"))


class EditMode(Base):
    def test_an_edit_run_marks_the_manifest_the_note_the_message_and_the_project(self):
        res = self.run_it(mode="edit")
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["data"]["mode"], "edit")
        self.assertEqual(self.manifest()["mode"], "edit")
        self.assertEqual(self.manifest()["review_status"], "draft")                  # nothing was approved or signed
        self.assertIsNone(self.manifest()["signed"])
        self.assertTrue([r for r in self.manifest()["normative_profile"]["norm_records"] if r["review_status"] != "verified"])          # the records stay as they were: the mode only changes how the run reacts
        self.assertEqual(self.store.read_mode(), "edit")
        stage12 = res["data"]["run"]["results"][11]
        self.assertIn("EDIT MODE", stage12["message"])
        self.assertEqual(api.status(self.project, clock=A.CLOCK, actor=A.ORC)["data"]["mode"], "edit")

    def test_the_norm_records_are_not_touched(self):
        edit = self.run_it(mode="edit")
        records = self.manifest()["normative_profile"]["norm_records"]
        self.assertTrue(edit["ok"] and records and any(r["review_status"] == "pending review" for r in records))

    def test_approve_and_issue_are_reachable_and_say_it_is_edit_mode(self):
        self.run_it(mode="edit")
        self.assertTrue(api.submit(self.project, ENG, clock=A.CLOCK)["ok"])
        approved = api.approve(self.project, ENG, clock=A.CLOCK)
        self.assertEqual((approved["ok"], approved["data"]["workflow_state"], approved["data"]["mode"]), (True, "approved", "edit"))
        self.assertIn("not for production", approved["data"]["notice"])
        issued = api.issue(self.project, ENG, clock=A.CLOCK)
        self.assertEqual((issued["ok"], issued["data"]["workflow_state"]), (True, "issued"))
        events = [json.loads(line) for line in (self.project / ".epc" / "audit" / "events.jsonl").read_text(encoding="utf-8").splitlines()] if (self.project / ".epc" / "audit" / "events.jsonl").exists() else []
        done = [e for e in events if e.get("action") == "transition:approve" and e.get("result") == "ok"]
        self.assertTrue(not events or done and done[-1]["detail"].get("d21") == "not applied (edit mode)")

    def test_a_package_of_production_in_a_project_in_edit_mode_keeps_the_guard(self):
        self.run_it()                                                                  # a production manifest
        with self.store.pipeline_session("seed") as token:
            self.store.write_mode(token, "edit")                                      # the project says edit, the manifest in force does not
        self.assertTrue(api.submit(self.project, ENG, clock=A.CLOCK)["ok"])
        refused = api.approve(self.project, ENG, clock=A.CLOCK)
        self.assertEqual((refused["ok"], refused["error"]["code"]), (False, "blocked_d21"))

    def test_a_production_run_does_not_take_over_a_revision_made_in_edit_mode(self):
        self.run_it(mode="edit")
        with self.store.pipeline_session("seed") as token:
            self.store.write_workflow(token, {"state": "corrected", "history": []})
        res = self.run_it()
        stage12 = res["data"]["run"]["results"][11] if res["ok"] else {}
        self.assertTrue(not res["ok"] or stage12.get("status") == "blocked", res)
        self.assertIn("edit mode", json.dumps(res))
        with self.store.pipeline_session("seed2") as token:
            self.store.write_workflow(token, {"state": "corrected", "history": []})
        again = self.run_it(revision="R1")
        self.assertTrue(again["ok"], again)
        self.assertNotIn("mode", self.manifest())


class Plumbing(unittest.TestCase):
    def test_the_marks_of_the_edit_mode_in_the_cover_and_the_reports(self):
        from disciplines.electrical_lv.stages import rendering
        rows = [{"name": "a", "code": None, "path": "a.dxf", "sha256": "0" * 64}]
        records = [{"review_status": "pending review"}]
        edit = rendering.transmittal_data("TR-001", "P", "R0", "run", rows, records, "edit")
        prod = rendering.transmittal_data("TR-001", "P", "R0", "run", rows, records)
        self.assertIn(["Mode", rendering.EDIT_MARK], edit["header"])
        self.assertIn(rendering.EDIT_MARK, edit["footer"] + edit["sections"][0][1])
        self.assertNotIn("EDIT MODE", json.dumps(prod))
        report = {"title": "t", "blocks": [], "footer": "f"}
        self.assertEqual(rendering.marked(copy.deepcopy(report), "production"), report)
        self.assertTrue(rendering.marked(report, "edit")["footer"].endswith(rendering.EDIT_MARK))

    def test_a_change_of_mode_resumes_from_the_documents_and_a_production_signature_is_unchanged(self):
        prod = RS.signatures({"a": 1}, {"l": 1}, {"x": 1})
        self.assertNotIn("mode", prod)
        self.assertEqual(RS.first_stage(prod, RS.signatures({"a": 1}, {"l": 1}, {"x": 1}, "edit")), 11)
        self.assertEqual(RS.first_stage(RS.signatures({"a": 1}, {"l": 1}, {"x": 1}, "edit"), RS.signatures({"a": 1}, {"l": 1}, {"x": 1}, "edit")), 12)

    def test_the_store_keeps_the_mode_apart_from_the_reviews(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api.init_project(root, "API-1", A.ANSWERS, clock=A.CLOCK, actor=A.ORC)
            store = ProjectStore(root / "API-1")
            with store.pipeline_session("t") as token:
                with self.assertRaises(StoreError):
                    store.write_mode(token, "sandbox")
                with self.assertRaises(StoreError):
                    store.write_review(token, "mode.json", {})
                store.write_mode(token, "edit")
            self.assertEqual(store.read_mode(), "edit")
            self.assertNotIn("mode.json", store.list_reviews())

    def test_the_cli_takes_the_mode(self):
        import io
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api.init_project(root, "API-1", A.ANSWERS, clock=A.CLOCK, actor=A.ORC)
            (root / "loads.json").write_text(json.dumps(loads()), encoding="utf-8")
            (root / "inputs.json").write_text(json.dumps(inputs()), encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            env = {"EPC_ACTOR_ROLE": "orchestrator", "EPC_ACTOR_ID": "o1"}
            code = main(["--projects-root", str(root), "run", "API-1", "--loads", str(root / "loads.json"), "--engine-inputs", str(root / "inputs.json"), "--mode", "edit", "--json"], stdout=out, stderr=err, env=env)
            data = json.loads(out.getvalue() or err.getvalue())
        self.assertEqual((code, data.get("ok"), (data.get("data") or {}).get("mode")), (0, True, "edit"))


if __name__ == "__main__":
    unittest.main()
