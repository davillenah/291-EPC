"""MIG-3X: permissions and tamper detection on the project folder that a real run of `synthetic_lv_small` produced.

(a) no agent role can write, create or delete the protected classes, and every denial is a `denied` event in a hash chain that still verifies;
(b) the PreToolUse hook blocks Write/Edit tool events and shell redirections into the real files of the project, and lets reads through;
(c) approving is for the engineer of record only, and the D21 guard (unreviewed norm records) keeps the project from ever reaching approved or issued;
(d) a changed input blocks a rerun at IM-01, and a changed output or manifest is reported by calc_check (CC-D06).

Needs the engine packages on PYTHONPATH (the gate's `harness-tests` environment has them).
"""
import copy
import importlib.util
import io
import json
import unittest
from pathlib import Path

import synthetic_lv as S

from disciplines.electrical_lv.store import ProjectStore
from epc_platform.events import EventLog
from epc_platform.permissions import PermissionDenied, enforce
from epc_platform.workflow import Workflow

HOOK = S.REPO / "harness" / ".claude" / "hooks" / "guard_paths.py"
SPEC = importlib.util.spec_from_file_location("guard_paths_synthetic", HOOK)
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)

ROSTER = S.read_json(S.REPO / "harness" / ".claude" / "roster.json")
AGENT_ROLES = [a["name"] for a in ROSTER["agents"]]
PROTECTED = ("ssot", "deliverables", "inputs", "audit", "config_normative", "schemas")
WRITE_ACTIONS = ("write", "create", "delete")
MANIFEST = ".epc/manifests/TR-001.manifest.json"
PROTECTED_FILES = (".epc/project_profile.json", ".epc/master_project_state.json", ".epc/ssot/stage_01_intake.json", ".epc/ssot/stage_16_package_issue.json", MANIFEST,
                   "inputs/intake_answers.json", ".epc/audit/events.jsonl")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proj = S.SyntheticRun().start()
        cls.addClassCleanup(cls.proj.cleanup)
        cls.root = cls.proj.project

    def log(self):
        return EventLog.for_project(self.root, S.clock)


class RosterIsTheFiveProductAgents(unittest.TestCase):
    def test_roles(self):
        self.assertEqual(sorted(AGENT_ROLES), ["calc_check", "documentation", "electrical_lv", "orchestrator", "procurement"])


class RolesAreDenied(Base):
    def test_every_agent_is_denied_write_create_delete_on_every_protected_class_and_each_denial_is_logged(self):
        log = self.log()
        before = len(log.read())
        denied = 0
        for role in AGENT_ROLES:
            for action in WRITE_ACTIONS:
                for path_class in PROTECTED:
                    with self.subTest(role=role, action=action, path_class=path_class):
                        with self.assertRaises(PermissionDenied) as caught:
                            enforce(role, action, path_class, inputs_frozen=True, log=log, actor_id=f"{role}-1", run_id="perm", target=f"{path_class}/x")
                        self.assertFalse(caught.exception.decision.allowed)
                        denied += 1
        records = log.read()
        new = records[before:]
        self.assertEqual((denied, len(new)), (len(AGENT_ROLES) * len(WRITE_ACTIONS) * len(PROTECTED), 90))
        self.assertEqual({r["result"] for r in new}, {"denied"})
        self.assertEqual({r["actor"]["role"] for r in new}, set(AGENT_ROLES))
        self.assertEqual(log.verify(), [])

    def test_the_inputs_are_frozen_for_everyone_after_the_run(self):
        store = ProjectStore(self.root)
        self.assertTrue(store.is_frozen())
        with self.assertRaises(Exception):
            store.write_input("late.json", b"{}")


