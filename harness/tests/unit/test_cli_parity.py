"""MIG-33c: the `epc` CLI, the MCP server and the direct `epc_platform.api` calls give the same answers (PRD 14.5 parity).

The CLI is called in process through `main(argv)`; the MCP server through its dispatch function; the reference is `api.run_pipeline` on a
third project with the same run id and clock. The DXF size/hash are masked as in test_mcp_parity.
"""
import io
import json
import tempfile
import unittest
from pathlib import Path

import test_mcp_parity as M
import test_pipeline_discipline as D
import test_pipeline_wiring as W

from epc_platform import api
from epc_platform.cli import commands
from epc_platform.cli.main import main

CLOCK = M.CLOCK
ORC = M.ORC
CODE = "PARITY-1"
# CLI subcommand -> api function it calls
CLI_TO_API = {"init": "init_project", "run": "run_pipeline", "status": "status", "review": "review", "submit": "submit", "approve": "approve", "issue": "issue",
              "engines list": "list_engines", "engines info": "engine_info", "engines schema": "engine_schema", "norms": "norm_records", "norms-pending": "norms_pending",
              "stages": "stage_table"}
# MCP tool -> api function it calls (every tool of the server; the older tools that read the parked web backend were archived in MIG-38b)
MCP_TO_API = {"epc_project_init": "init_project", "epc_pipeline_run": "run_pipeline", "epc_project_status": "status", "epc_project_review": "review", "epc_project_submit": "submit",
              "epc_project_approve": "approve", "epc_project_issue": "issue", "epc_engine_list": "list_engines", "epc_engine_info": "engine_info", "epc_engine_schema": "engine_schema",
              "epc_norm_records": "norm_records", "epc_norms_pending": "norms_pending", "epc_stage_table": "stage_table"}
MCP_ONLY = set()          # every MCP tool calls an api function since MIG-38b (the older web-backend tools were archived)
API_HELPERS = {"ApiError", "fail", "ok", "project_path"}


def epc(root, *argv):
    out, err = io.StringIO(), io.StringIO()
    code = main(["--projects-root", str(root), *argv, "--json"], stdout=out, stderr=err, clock=CLOCK, env={})
    return code, json.loads(out.getvalue())


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.cli_root, self.mcp_root, self.api_root = (self.dir / n for n in ("cli", "mcp", "api"))
        for root in (self.cli_root, self.mcp_root, self.api_root):
            root.mkdir()
        self.files = {}
        for name, doc in (("answers", M.ANSWERS), ("loads", W.loads_doc()), ("inputs", W.inputs_doc())):
            self.files[name] = self.dir / f"{name}.json"
            self.files[name].write_text(json.dumps(doc), encoding="utf-8")
        self.mcp = M.server(self.mcp_root)

    def init_all(self):
        self.assertEqual(epc(self.cli_root, "init", CODE, "--answers", str(self.files["answers"]))[0], 0)
        self.assertTrue(self.mcp("epc_project_init", project=CODE, answers=M.ANSWERS)["ok"])
        self.assertTrue(api.init_project(self.api_root, CODE, M.ANSWERS, clock=CLOCK, actor=ORC)["ok"])

    def run_all(self, stop_after):
        self.init_all()
        args = ["run", CODE, "--loads", str(self.files["loads"]), "--engine-inputs", str(self.files["inputs"]), "--run-id", "r-parity", "--detail"]
        if stop_after:
            args += ["--stop-after", str(stop_after)]
        code, via_cli = epc(self.cli_root, *args)
        via_mcp = self.mcp("epc_pipeline_run", project=CODE, loads=W.loads_doc(), engine_inputs=W.inputs_doc(), stop_after=stop_after, run_id="r-parity",
                           detail=True)
        direct = api.run_pipeline(self.api_root / CODE, loads=W.loads_doc(), engine_inputs=W.inputs_doc(), stop_after=stop_after, run_id="r-parity",
                                  detail=True, clock=CLOCK, actor=ORC)
        self.assertEqual(code, 0)
        return via_cli, via_mcp, json.loads(json.dumps(direct))


def masked(envelope):
    """The run without the DXF stamps; the audit's last hash differs between project folders (the log holds folder-specific text), so it is dropped."""
    audit = {k: v for k, v in envelope["data"]["audit"].items() if k != "last_hash"}
    return dict(envelope, data=dict(envelope["data"], run=M.without_dxf_hashes(envelope["data"]["run"]), audit=audit))


class RunParity(Base):
    def test_run_equals_mcp_and_api(self):
        via_cli, via_mcp, direct = self.run_all(11)
        self.assertTrue(via_cli["ok"], via_cli)
        self.assertEqual(masked(via_cli), masked(via_mcp))
        self.assertEqual(masked(via_cli), masked(direct))
        self.assertEqual(via_cli["data"]["pipeline_run_id"], "r-parity")

    def test_the_full_run_equals_mcp_and_api(self):
        via_cli, via_mcp, direct = self.run_all(None)
        self.assertEqual(masked(via_cli), masked(via_mcp))
        self.assertEqual(masked(via_cli), masked(direct))
        self.assertEqual(via_cli["data"]["workflow_state"], "draft_ready")

    def test_the_brief_run_equals_mcp(self):
        self.init_all()
        args = ["--loads", str(self.files["loads"]), "--engine-inputs", str(self.files["inputs"]), "--stop-after", "5", "--run-id", "r-b"]
        _, via_cli = epc(self.cli_root, "run", CODE, *args)
        via_mcp = self.mcp("epc_pipeline_run", project=CODE, loads=W.loads_doc(), engine_inputs=W.inputs_doc(), stop_after=5, run_id="r-b")
        drop = lambda e: dict(e, data=dict(e["data"], audit={k: v for k, v in e["data"]["audit"].items() if k != "last_hash"}))  # noqa: E731
        self.assertEqual(drop(via_cli), drop(via_mcp))
        self.assertTrue(all("outputs" not in r for r in via_cli["data"]["run"]["results"]))

    def test_status_equals_mcp_and_api_except_the_audit_block(self):
        self.run_all(5)
        _, via_cli = epc(self.cli_root, "status", CODE)
        via_mcp = self.mcp("epc_project_status", project=CODE)
        direct = json.loads(json.dumps(api.status(self.api_root / CODE, clock=CLOCK, actor=ORC)))
        rest = lambda e: {k: v for k, v in e["data"].items() if k != "audit"}  # noqa: E731
        self.assertEqual(rest(via_cli), rest(via_mcp))
        self.assertEqual(rest(via_cli), rest(direct))
        # the CLI call came first in its own project: each status call adds its own event; the same count as the other two projects' history
        counts = (via_cli["data"]["audit"]["count"], via_mcp["data"]["audit"]["count"], direct["data"]["audit"]["count"])
        self.assertEqual(counts[0], counts[1])
        self.assertEqual(counts[2], counts[0])
        self.assertTrue(via_cli["data"]["audit"]["chain_intact"])


