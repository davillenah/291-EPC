"""MIG-33c: behaviour of the `epc` CLI (`epc_platform.cli.main.main`, in process): exit codes, files, roles, the project chain, rendering.

The synthetic project and the builders are those of test_mcp_parity / test_pipeline_wiring. Needs the engine packages on PYTHONPATH.
"""
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

import test_mcp_parity as M
import test_pipeline_wiring as W

from disciplines.electrical_lv.store import ProjectStore
from epc_platform import api
from epc_platform.cli import main as cli_main
from epc_platform.cli.main import main
from epc_platform.events import EventLog
from epc_platform.workflow import Workflow

CLOCK = M.CLOCK
ENG = ["--actor-role", "engineer_of_record", "--actor-id", "e1"]
CODE = "CLI-1"


def epc(argv, env=None):
    """(exit code, stdout text, stderr text) of one in-process `epc` call."""
    out, err = io.StringIO(), io.StringIO()
    code = main(list(argv), stdout=out, stderr=err, clock=CLOCK, env={} if env is None else env)
    return code, out.getvalue(), err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.root = self.dir / "projects"
        self.root.mkdir()
        self.files = self.dir / "files"
        self.files.mkdir()
        self.write("answers.json", dict(M.ANSWERS, project_code=CODE))
        self.write("loads.json", W.loads_doc())
        self.write("inputs.json", W.inputs_doc())

    def write(self, name, data):
        path = self.files / name
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return str(path)

    def run_epc(self, *argv, env=None):
        return epc(["--projects-root", str(self.root), *argv], env)

    def envelope(self, *argv):
        code, out, _ = self.run_epc(*argv, "--json")
        return code, json.loads(out)

    def init(self):
        return self.envelope("init", CODE, "--answers", str(self.files / "answers.json"))

    def events(self):
        return EventLog.for_project(self.root / CODE, CLOCK).read()

    def seed(self, state):
        store = ProjectStore(self.root / CODE)
        with store.pipeline_session("seed") as token:
            store.write_workflow(token, {"state": state, "history": []})


class UsageTests(Base):
    def test_usage_errors_exit_2_without_a_traceback(self):
        for argv in ([], ["nope"], ["run"], ["run", CODE], ["init", CODE], ["engines"], ["engines", "nope"], ["run", CODE, "--loads", "x", "--stop-after", "z"]):
            with self.subTest(argv=argv):
                code, out, err = epc(argv)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("error", err)
                self.assertNotIn("Traceback", err)

    def test_help_exits_0_on_stdout(self):
        for argv in (["-h"], ["run", "--help"], ["engines", "info", "-h"]):
            code, out, err = epc(argv)
            self.assertEqual((code, err), (0, ""))
            self.assertIn("usage: epc", out)

    def test_the_global_options_work_before_and_after_the_subcommand(self):
        before = self.run_epc("--json", "stages")
        after = self.run_epc("stages", "--json")
        self.assertEqual(before, after)
        self.assertEqual(json.loads(before[1])["data"]["count"], 16)


class FileTests(Base):
    def test_invalid_and_missing_json_files_are_error_envelopes(self):
        bad = self.write("bad.json", "{not json")
        for path, wanted in ((bad, "invalid_json"), (str(self.files / "missing.json"), "unreadable_file")):
            with self.subTest(wanted=wanted):
                code, env = self.envelope("init", CODE, "--answers", path)
                self.assertEqual((code, env["ok"], env["error"]["code"]), (1, False, wanted))
                human = self.run_epc("init", CODE, "--answers", path)
                self.assertEqual((human[0], human[1]), (1, ""))
                self.assertIn(f"error [{wanted}]", human[2])
                self.assertNotIn("Traceback", human[2])
        self.assertFalse((self.root / CODE).exists())

    def test_a_byte_order_mark_is_accepted(self):
        path = self.files / "bom.json"
        path.write_bytes(b"\xef\xbb\xbf" + json.dumps(dict(M.ANSWERS, project_code=CODE)).encode())
        self.assertEqual(self.envelope("init", CODE, "--answers", str(path))[0], 0)

    def test_the_cli_writes_no_file_of_its_own(self):
        before = sorted(p.name for p in self.files.iterdir())
        self.envelope("stages")
        self.assertEqual(sorted(p.name for p in self.files.iterdir()), before)


