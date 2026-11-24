"""MIG-33b: the MCP server exposes the pipeline and the read-only engine queries, and equals the direct calls (PRD 14.5 parity).

The tools are called through the server's own dispatch function (`epc_mcp.protocol.handle`, in process, no subprocess). The reference is
`pipeline.run` called directly on a second project with the same run id and clock. Needs the engine packages and `harness/src/platform/mcp/src`
on PYTHONPATH (the gate's `harness-tests` environment has them).
"""
import json
import tempfile
import unittest
from pathlib import Path

import test_pipeline_discipline as D
import test_pipeline_wiring as W
import test_ssot_wired_pipeline as S

from disciplines.electrical_lv import pipeline
from disciplines.electrical_lv.intake.profile import build_profile
from disciplines.electrical_lv.stages import PipelineContext
from disciplines.electrical_lv.stages.table import WIRED_STAGES
from disciplines.electrical_lv.store import ProjectStore
from epc_mcp.protocol import handle
from epc_mcp.registry import Context
from epc_mcp.tools import build_registry
from epc_platform import api
from epc_platform.events import EventLog
from epc_platform.permissions import check

CLOCK = lambda: "2026-01-01T00:00:00Z"  # noqa: E731
ORC = {"role": "orchestrator", "id": "o1"}
NEW_TOOLS = ["epc_engine_info", "epc_engine_list", "epc_engine_schema", "epc_norm_records", "epc_norms_pending", "epc_pipeline_run", "epc_project_approve", "epc_project_init", "epc_project_issue",
             "epc_project_review", "epc_project_status", "epc_project_submit", "epc_stage_table"]
WRITE_TOOLS = ["epc_pipeline_run", "epc_project_approve", "epc_project_init", "epc_project_issue", "epc_project_review", "epc_project_submit"]
ANSWERS = dict(S.ANSWERS, project_code="PARITY-1")
REGISTRY = build_registry()


def without_dxf_hashes(run):
    """The run as a dict without the DXF stamps: the drawing engine writes the current time into the files, so their size and hash differ."""
    out = W.without_dxf_stamp(run)
    if len(out["results"]) == 12:
        outputs = out["results"][11]["outputs"]
        for item in [f for m in outputs["manifests"] for f in m["manifest"]["files"]] + outputs["transmittal"]["files"]:
            if (item["path"] or "").endswith(".dxf"):
                item["sha256"] = None
    return out


def server(root, actor=ORC, profile="full"):
    """A callable that sends one tools/call message through the server dispatch and returns the decoded envelope."""
    ctx = Context(Path(root), profile, clock=CLOCK, actor=actor)
    counter = iter(range(1, 10_000))

    def call(tool, /, **arguments):
        message = {"jsonrpc": "2.0", "id": next(counter), "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
        answer = handle(message, REGISTRY, ctx)
        return json.loads(answer["result"]["content"][0]["text"])

    call.ctx = ctx
    return call


def listed(root, profile="full"):
    ctx = Context(Path(root), profile)
    return handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, REGISTRY, ctx)["result"]["tools"]


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.call = server(self.root)

    def init(self, code="PARITY-1", call=None):
        return (call or self.call)("epc_project_init", project=code, answers=ANSWERS)

    def events(self, code="PARITY-1"):
        return EventLog.for_project(self.root / code, CLOCK).read()


class ToolListTests(Base):
    def test_the_new_tools_are_listed_with_json_schemas(self):
        tools = {t["name"]: t for t in listed(self.root)}
        for name in NEW_TOOLS:
            with self.subTest(tool=name):
                self.assertIn(name, tools)
                schema = tools[name]["inputSchema"]
                self.assertEqual(schema["type"], "object")
                self.assertTrue(set(schema["required"]) <= set(schema["properties"]), name)
                self.assertTrue(tools[name]["description"])
        self.assertEqual(json.loads(json.dumps(list(tools.values()))), list(tools.values()))

    def test_the_server_lists_only_epc_tools_that_call_the_platform_api(self):
        names = {t["name"] for t in listed(self.root)}
        self.assertEqual(names, set(NEW_TOOLS))

    def test_the_write_tools_are_refused_when_the_write_gate_is_off(self):
        readonly = {t["name"] for t in listed(self.root, "readonly")}
        self.assertTrue(readonly.isdisjoint(WRITE_TOOLS))
        self.assertTrue({"epc_stage_table", "epc_engine_list", "epc_engine_info", "epc_norm_records", "epc_project_status"} <= readonly)
        call = server(self.root, profile="readonly")
        for name in WRITE_TOOLS:
            with self.subTest(tool=name):
                answer = call(name, project="PARITY-1", answers=ANSWERS, corrections=[{"a": 1}])
                self.assertEqual((answer["ok"], answer["error"]["code"]), (False, "unknown_tool"))
        self.assertFalse((self.root / "PARITY-1").exists())


