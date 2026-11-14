"""MIG-33a: the RACI as data, `check`, `classify_path` and `enforce`."""
import itertools
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from epc_platform.events import EventLog
from epc_platform.permissions import PathError, PermissionDenied, check, classify_path, enforce, may_trigger
from epc_platform.permissions import rules as R
from epc_platform.permissions.core import INTERNAL_CLASSES


def clock():
    return "2026-01-01T00:00:00Z"


class MatrixTests(unittest.TestCase):
    def test_agents_never_write_ssot_deliverables_config_normative(self):
        for role, action, cls in itertools.product(R.AGENTS, R.WRITES, (R.SSOT, R.DELIVERABLES, R.CONFIG_NORMATIVE)):
            for frozen in (False, True):
                with self.subTest(role=role, action=action, cls=cls):
                    self.assertFalse(check(role, action, cls, frozen).allowed)

    def test_agents_never_write_inputs_once_frozen(self):
        for role, action in itertools.product(R.AGENTS, R.WRITES):
            with self.subTest(role=role, action=action):
                d = check(role, action, R.INPUTS, inputs_frozen=True)
                self.assertFalse(d.allowed)
                self.assertEqual(d.rule_id, "D-04")

    def test_intake_before_the_freeze_is_for_the_orchestrator_and_the_engineer_only(self):
        allowed = {r for r in R.ROLES if check(r, R.CREATE, R.INPUTS).allowed}
        self.assertEqual(allowed, {R.ORCHESTRATOR, R.ENGINEER})
        self.assertFalse(any(check(r, R.WRITE, R.INPUTS, True).allowed for r in R.ROLES))

    def test_nobody_deletes_anything(self):
        for role, cls in itertools.product(R.ROLES, R.PATH_CLASSES):
            self.assertEqual(check(role, R.DELETE, cls).rule_id, "D-01")

    def test_only_the_engineer_of_record_signs_and_approves_norm_values(self):
        for action in (R.SIGN, R.APPROVE_NORM_VALUES):
            for role, cls in itertools.product(R.ROLES, R.PATH_CLASSES):
                with self.subTest(action=action, role=role, cls=cls):
                    if role == R.ENGINEER and cls == (R.DELIVERABLES if action == R.SIGN else R.CONFIG_NORMATIVE):
                        self.assertTrue(check(role, action, cls).allowed)
                    else:
                        self.assertFalse(check(role, action, cls).allowed)

    def test_the_producer_never_verifies_and_the_verifier_never_produces(self):
        for cls in (R.SSOT, R.RUNS, R.DELIVERABLES, R.TRANSMITTALS):
            for action in R.WRITES:
                self.assertEqual(check(R.CALC_CHECK, action, cls).rule_id, "D-05")
        for role, action in itertools.product(R.PRODUCERS, R.WRITES):
            self.assertEqual(check(role, action, R.REVIEWS).rule_id, "D-06")
        for action in R.WRITES:
            self.assertTrue(check(R.CALC_CHECK, action, R.REVIEWS).allowed)

    def test_everybody_reads_everything(self):
        for role, cls in itertools.product(R.ROLES, R.PATH_CLASSES):
            self.assertTrue(check(role, R.READ, cls).allowed)

    def test_issue_is_for_the_engineer_and_the_orchestrator(self):
        allowed = {r for r in R.ROLES if check(r, R.ISSUE, R.DELIVERABLES).allowed}
        self.assertEqual(allowed, {R.ENGINEER, R.ORCHESTRATOR})

    def test_ssot_runs_deliverables_audit_schemas_code_are_written_by_no_role(self):
        for role, action, cls in itertools.product(R.ROLES, R.WRITES, (R.SSOT, R.RUNS, R.DELIVERABLES, R.AUDIT, R.SCHEMAS, R.HARNESS_CODE)):
            self.assertFalse(check(role, action, cls).allowed, (role, action, cls))

    def test_only_the_engineer_edits_norm_data_among_roles(self):
        self.assertEqual({r for r in R.ROLES if check(r, R.WRITE, R.CONFIG_NORMATIVE).allowed}, {R.ENGINEER})

    def test_the_whole_matrix_is_decided_and_every_decision_names_a_rule(self):
        for role, action, cls in itertools.product(R.ROLES, R.ACTIONS, R.PATH_CLASSES):
            d = check(role, action, cls)
            self.assertTrue(d.rule_id and d.reason)
            self.assertEqual(d.allowed, d.rule_id.startswith("A-"))

    def test_unknown_names_are_denied(self):
        for args in (("root", R.READ, R.SSOT), (R.ENGINEER, "rm", R.SSOT), (R.ENGINEER, R.READ, "etc")):
            self.assertEqual(check(*args).rule_id, "D-98")

    def test_the_role_lists_match_the_prd(self):
        self.assertEqual(set(R.AGENTS), {"orchestrator", "electrical_lv", "calc_check", "documentation", "procurement"})
        self.assertEqual(len(R.ROLES), 7)
        self.assertEqual(len(R.PATH_CLASSES), 10)
        self.assertEqual(len(R.ACTIONS), 7)

    def test_triggers(self):
        self.assertTrue(may_trigger(R.ENGINEER, "approve"))
        self.assertFalse(may_trigger(R.ORCHESTRATOR, "approve"))
        self.assertFalse(may_trigger(R.CALC_CHECK, "start_run"))
        self.assertFalse(may_trigger(R.ENGINEER, "nonsense"))


class EnforceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.log = EventLog.for_project(Path(self._tmp.name) / "P", clock)

    def test_denied_raises_and_is_logged(self):
        with self.assertRaises(PermissionDenied) as cm:
            enforce(R.ELECTRICAL_LV, R.WRITE, R.SSOT, log=self.log, actor_id="e1", run_id="r1", target="ssot/x.json")
        self.assertEqual(cm.exception.decision.rule_id, "D-07")
        rec = self.log.read()[0]
        self.assertEqual((rec["result"], rec["action"], rec["actor"]), ("denied", "write:ssot", {"role": "electrical_lv", "id": "e1"}))
        self.assertEqual(rec["detail"]["rule_id"], "D-07")

    def test_allowed_is_logged_and_returned(self):
        d = enforce(R.ENGINEER, R.SIGN, R.DELIVERABLES, log=self.log)
        self.assertTrue(d.allowed)
        self.assertEqual(self.log.read()[0]["result"], "allowed")

    def test_works_without_a_log(self):
        with self.assertRaises(PermissionDenied):
            enforce(R.PROCUREMENT, R.DELETE, R.REVIEWS)


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.project = self.base / "P"
        for name in R.PROJECT_CLASSES:
            (self.project / (f".epc/{name}" if name in INTERNAL_CLASSES else name)).mkdir(parents=True)
        self.repo = self.base / "repo"
        for rel in ("harness/config/normative/AR", "harness/schemas", "harness/src/x"):
            (self.repo / rel).mkdir(parents=True)

    def test_project_folders_and_root_files(self):
        for cls in R.PROJECT_CLASSES:
            base = f".epc/{cls}" if cls in INTERNAL_CLASSES else cls
            self.assertEqual(classify_path(self.project, f"{base}/a/b.json"), cls)
            self.assertEqual(classify_path(self.project, self.project / base / "z"), cls)
        for name in (".epc/project_profile.json", ".epc/master_project_state.json", ".epc/epc-progress.txt"):
            self.assertEqual(classify_path(self.project, name), R.SSOT)

    def test_repo_paths_need_a_repo_root(self):
        target = self.repo / "harness/config/normative/AR/x.json"
        self.assertEqual(classify_path(self.project, target, repo_root=self.repo), R.CONFIG_NORMATIVE)
        self.assertEqual(classify_path(self.project, self.repo / "harness/schemas/a.json", repo_root=self.repo), R.SCHEMAS)
        self.assertEqual(classify_path(self.project, self.repo / "harness/src/x/a.py", repo_root=self.repo), R.HARNESS_CODE)
        with self.assertRaises(PathError):
            classify_path(self.project, target)
        with self.assertRaises(PathError):
            classify_path(self.project, self.repo / "README.md", repo_root=self.repo)

    def test_escapes_and_unknown_paths_are_refused(self):
        for bad in ("../x", "ssot/../../x", "/etc/passwd", "ssot\\a", "", "unknown/x", "C:\\Windows", "a/./b", self.base / "other" / "x", self.project, "."):
            with self.subTest(bad=str(bad)):
                with self.assertRaises(PathError):
                    classify_path(self.project, bad)

    def test_absolute_path_with_dotdot_that_escapes_is_refused(self):
        with self.assertRaises(PathError):
            classify_path(self.project, str(self.project / ".epc" / "ssot" / ".." / ".." / "x"))
        self.assertEqual(classify_path(self.project, str(self.project / ".epc" / "ssot" / ".." / ".." / "inputs" / "x")), R.INPUTS)

    def test_a_link_inside_the_project_that_leaves_it_is_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        link = self.project / "inputs" / "evil"
        try:
            if os.name == "nt":
                subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True)
            else:
                os.symlink(outside, link)
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("the OS does not allow creating a link here")
        with self.assertRaises(PathError):
            classify_path(self.project, "inputs/evil/x.txt")

    def test_a_link_between_two_project_folders_is_classified_by_its_target(self):
        link = self.project / "inputs" / "to_ssot"
        try:
            if os.name == "nt":
                subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(self.project / ".epc" / "ssot")], check=True, capture_output=True)
            else:
                os.symlink(self.project / ".epc" / "ssot", link)
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("the OS does not allow creating a link here")
        self.assertEqual(classify_path(self.project, "inputs/to_ssot/a.json"), R.SSOT)


if __name__ == "__main__":
    unittest.main()