class RenderTests(Base):
    def test_only_json_mode_prints_raw_json(self):
        self.init()
        for argv in (["stages"], ["engines", "list"], ["engines", "info", "sld"], ["norms", "epc_aea90364"], ["status", CODE]):
            with self.subTest(argv=argv):
                code, out, _ = self.run_epc(*argv)
                self.assertEqual(code, 0)
                self.assertFalse(out.lstrip().startswith(("{", "[")))
                with self.assertRaises(ValueError):
                    json.loads(out)
                json_code, json_out, _ = self.run_epc(*argv, "--json")
                self.assertEqual((json_code, json.loads(json_out)["ok"]), (0, True))

    def test_the_human_tables_show_the_rows(self):
        stages = self.run_epc("stages")[1]
        self.assertIn("feeder_sizing", stages)
        self.assertTrue(stages.rstrip().endswith("16 stages"))
        self.assertIn("30 engines", self.run_epc("engines", "list")[1])
        status = self.run_epc("status", CODE) if self.init() else None
        self.assertIn("workflow", status[1])
        self.assertIn("create:inputs", status[1])

    def test_json_output_is_canonical(self):
        out = self.run_epc("stages", "--json")[1]
        self.assertEqual(out, json.dumps(json.loads(out), sort_keys=True, indent=2, ensure_ascii=False) + "\n")

    def test_an_unknown_engine_is_an_error_on_stderr(self):
        code, out, err = self.run_epc("engines", "info", "nope")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("error [unknown_engine]", err)