class QueryParity(Base):
    def test_engines_list_has_the_24_engines_and_equals_mcp_and_api(self):
        code, via_cli = epc(self.cli_root, "engines", "list")
        self.assertEqual((code, via_cli["data"]["count"], len(via_cli["data"]["engines"])), (0, 37, 37))
        self.assertEqual(via_cli, self.mcp("epc_engine_list"))
        self.assertEqual(via_cli, json.loads(json.dumps(api.list_engines(actor=ORC))))

    def test_engines_info_equals_mcp(self):
        _, via_cli = epc(self.cli_root, "engines", "info", "aea90364")
        self.assertEqual(via_cli, self.mcp("epc_engine_info", name="aea90364"))
        self.assertEqual(via_cli["data"]["package"], "epc_aea90364")

    def test_stages_are_the_12_rows_of_the_prd(self):
        _, via_cli = epc(self.cli_root, "stages")
        rows = D.prd_rows()
        self.assertEqual((via_cli["data"]["count"], len(rows)), (12, 12))
        for row, (number, title, engines, status) in zip(via_cli["data"]["stages"], rows):
            self.assertEqual((row["number"], row["title"], row["engines"], row["status"]), (int(number), title, engines, status))
        self.assertEqual(via_cli, self.mcp("epc_stage_table"))

    def test_norms_equal_the_api_and_the_mcp_tool(self):
        _, via_cli = epc(self.cli_root, "norms", "epc_aea90364")
        self.assertEqual(via_cli, json.loads(json.dumps(api.norm_records("epc_aea90364", actor=ORC))))
        self.assertEqual(via_cli, self.mcp("epc_norm_records", package="epc_aea90364"))
        _, every = epc(self.cli_root, "norms")
        self.assertEqual(every, self.mcp("epc_norm_records"))
        self.assertGreater(every["data"]["count"], via_cli["data"]["count"])

    def test_norms_pending_equal_the_api_and_the_mcp_tool(self):
        for detail, argv, extra in ((False, ("norms-pending",), {}), (True, ("norms-pending", "--detail"), {"detail": True})):
            _, via_cli = epc(self.cli_root, *argv)
            self.assertEqual(via_cli, json.loads(json.dumps(api.norms_pending(detail, actor=ORC))))
            self.assertEqual(via_cli, self.mcp("epc_norms_pending", **extra))
        self.assertGreater(via_cli["data"]["pending_points"], 0)
        self.assertEqual(sum(r["pending"] for r in via_cli["data"]["rows"]), via_cli["data"]["pending_points"])

    def test_a_query_with_a_project_is_audited_in_that_project(self):
        self.init_all()
        before = epc(self.cli_root, "status", CODE)[1]["data"]["audit"]["count"]
        epc(self.cli_root, "stages", "--project", CODE)
        after = epc(self.cli_root, "status", CODE)[1]["data"]["audit"]["count"]
        self.assertEqual(after - before, 2)


class ParityTable(unittest.TestCase):
    def test_the_cli_table_is_the_expected_one(self):
        self.assertEqual({k: c.api_name for k, c in commands.COMMANDS.items()}, CLI_TO_API)

    def test_every_cli_command_calls_a_real_api_function(self):
        for key, name in CLI_TO_API.items():
            self.assertTrue(callable(getattr(api, name)), key)

    def test_the_cli_commands_are_the_mcp_tools_minus_the_mcp_only_ones(self):
        registry = M.REGISTRY
        tools = set(registry.names("full"))
        self.assertEqual(tools - MCP_ONLY, set(MCP_TO_API))
        self.assertTrue(MCP_ONLY <= tools)
        self.assertEqual(set(MCP_TO_API.values()), set(CLI_TO_API.values()))
        self.assertEqual(len(MCP_TO_API), len(set(MCP_TO_API.values())))

    def test_every_api_function_is_exposed_by_the_cli_and_the_mcp_server(self):
        public = {n for n in api.__all__ if n not in API_HELPERS}
        self.assertEqual(public, set(CLI_TO_API.values()))
        self.assertEqual(public, set(MCP_TO_API.values()))

    def test_the_write_commands_are_write_tools_in_the_full_profile_only(self):
        writes = {"init_project", "run_pipeline", "review", "submit", "approve", "issue"}
        readonly = set(M.REGISTRY.names("readonly"))
        for tool, name in MCP_TO_API.items():
            self.assertEqual(tool in readonly, name not in writes, tool)


if __name__ == "__main__":
    unittest.main()