class HookBlocksWrites(Base):
    def setUp(self):
        self.saved = G.PROJECTS
        G.PROJECTS = self.root.parent.resolve()      # the hook looks for projects under REPO/projects: point it at the temp projects root
        self.addCleanup(setattr, G, "PROJECTS", self.saved)

    def call(self, event, role, audit=False):
        env = {"EPC_ACTOR_ROLE": role}
        if audit:
            env.update(EPC_PROJECT_DIR=str(self.root), EPC_HOOK_NOW=S.CLOCK_TEXT, EPC_RUN_ID="hook")
        err = io.StringIO()
        return G.run(io.StringIO(json.dumps(event)), err, env), err.getvalue()

    def edit(self, tool, rel):
        return {"tool_name": tool, "tool_input": {"file_path": str(self.root / rel)}, "cwd": str(self.root)}

    def shell(self, command, tool="Bash"):
        return {"tool_name": tool, "tool_input": {"command": command}, "cwd": str(self.root)}

    def test_write_and_edit_of_real_project_files_are_blocked_for_every_agent(self):
        for role in AGENT_ROLES:
            for rel in PROTECTED_FILES:
                for tool in ("Write", "Edit", "MultiEdit"):
                    with self.subTest(role=role, file=rel, tool=tool):
                        self.assertTrue((self.root / rel).is_file(), rel)
                        code, message = self.call(self.edit(tool, rel), role)
                        self.assertEqual(code, 2)
                        self.assertIn("BLOCKED", message)

    def test_shell_redirections_into_real_files_are_blocked_for_every_agent(self):
        for role in AGENT_ROLES:
            for rel in PROTECTED_FILES:
                for command in (f"echo x > {rel}", f"echo x >> {rel}", f"printf x | tee {rel}"):
                    with self.subTest(role=role, file=rel, command=command):
                        code, message = self.call(self.shell(command), role)
                        self.assertEqual(code, 2, message)

    def test_blocks_name_the_rule_and_reads_pass(self):
        code, message = self.call(self.edit("Write", ".epc/ssot/stage_01_intake.json"), "orchestrator")
        self.assertEqual(code, 2)
        self.assertIn("D-07", message)
        code, message = self.call(self.edit("Write", "inputs/intake_answers.json"), "orchestrator")
        self.assertIn("D-04", message)
        for role in AGENT_ROLES:
            for rel in PROTECTED_FILES:
                reads = ({"tool_name": "Read", "tool_input": {"file_path": str(self.root / rel)}, "cwd": str(self.root)},
                         {"tool_name": "Grep", "tool_input": {"path": str(self.root / rel), "pattern": "x"}, "cwd": str(self.root)},
                         self.shell(f"cat {rel}"), self.shell(f"grep -c stage {rel}"), self.shell(f"python -c \"print(1)\" > /dev/null"))
                for event in reads:
                    with self.subTest(role=role, file=rel, tool=event["tool_name"]):
                        self.assertEqual(self.call(event, role)[0], 0)

    def test_blocks_are_audited_and_the_chain_still_verifies(self):
        log = self.log()
        before = len(log.read())
        code, _ = self.call(self.edit("Write", MANIFEST), "documentation", audit=True)
        self.assertEqual(code, 2)
        new = log.read()[before:]
        self.assertEqual([(r["action"], r["result"], r["actor"]["role"]) for r in new], [("hook:Write", "denied", "documentation")])
        self.assertEqual(log.verify(), [])

    def test_no_file_was_changed_by_the_blocked_calls(self):
        self.assertEqual(S.read_json(self.root / ".epc" / "ssot" / "stage_01_intake.json"), self.proj.ssot("stage_01_intake.json"))
        self.assertTrue(all((self.root / rel).is_file() for rel in PROTECTED_FILES))