class SessionTests(Base):
    def test_defaults_and_environment(self):
        self.init()
        code, env = self.envelope("status", CODE)
        self.assertEqual(env["data"]["audit"]["last"][-1]["actor"], {"role": "orchestrator", "id": "cli"})
        out = io.StringIO()
        status = main(["status", CODE, "--json"], stdout=out, stderr=io.StringIO(), clock=CLOCK,
                      env={"EPC_PROJECTS_ROOT": str(self.root), "EPC_ACTOR_ROLE": "reviewing_engineer", "EPC_ACTOR_ID": "r9"})
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out.getvalue())["data"]["audit"]["last"][-1]["actor"], {"role": "reviewing_engineer", "id": "r9"})

    def test_the_option_beats_the_environment(self):
        self.init()
        code, out, _ = self.run_epc("status", CODE, "--json", "--actor-id", "opt", env={"EPC_ACTOR_ID": "env"})
        self.assertEqual(json.loads(out)["data"]["audit"]["last"][-1]["actor"]["id"], "opt")

    def test_the_default_clock_is_a_utc_timestamp(self):
        self.assertRegex(cli_main.utc_now(), r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.init()
        out, err = io.StringIO(), io.StringIO()
        main(["--projects-root", str(self.root), "status", CODE, "--json"], stdout=out, stderr=err, env={})
        stamp = json.loads(out.getvalue())["data"]["audit"]["last"][-1]["ts"]
        self.assertRegex(stamp, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_the_default_projects_root_is_next_to_the_harness(self):
        from epc_platform.cli import commands
        self.assertEqual(commands.default_projects_root().name, "projects")
        self.assertTrue((commands.default_projects_root().parent / "harness").is_dir())

    def test_a_wrong_project_or_role_is_reported(self):
        self.assertEqual(self.envelope("status", "NOPE")[1]["error"]["code"], "project_not_found")
        self.assertEqual(self.envelope("status", "../x")[1]["error"]["code"], "invalid_project")
        self.init()
        code, env = self.envelope("status", CODE, "--actor-role", "stranger")
        self.assertEqual((code, env["error"]["code"]), (1, "permission_denied"))


class ChainTests(Base):
    def test_init_run_status_approve_review_and_issue(self):
        self.assertEqual(self.init()[0], 0)
        self.assertEqual(self.init()[1]["error"]["code"], "project_exists")
        code, env = self.envelope("run", CODE, "--loads", str(self.files / "loads.json"), "--engine-inputs", str(self.files / "inputs.json"), "--run-id", "r-1")
        self.assertEqual((code, env["data"]["workflow_state"], env["data"]["run"]["summary"]["stages_run"]), (0, "draft_ready", 16))
        self.assertEqual(self.envelope("status", CODE)[1]["data"]["workflow"]["state"], "draft_ready")
        # in review with real manifests: the norm records are not verified, so D21 refuses the approval
        Workflow(self.root / CODE, EventLog.for_project(self.root / CODE, CLOCK)).transition("submit_for_review", "engineer_of_record", "e1")
        code, env = self.envelope("approve", CODE, *ENG)
        self.assertEqual((code, env["error"]["code"]), (1, "blocked_d21"))
        corrections = self.write("corrections.json", [{"target": "stage_08", "note": "check the cable"}])
        code, env = self.envelope("review", CODE, "--corrections", corrections, *ENG)
        self.assertEqual((code, env["data"]["workflow_state"]), (0, "corrected"))
        self.assertTrue((self.root / CODE / env["data"]["review_file"]).is_file())
        self.seed("approved")
        code, env = self.envelope("issue", CODE, *ENG)
        self.assertEqual((code, env["error"]["code"]), (1, "blocked_d21"))
        self.assertEqual(ProjectStore(self.root / CODE).read_workflow()["state"], "approved")
        self.assertEqual(EventLog.for_project(self.root / CODE, CLOCK).verify(), [])

    def test_issue_before_approval_is_a_bad_state(self):
        self.init()
        code, env = self.envelope("issue", CODE, *ENG)
        self.assertEqual((code, env["error"]["code"]), (1, "bad_state"))

    def test_approve_by_a_role_that_is_not_the_engineer_is_denied_and_logged(self):
        self.init()
        self.seed("in_review")
        code, env = self.envelope("approve", CODE, "--actor-role", "orchestrator", "--actor-id", "o1")
        self.assertEqual((code, env["error"]["code"]), (1, "permission_denied"))
        denied = [e for e in self.events() if e["result"] == "denied"]
        self.assertEqual([(e["action"], e["actor"]) for e in denied], [("transition:approve", {"role": "orchestrator", "id": "o1"})])
        self.assertEqual(ProjectStore(self.root / CODE).read_workflow()["state"], "in_review")

    def test_approve_without_manifests_is_blocked_by_d21(self):
        self.init()
        self.seed("in_review")
        code, env = self.envelope("approve", CODE, *ENG)
        self.assertEqual((code, env["error"]["code"]), (1, "blocked_d21"))
        self.assertEqual(self.run_epc("approve", CODE, *ENG)[1], "")

    def test_a_denied_run_by_an_agent_role(self):
        self.init()
        code, env = self.envelope("run", CODE, "--loads", str(self.files / "loads.json"), "--stop-after", "3", "--actor-role", "electrical_lv")
        self.assertEqual((code, env["error"]["code"]), (1, "permission_denied"))
        self.assertEqual(len([e for e in self.events() if e["result"] == "denied"]), 1)

    def test_approve_envelope_equals_the_api(self):
        self.init()
        self.seed("in_review")
        code, env = self.envelope("approve", CODE, *ENG)
        direct = api.approve(self.root / CODE, {"role": "engineer_of_record", "id": "e1"}, clock=CLOCK)
        self.assertEqual(env, json.loads(json.dumps(direct)))


if __name__ == "__main__":
    unittest.main()