class EngineQueryTests(Base):
    def test_the_engine_list_has_the_24_engines(self):
        answer = self.call("epc_engine_list")
        engines = answer["data"]["engines"]
        self.assertEqual((answer["ok"], answer["data"]["count"], len(engines)), (True, 34, 34))
        self.assertEqual({e["package"] for e in engines}, {f"epc_{a}" for a in (
            "aea90364", "calc_common", "load_balance", "voltage_drop", "feeder_sizing", "short_circuit", "grounding", "selectivity", "transformer_sizing", "hvac", "pv", "lighting", "receptacles", "arch", "drawing", "dxf", "mld", "plan", "sld", "symbols", "titleblock",
            "documents", "terminal_blocks", "design_basis", "descriptive_report", "boq", "datasheets", "rfq", "cutlist", "walls", "dims", "rules", "standards", "calc_check")})
        versions = {e["package"]: e["version"] for e in engines}
        self.assertEqual((versions["epc_aea90364"], versions["epc_hvac"], versions["epc_rules"]), ("1.6.0", "0.1.0", "0.1.0"))
        self.assertEqual(answer, json.loads(json.dumps(api.list_engines())))

    def test_engine_schema_gives_the_published_contract(self):
        data = self.call("epc_engine_schema", name="cutlist")["data"]
        self.assertEqual((data["package"], data["count"], sorted(data["schemas"])), ("epc_cutlist", 1, ["input.schema.json"]))
        self.assertEqual(self.call("epc_engine_schema", name="epc_cutlist")["data"], data)
        self.assertEqual(self.call("epc_engine_schema", name="nope")["error"]["code"], "unknown_engine")

    def test_an_engine_without_schema_says_so(self):
        answer = self.call("epc_engine_schema", name="rules")
        self.assertEqual((answer["ok"], answer["data"]["count"]), (True, 0))
        self.assertTrue(answer["warnings"])

    def test_engine_info_names_the_version_and_the_public_modules(self):
        info = self.call("epc_engine_info", name="aea90364")["data"]
        self.assertEqual((info["package"], info["group"], info["area"]), ("epc_aea90364", "calculation", "aea90364"))
        self.assertIn("aea_pipeline", info["public_modules"])
        self.assertEqual(self.call("epc_engine_info", name="epc_aea90364")["data"], info)
        self.assertEqual(self.call("epc_engine_info", name="nope")["error"]["code"], "unknown_engine")

    def test_norm_records_equal_the_read_only_reader_and_have_no_review_change(self):
        from disciplines.electrical_lv.norm_records import read_norm_records
        answer = self.call("epc_norm_records", package="epc_aea90364")["data"]
        self.assertEqual(answer["records"], read_norm_records(["epc_aea90364"]))
        self.assertEqual(answer["count"], sum(answer["by_status"].values()))
        self.assertGreater(answer["count"], 0)

    def test_norms_pending_equal_the_read_only_review_units(self):
        from disciplines.electrical_lv import norm_review
        data = self.call("epc_norms_pending")["data"]
        expected = norm_review.summary()
        self.assertEqual((data["units"], data["units_with_pending"], data["pending_points"]),
                         (expected["units"], expected["units_with_pending"], expected["pending_points"]))
        detail = self.call("epc_norms_pending", detail=True)["data"]["rows"]
        self.assertEqual(sum(r["pending"] for r in detail), data["pending_points"])
        self.assertTrue(all(r["pending"] for r in detail))

    def test_the_stage_table_has_12_rows_matching_the_prd(self):
        data = self.call("epc_stage_table")["data"]
        rows = D.prd_rows()
        self.assertEqual((data["count"], len(data["stages"]), len(rows)), (12, 12, 12))
        for row, (number, title, engines, status) in zip(data["stages"], rows):
            with self.subTest(stage=number):
                self.assertEqual((row["number"], row["title"], row["engines"], row["status"]), (int(number), title, engines, status))
        self.assertEqual([r["number"] for r in data["stages"] if r["wired"]], list(WIRED_STAGES))

    def test_a_query_names_no_value_that_an_engine_did_not_give(self):
        text = json.dumps(self.call("epc_stage_table"))
        self.assertNotIn("traceback", text.lower())


