"""MIG-34: the PreToolUse hook `harness/.claude/hooks/guard_paths.py` blocks what PRD 14.4 forbids and lets benign work through.

Tested in process (fast, a table of synthetic events) and as a subprocess (the way Claude Code runs it: JSON on stdin, exit code 2 plus one line
on stderr that names the rule id). The rules come from `epc_platform.permissions`; this file only checks the hook's behaviour.

  python -m pytest harness/tests/architecture/test_guard_hook.py
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "harness" / ".claude" / "hooks" / "guard_paths.py"
_SPEC = importlib.util.spec_from_file_location("guard_paths_under_test", HOOK)
G = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(G)
CWD = str(REPO)
P = "projects/p1"


def edit(tool, path):
    return {"tool_name": tool, "tool_input": {"file_path": path}, "cwd": CWD}


def bash(command, tool="Bash"):
    return {"tool_name": tool, "tool_input": {"command": command}, "cwd": CWD}


def call(event, role=None, environ=None):
    env = dict(environ or {})
    if role:
        env["EPC_ACTOR_ROLE"] = role
    err = io.StringIO()
    code = G.run(io.StringIO(json.dumps(event)), err, env)
    return code, err.getvalue()


# (name, event, expected rule id)
BLOCKED = [
    ("write ssot", edit("Write", f"{P}/ssot/stage_04.json"), "D-07"),
    ("edit ssot", edit("Edit", f"{P}/ssot/stage_04.json"), "D-07"),
    ("multiedit ssot", edit("MultiEdit", f"{P}/ssot/stage_04.json"), "D-07"),
    ("notebook ssot", {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": f"{P}/ssot/n.ipynb"}, "cwd": CWD}, "D-07"),
    ("write deliverable", edit("Write", f"{P}/deliverables/R0/sld.dxf"), "D-07"),
    ("write input", edit("Write", f"{P}/inputs/brief.pdf"), "D-04"),
    ("edit input", edit("Edit", f"{P}/inputs/brief.pdf"), "D-04"),
    ("write audit", edit("Write", f"{P}/audit/events.jsonl"), "D-09"),
    ("edit audit", edit("Edit", f"{P}/audit/events.jsonl"), "D-09"),
    ("write profile", edit("Write", f"{P}/project_profile.json"), "D-07"),
    ("write state", edit("Edit", f"{P}/master_project_state.json"), "D-07"),
    ("write normative config", edit("Write", "harness/config/normative/AR/values.json"), "D-07"),
    ("edit normative config", edit("Edit", "harness/config/normative/AR/values.json"), "D-07"),
    ("write schema", edit("Write", "harness/schemas/project_profile.schema.json"), "D-10"),
    ("edit schema", edit("Edit", "harness/schemas/project_profile.schema.json"), "D-10"),
    ("write knowledge normative", edit("Write", "harness/knowledge/normative/AEA90364/x.md"), "H-01"),
    ("absolute path", edit("Write", str(REPO / "projects" / "p1" / "ssot" / "a.json")), "D-07"),
    ("traversal", edit("Write", f"{P}/runs/r1/../../ssot/a.json"), "D-07"),
    ("unknown project path", edit("Write", f"{P}/zzz/a.txt"), "H-03"),
    ("missing path", {"tool_name": "Write", "tool_input": {}, "cwd": CWD}, "H-00"),
    ("redirect", bash(f"echo x > {P}/ssot/a.json"), "D-07"),
    ("append", bash(f"echo x >> {P}/deliverables/R0/a.txt"), "D-07"),
    ("redirect no space", bash(f"echo x>{P}/inputs/a.txt"), "D-04"),
    ("redirect backslash", bash("echo x > projects\\p1\\ssot\\a.json"), "D-07"),
    ("tee", bash(f"echo x | tee {P}/ssot/a.json"), "D-07"),
    ("Set-Content", bash(f"Set-Content -Path {P}/ssot/a.json -Value x", "PowerShell"), "D-07"),
    ("Out-File", bash(f"'x' | Out-File {P}/deliverables/a.txt", "PowerShell"), "D-07"),
    ("cp into ssot", bash(f"cp /tmp/a.json {P}/ssot/a.json"), "D-07"),
    ("mv out of ssot", bash(f"mv {P}/ssot/a.json /tmp/a.json"), "D-07"),
    ("sed -i", bash(f"sed -i s/a/b/ {P}/ssot/a.json"), "D-07"),
    ("sed -i combined flags", bash(f"sed -ni p {P}/deliverables/a.txt"), "D-07"),
    ("python open w", bash(f"python -c \"open('{P}/ssot/a.json','w').write('x')\""), "D-07"),
    ("python write_text", bash(f"python -c \"from pathlib import Path; Path('{P}/audit/events.jsonl').write_text('')\""), "D-09"),
    ("dd", bash(f"dd if=/dev/zero of={P}/ssot/a.bin"), "D-07"),
    ("write schema by shell", bash("echo {} > harness/schemas/x.schema.json"), "D-10"),
    ("write normative by shell", bash("cp x.json harness/config/normative/AR/x.json"), "D-07"),
    ("cd then relative redirect", bash(f"cd {P}/ssot && echo x > a.json"), "D-07"),
    ("unresolvable path", bash("echo x > $TARGET"), "H-03"),
    ("bash -c wrapper", bash(f"bash -c 'echo x > {P}/ssot/a.json'"), "D-07"),
    ("encoded powershell", bash("powershell -EncodedCommand AAAA", "PowerShell"), "H-03"),
    ("git commit", bash("git commit -m x"), "H-02"),
    ("git push", bash("git push origin main"), "H-02"),
    ("git merge", bash("git merge dev"), "H-02"),
    ("git reset", bash("git reset --hard"), "H-02"),
    ("git checkout", bash("git checkout main"), "H-02"),
    ("git switch", bash("git switch dev"), "H-02"),
    ("git branch", bash("git branch x"), "H-02"),
    ("git tag", bash("git tag v1"), "H-02"),
    ("git stash", bash("git stash"), "H-02"),
    ("git rebase", bash("git rebase dev"), "H-02"),
    ("git add", bash("git add -A"), "H-02"),
    ("git with -C", bash("git -C . commit -m x"), "H-02"),
    ("git after &&", bash("ls && git push"), "H-02"),
    ("rm", bash("rm notes.txt"), "D-01"),
    ("rm -rf", bash("rm -rf build"), "D-01"),
    ("del", bash("del notes.txt"), "D-01"),
    ("Remove-Item", bash("Remove-Item notes.txt", "PowerShell"), "D-01"),
    ("rmdir", bash("rmdir old"), "D-01"),
    ("find -delete", bash("find . -name '*.tmp' -delete"), "D-01"),
    ("xargs rm", bash("ls | xargs rm"), "D-01"),
    ("rm in sh -c", bash("sh -c 'rm x'"), "D-01"),
    ("python rmtree", bash("python -c \"import shutil; shutil.rmtree('x')\""), "D-01"),
    ("unknown writing tool", {"tool_name": "SuperWriteFile", "tool_input": {"x": 1}}, "H-04"),
    ("no command", {"tool_name": "Bash", "tool_input": {}}, "H-00"),
]

# (name, event, role)
ALLOWED = [
    ("read ssot", edit("Read", f"{P}/ssot/a.json"), None),
    ("glob", {"tool_name": "Glob", "tool_input": {"pattern": "**/*.py"}}, None),
    ("grep", {"tool_name": "Grep", "tool_input": {"pattern": "x"}}, None),
    ("read normative pdf", edit("Read", "harness/knowledge/normative/AEA90364/x.pdf"), None),
    ("write run folder", edit("Write", f"{P}/runs/run-1/log.txt"), None),
    ("write review as calc_check", edit("Write", f"{P}/reviews/findings.json"), "calc_check"),
    ("write review as reviewing engineer", edit("Write", f"{P}/reviews/findings.json"), "reviewing_engineer"),
    ("create transmittal as orchestrator", edit("Write", f"{P}/transmittals/new_transmittal_x.md"), "orchestrator"),
    ("write a test", edit("Write", "harness/tests/unit/test_new.py"), None),
    ("edit a doc", edit("Edit", "harness/docs/BACKLOG.md"), None),
    ("write a doc", edit("Write", "docs/notes.md"), None),
    ("engineer edits normative config", edit("Edit", "harness/config/normative/AR/values.json"), "engineer_of_record"),
    ("project folder itself", bash(f"ls {P}"), None),
    ("ls", bash("ls -la"), None),
    ("git status", bash("git status"), None),
    ("git diff", bash("git diff --stat"), None),
    ("git log", bash("git log --oneline -5"), None),
    ("git ls-files", bash("git ls-files harness"), None),
    ("git check-ignore", bash("git check-ignore -v x"), None),
    ("cat ssot", bash(f"cat {P}/ssot/a.json"), None),
    ("grep ssot", bash(f"grep -rn x {P}/ssot > /dev/null"), None),
    ("stderr redirect", bash("ls missing 2>&1"), None),
    ("redirect to nul", bash("ls > nul"), None),
    ("copy from ssot into runs", bash(f"cp {P}/ssot/a.json {P}/runs/r1/a.json"), None),
    ("redirect into docs", bash("echo x > harness/docs/x.md"), None),
    ("redirect into runs", bash(f"echo x > {P}/runs/r1/x.txt"), None),
    ("pytest", bash("python -m pytest harness/tests -q"), None),
    ("python reading", bash(f"python -c \"print(open('{P}/ssot/a.json').read())\""), None),
    ("build tool", bash(".venv/Scripts/python harness/tools/build/epc_build.py registry"), None),
    ("epc mcp tool", {"tool_name": "mcp__epc__epc_project_status", "tool_input": {}}, None),
    ("unknown read-only tool", {"tool_name": "Inspector", "tool_input": {}}, None),
    ("echo mentioning git", bash("echo git commit is forbidden"), None),
]


class InProcess(unittest.TestCase):
    def test_the_table_is_big_enough(self):
        self.assertGreaterEqual(len(BLOCKED), 40)
        self.assertGreaterEqual(len(ALLOWED), 20)

    def test_blocked_events(self):
        for name, event, rule in BLOCKED:
            with self.subTest(name):
                code, message = call(event)
                self.assertEqual(code, 2, message)
                self.assertIn(f"[{rule}]", message)
                self.assertEqual(len(message.strip().splitlines()), 1)

    def test_allowed_events(self):
        for name, event, role in ALLOWED:
            with self.subTest(name):
                self.assertEqual(call(event, role), (0, ""))

    def test_every_agent_role_is_blocked_from_every_protected_class(self):
        from epc_platform.permissions import rules as R
        paths = {"ssot": f"{P}/ssot/a", "deliverables": f"{P}/deliverables/a", "inputs": f"{P}/inputs/a", "audit": f"{P}/audit/a",
                 "schemas": "harness/schemas/a", "config_normative": "harness/config/normative/a"}
        for role in R.AGENTS:
            for cls, path in paths.items():
                with self.subTest(role=role, cls=cls):
                    self.assertEqual(call(edit("Write", path), role)[0], 2)

    def test_malformed_input_fails_closed(self):
        for text in ("", "not json", "[]", "{}", '{"tool_name": 3}', '{"tool_name": "Write", "tool_input": []}'):
            with self.subTest(text=text):
                err = io.StringIO()
                self.assertEqual(G.run(io.StringIO(text), err, {}), 2)
                self.assertIn("[H-00]", err.getvalue())

    def test_an_unknown_role_is_blocked_on_writes_and_not_on_reads(self):
        code, message = call(edit("Write", "docs/a.md"), "nobody")
        self.assertEqual(code, 2)
        self.assertIn("[D-98]", message)
        self.assertEqual(call(edit("Read", "docs/a.md"), "nobody")[0], 0)

    def test_a_crash_in_the_decision_fails_closed(self):
        original = G.decide
        G.decide = lambda event, role: 1 / 0
        try:
            code, message = call(edit("Write", "docs/a.md"))
        finally:
            G.decide = original
        self.assertEqual(code, 2)
        self.assertIn("[H-00]", message)

    def test_the_hook_reads_no_system_clock(self):
        text = HOOK.read_text(encoding="utf-8")
        for needle in ("datetime", "time.time", "import time", "utcnow"):
            self.assertNotIn(needle, text)


class Audit(unittest.TestCase):
    def test_a_block_is_appended_to_the_project_audit_log(self):
        from epc_platform.events import EventLog
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "p9"
            project.mkdir()
            env = {"EPC_PROJECT_DIR": str(project), "EPC_HOOK_NOW": "2026-01-01T00:00:00Z", "EPC_RUN_ID": "run-x"}
            self.assertEqual(call(edit("Write", f"{P}/ssot/a.json"), environ=env)[0], 2)
            self.assertEqual(call(bash("git push"), environ=env)[0], 2)
            self.assertEqual(call(edit("Read", f"{P}/ssot/a.json"), environ=env)[0], 0)
            log = EventLog.for_project(project, lambda: "-")
            records = log.read()
            self.assertEqual([r["result"] for r in records], ["denied", "denied"])
            self.assertEqual(records[0]["ts"], "2026-01-01T00:00:00Z")
            self.assertEqual(records[0]["detail"]["rule_id"], "D-07")
            self.assertEqual(records[1]["detail"]["rule_id"], "H-02")
            self.assertEqual(log.verify(), [])

    def test_without_the_variable_nothing_is_written(self):
        self.assertFalse(G.audit_denied({"tool_name": "Write"}, "orchestrator", G.Block("D-07", "x"), {}))

    def test_the_timestamp_defaults_to_a_dash(self):
        from epc_platform.events import EventLog
        with tempfile.TemporaryDirectory() as tmp:
            call(edit("Write", f"{P}/ssot/a.json"), environ={"EPC_PROJECT_DIR": tmp})
            self.assertEqual(EventLog.for_project(tmp, lambda: "x").read()[0]["ts"], "-")

    def test_a_broken_audit_target_never_breaks_the_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "afile"
            blocker.write_text("x", encoding="utf-8")
            code, message = call(edit("Write", f"{P}/ssot/a.json"), environ={"EPC_PROJECT_DIR": str(blocker)})
            self.assertEqual(code, 2)
            self.assertIn("[D-07]", message)


class AsSubprocess(unittest.TestCase):
    def run_hook(self, event_text, **env):
        full = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "EPC_ACTOR_ROLE", "EPC_PROJECT_DIR")}
        full.update(env)
        return subprocess.run([sys.executable, str(HOOK)], input=event_text, capture_output=True, text=True, cwd=str(REPO), env=full, timeout=60)

    def test_blocked_events_exit_2_with_the_rule_id_on_stderr(self):
        for name, event, rule in BLOCKED[::9]:
            with self.subTest(name):
                done = self.run_hook(json.dumps(event))
                self.assertEqual(done.returncode, 2, done.stderr)
                self.assertIn(f"[{rule}]", done.stderr)
                self.assertEqual(done.stdout, "")

    def test_allowed_events_exit_0_in_silence(self):
        for name, event, role in ALLOWED[::8]:
            with self.subTest(name):
                done = self.run_hook(json.dumps(event), **({"EPC_ACTOR_ROLE": role} if role else {}))
                self.assertEqual((done.returncode, done.stderr), (0, ""))

    def test_garbage_and_empty_input_exit_2(self):
        for text in ("", "garbage", "\x00"):
            with self.subTest(text=text):
                done = self.run_hook(text)
                self.assertEqual(done.returncode, 2)
                self.assertIn("[H-00]", done.stderr)

    def test_the_default_role_is_the_orchestrator(self):
        event = json.dumps(edit("Write", f"{P}/transmittals/new_transmittal_y.md"))
        self.assertEqual(self.run_hook(event).returncode, 0)
        self.assertEqual(self.run_hook(event, EPC_ACTOR_ROLE="electrical_lv").returncode, 2)


if __name__ == "__main__":
    unittest.main()