class ApprovalNeedsTheEngineerAndD21(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        workflow = Workflow(cls.root, EventLog.for_project(cls.root, S.clock), ProjectStore(cls.root))
        cls.start_state = workflow.state

    def state(self):
        return ProjectStore(self.root).read_workflow()["state"]

    def test_approve_by_agents_is_permission_denied_at_every_state(self):
        for role in AGENT_ROLES:
            code, env = S.envelope(self.proj.root, "approve", S.CODE, "--actor-role", role, "--actor-id", f"{role}-1")
            self.assertEqual((code, env["ok"], env["error"]["code"]), (1, False, "permission_denied"), role)
        self.assertIn(self.state(), ("draft_ready", "in_review"))

    def test_the_engineer_is_blocked_by_d21_and_the_project_never_reaches_approved_or_issued(self):
        self.assertEqual(self.state(), "draft_ready")
        code, env = S.envelope(self.proj.root, "approve", S.CODE, *S.ENGINEER)
        self.assertEqual((code, env["error"]["code"]), (1, "bad_state"))              # not yet in review
        Workflow(self.root, self.log(), ProjectStore(self.root)).transition("submit_for_review", "engineer_of_record", "eng-1", run_id="review")
        self.assertEqual(self.state(), "in_review")
        code, env = S.envelope(self.proj.root, "approve", S.CODE, *S.ENGINEER)
        self.assertEqual((code, env["ok"], env["error"]["code"]), (1, False, "blocked_d21"))
        self.assertIn("not verified", env["error"]["message"])
        for argv in (S.ENGINEER, S.ORCHESTRATOR):
            code, env = S.envelope(self.proj.root, "issue", S.CODE, *argv)
            self.assertEqual((code, env["ok"]), (1, False))
        self.assertEqual(self.state(), "in_review")
        history = [h["to"] for h in ProjectStore(self.root).read_workflow()["history"]]
        self.assertNotIn("approved", history)
        self.assertNotIn("issued", history)
        for _path, manifest in ProjectStore(self.root).read_manifests():
            self.assertEqual(manifest["review_status"], "draft")
            self.assertIsNone(manifest["signed"])

    def test_the_denials_are_in_the_log_and_the_chain_verifies(self):
        S.envelope(self.proj.root, "approve", S.CODE, "--actor-role", "orchestrator", "--actor-id", "o9")
        denied = [r for r in self.log().read() if r["result"] == "denied" and r["actor"]["id"] == "o9"]
        self.assertEqual([r["action"] for r in denied], ["transition:approve"])
        self.assertEqual(self.log().verify(), [])


class TamperIsDetected(unittest.TestCase):
    def setUp(self):
        self.proj = S.SyntheticRun().start()
        self.addCleanup(self.proj.cleanup)
        self.root = self.proj.project

    def run_dict(self):
        return {"pipeline_run_id": S.RUN_ID, "results": [self.proj.ssot(p.name) for p in self.proj.stage_files()]}

    def files(self, changed=None):
        stage14 = self.proj.ssot("stage_14_drawings.json")["outputs"]
        files = {f"{stage14['directory']}/{f['path']}": (self.root / ".epc" / "runs" / S.RUN_ID / stage14["directory"] / f["path"]).read_bytes() for f in stage14["files"]}
        files.update(changed or {})
        return files

    def check(self, run, files):
        import epc_calc_check
        return epc_calc_check.check_run(run, files=files, run_id="tamper", groups=[epc_calc_check.GROUP_MANIFESTS])

    def test_the_untouched_run_has_no_manifest_finding(self):
        self.assertEqual(self.check(self.run_dict(), self.files()), [])

    def test_a_changed_input_blocks_the_rerun_at_im01(self):
        path = self.root / "inputs" / "loads" / "loads.json"
        path.write_bytes(path.read_bytes() + b" ")                       # one byte, written behind the store's back
        store = ProjectStore(self.root)
        self.assertEqual([f["clause"] for f in store.verify_inputs_unchanged("probe")], ["project criterion IM-01"])
        (self.proj.work / "c.json").write_text(json.dumps([{"note": "synthetic correction"}]), encoding="utf-8")
        self.assertEqual(S.envelope(self.proj.root, "review", S.CODE, "--corrections", str(self.proj.work / "c.json"), *S.ENGINEER)[0], 0)
        code, env = self.proj.run(run_id="synth-run-2")
        self.assertEqual(code, 0)
        run = env["data"]["run"]
        self.assertFalse(run["summary"]["ok"])
        self.assertEqual(run["summary"]["stopped_at"], 2)
        blocked = run["results"][1]
        self.assertEqual((blocked["status"], blocked["reason"]), ("blocked", "inputs_changed"))
        self.assertEqual({f["clause"] for f in blocked["findings"]}, {"project criterion IM-01"})
        self.assertNotEqual(env["data"]["workflow_state"], "draft_ready")
        self.assertEqual(ProjectStore(self.root).read_state()["status"], "blocked")

    def test_a_changed_output_byte_is_reported_as_cc_d06(self):
        stage14 = self.proj.ssot("stage_14_drawings.json")["outputs"]
        key = f"{stage14['directory']}/SLD_TS-SYNTH.dxf"
        data = bytearray(self.files()[key])
        data[0] ^= 1
        found = self.check(self.run_dict(), self.files({key: bytes(data)}))
        self.assertTrue(found and all("CC-D06" in f["clause"] for f in found), found)
        self.assertTrue(any(f["field"].endswith("/sha256") for f in found))
        self.assertTrue(any("SHA-256 of the file bytes" in f["evidence"][0] for f in found))

    def test_a_changed_manifest_hash_is_reported_as_cc_d06(self):
        run = self.run_dict()
        package = copy.deepcopy(run["results"][15])
        item = package["outputs"]["manifests"][0]["manifest"]
        entry = item["files"][0]
        entry["sha256"] = "0" * 63 + ("1" if entry["sha256"][-1] != "1" else "2")
        run["results"][15] = package
        found = self.check(run, self.files())
        self.assertTrue(found and all("CC-D06" in f["clause"] for f in found), found)

    def test_a_changed_manifest_file_on_disk_fails_its_own_check(self):
        path = self.root / MANIFEST
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["review_status"] = "approved_for_construction"
        manifest["files"][0]["sha256"] = "f" * 64
        files = self.files({MANIFEST: json.dumps(manifest).encode("utf-8")})
        found = self.check(self.run_dict(), files)
        self.assertTrue(any("CC-D06" in f["clause"] for f in found), found)


if __name__ == "__main__":
    unittest.main()