class ParityTests(Base):
    """`epc_pipeline_run` equals `pipeline.run` called directly with the same run id and clock."""

    @classmethod
    def direct(cls, stop_after):
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "PARITY-1")
            store.init_with_answers(ANSWERS)
            ctx = PipelineContext(profile=build_profile(ANSWERS), loads=W.loads_doc(), engine_inputs=W.inputs_doc(), store=store)
            result = pipeline.run(ctx, stop_after=stop_after, run_id="r-parity", clock=CLOCK).to_dict()
            return without_dxf_hashes(result), store.read_state()["stages"]

    def run_tool(self, stop_after):
        self.assertTrue(self.init()["ok"])
        return self.call("epc_pipeline_run", project="PARITY-1", loads=W.loads_doc(), engine_inputs=W.inputs_doc(), stop_after=stop_after,
                         run_id="r-parity", detail=True)

    def test_the_tool_result_equals_the_direct_pipeline_run(self):
        answer = self.run_tool(11)
        self.assertTrue(answer["ok"], answer)
        expected, _ = self.direct(11)
        self.assertEqual(without_dxf_hashes(answer["data"]["run"]), expected)
        self.assertEqual(answer["data"]["pipeline_run_id"], "r-parity")
        self.assertEqual(answer["data"]["workflow_state"], "running")

    def test_the_full_12_stage_run_equals_the_direct_run_and_ends_in_draft_ready(self):
        answer = self.run_tool(None)
        self.assertTrue(answer["ok"], answer)
        expected, _ = self.direct(None)
        self.assertEqual(without_dxf_hashes(answer["data"]["run"]), expected)
        self.assertEqual(answer["data"]["workflow_state"], "draft_ready")
        self.assertEqual(answer["data"]["run"]["summary"]["stages_run"], 12)

    def test_the_numbers_in_the_result_come_from_the_engines(self):
        answer = self.run_tool(6)
        datos, _detail, _warnings = W.direct_call()
        rows = {r["circuit"]: r for r in answer["data"]["run"]["results"][5]["outputs"]["feeder_sizing"]["circuits"]}
        self.assertEqual({t: r["in_a"] for t, r in rows.items()}, {t: d["In"] for t, d in datos.items()})
        self.assertIn("epc_aea90364.aea_pipeline.calculate", [c["function"] for c in answer["data"]["run"]["results"][5]["engine_calls"]])

    def test_the_brief_result_has_no_stage_outputs(self):
        self.init()
        answer = self.call("epc_pipeline_run", project="PARITY-1", loads=W.loads_doc(), engine_inputs=W.inputs_doc(), stop_after=5, run_id="r-b")
        rows = answer["data"]["run"]["results"]
        self.assertEqual([r["stage"] for r in rows], [1, 2, 3, 4, 5])
        self.assertTrue(all("outputs" not in r for r in rows))

    def test_the_status_tool_equals_the_api_status(self):
        self.run_tool(11)
        via_tool = self.call("epc_project_status", project="PARITY-1")
        direct = api.status(self.root / "PARITY-1", clock=CLOCK, actor=ORC)
        self.assertTrue(via_tool["ok"] and direct["ok"])
        # each status call appends its own `allowed` event, so only the audit block differs (by exactly that event)
        self.assertEqual({k: v for k, v in via_tool["data"].items() if k != "audit"}, {k: v for k, v in direct["data"].items() if k != "audit"})
        self.assertEqual(direct["data"]["audit"]["count"], via_tool["data"]["audit"]["count"] + 1)
        self.assertTrue(direct["data"]["audit"]["chain_intact"])
        self.assertEqual(direct["data"]["state"], ProjectStore(self.root / "PARITY-1").read_state())
        self.assertEqual(direct["data"]["workflow"]["state"], "running")

    def test_the_run_writes_only_through_the_store(self):
        self.run_tool(5)
        root = self.root / "PARITY-1"
        store = ProjectStore(root)
        self.assertTrue(store.is_frozen())
        self.assertEqual(len(store.read_progress().splitlines()), 2 + 5)
        self.assertEqual(sorted(p.name for p in (root / ".epc" / "ssot").glob("stage_*.json"))[:2], ["stage_01_intake.json", "stage_02_requirements_inputs.json"])
        self.assertEqual(EventLog.for_project(root, CLOCK).verify(), [])


class PermissionTests(Base):
    def test_a_denied_run_returns_an_error_envelope_and_logs_a_denied_event(self):
        self.init()
        call = server(self.root, {"role": "electrical_lv", "id": "agent-1"})
        answer = call("epc_pipeline_run", project="PARITY-1", loads=W.loads_doc(), engine_inputs=W.inputs_doc(), stop_after=3)
        self.assertEqual((answer["ok"], answer["error"]["code"]), (False, "permission_denied"))
        denied = [e for e in self.events() if e["result"] == "denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual((denied[0]["actor"], denied[0]["action"]), ({"role": "electrical_lv", "id": "agent-1"}, "run:start"))
        self.assertFalse(list((self.root / "PARITY-1" / ".epc" / "ssot").glob("*.json")))
        self.assertEqual(EventLog.for_project(self.root / "PARITY-1", CLOCK).verify(), [])

    def test_agents_cannot_reach_ssot_or_deliverables(self):
        for role in ("orchestrator", "electrical_lv", "calc_check", "documentation", "procurement"):
            for path_class in ("ssot", "deliverables"):
                with self.subTest(role=role, path=path_class):
                    self.assertFalse(check(role, "write", path_class).allowed)
                    self.assertFalse(check(role, "create", path_class).allowed)

    def test_every_project_tool_denies_an_unknown_role_and_logs_it(self):
        self.init()
        call = server(self.root, {"role": "stranger", "id": "x"})
        for name, args in (("epc_project_status", {}), ("epc_project_review", {"corrections": [{"note": "n"}]}), ("epc_project_approve", {}),
                          ("epc_project_issue", {})):
            with self.subTest(tool=name):
                answer = call(name, project="PARITY-1", **args)
                self.assertEqual((answer["ok"], answer["error"]["code"]), (False, "permission_denied"))
        self.assertGreaterEqual(len([e for e in self.events() if e["result"] == "denied"]), 4)

    def test_init_by_a_role_that_cannot_create_inputs_leaves_nothing_behind(self):
        call = server(self.root, {"role": "calc_check", "id": "c1"})
        answer = self.init(call=call)
        self.assertEqual((answer["ok"], answer["error"]["code"]), (False, "permission_denied"))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_a_query_by_an_unknown_role_is_denied(self):
        answer = server(self.root, {"role": "stranger", "id": "x"})("epc_engine_list")
        self.assertEqual((answer["ok"], answer["error"]["code"]), (False, "permission_denied"))


class ProjectFlowTests(Base):
    def test_init_checks_the_answers_and_refuses_an_existing_project(self):
        bad = {k: v for k, v in ANSWERS.items() if k != "supply"}
        self.assertEqual(self.call("epc_project_init", project="PARITY-1", answers=bad)["error"]["code"], "invalid_answers")
        self.assertFalse((self.root / "PARITY-1").exists())
        self.assertTrue(self.init()["ok"])
        self.assertEqual(self.init()["error"]["code"], "project_exists")
        self.assertEqual(self.call("epc_project_init", project="../x", answers=ANSWERS)["error"]["code"], "invalid_project")
        self.assertEqual(self.call("epc_project_status", project="NOPE")["error"]["code"], "project_not_found")

    def test_review_records_the_corrections_through_the_workflow_and_never_edits_ssot(self):
        self.init()
        self.call("epc_pipeline_run", project="PARITY-1", loads=W.loads_doc(), engine_inputs=W.inputs_doc(), run_id="r-1")
        ssot = {p.name: p.read_bytes() for p in (self.root / "PARITY-1" / ".epc" / "ssot").glob("*.json")}
        engineer = server(self.root, {"role": "engineer_of_record", "id": "e1"})
        answer = engineer("epc_project_review", project="PARITY-1", corrections=[{"target": "stage_06", "note": "check the cable"}])
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(answer["data"]["workflow_state"], "corrected")
        review = json.loads((self.root / "PARITY-1" / answer["data"]["review_file"]).read_text(encoding="utf-8"))
        self.assertEqual(review["corrections"], [{"target": "stage_06", "note": "check the cable"}])
        self.assertEqual({p.name: p.read_bytes() for p in (self.root / "PARITY-1" / ".epc" / "ssot").glob("*.json")}, ssot)
        self.assertEqual(engineer("epc_project_review", project="PARITY-1", corrections=[])["error"]["code"], "invalid_arguments")

    def test_issue_is_refused_until_the_project_is_approved_and_by_d21_afterwards(self):
        self.init()
        self.assertEqual(self.call("epc_project_issue", project="PARITY-1")["error"]["code"], "bad_state")
        store = ProjectStore(self.root / "PARITY-1")
        with store.pipeline_session("seed") as token:
            store.write_workflow(token, {"state": "approved", "history": []})
        engineer = server(self.root, {"role": "engineer_of_record", "id": "e1"})
        self.assertEqual(engineer("epc_project_issue", project="PARITY-1")["error"]["code"], "blocked_d21")
        self.assertEqual(store.read_workflow()["state"], "approved")

    def test_approve_needs_the_engineer_and_is_blocked_by_d21(self):
        self.init()
        store = ProjectStore(self.root / "PARITY-1")
        with store.pipeline_session("seed") as token:
            store.write_workflow(token, {"state": "in_review", "history": []})
        self.assertEqual(self.call("epc_project_approve", project="PARITY-1")["error"]["code"], "permission_denied")
        engineer = server(self.root, {"role": "engineer_of_record", "id": "e1"})
        self.assertEqual(engineer("epc_project_approve", project="PARITY-1")["error"]["code"], "blocked_d21")
        self.assertEqual(store.read_workflow()["state"], "in_review")


if __name__ == "__main__":
    unittest.main()
