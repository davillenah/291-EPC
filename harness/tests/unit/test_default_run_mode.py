"""ADR-0035: the default mode of a run (`epc run` without --mode). An explicit mode wins; then EPC_RUN_MODE; then harness/config/default_run_mode; a missing or wrong file falls back to production."""
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "ci"))
import check_default_run_mode as CHK  # noqa: E402
import test_platform_api as A  # noqa: E402
import test_run_modes as RM  # noqa: E402
from disciplines.electrical_lv import run_mode  # noqa: E402
from epc_platform import api  # noqa: E402
from epc_platform.cli.main import main  # noqa: E402

REPO_FILE = Path(__file__).resolve().parents[2] / "config" / "default_run_mode"


def without_env():
    return mock.patch.dict(os.environ, {}, clear=False)


class Resolution(unittest.TestCase):
    def file(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "default_run_mode"
        if text is not None:
            path.write_text(text, encoding="utf-8")
        return path

    def test_the_file_decides_when_nothing_is_pinned(self):
        self.assertEqual(run_mode.default_mode({}, self.file("edit\n")), "edit")
        self.assertEqual(run_mode.default_mode({}, self.file("production\n")), "production")

    def test_the_environment_wins_over_the_file(self):
        self.assertEqual(run_mode.default_mode({"EPC_RUN_MODE": "production"}, self.file("edit\n")), "production")
        self.assertEqual(run_mode.default_mode({"EPC_RUN_MODE": "edit"}, self.file("production\n")), "edit")

    def test_a_missing_or_wrong_file_and_a_wrong_variable_fall_back_to_production(self):
        self.assertEqual(run_mode.default_mode({}, self.file(None)), "production")
        self.assertEqual(run_mode.default_mode({}, self.file("sandbox\n")), "production")
        self.assertEqual(run_mode.default_mode({"EPC_RUN_MODE": "sandbox"}, self.file("edit\n")), "edit")        # a wrong pin is ignored, the file decides

    def test_the_versioned_file_says_a_mode(self):
        self.assertIn(REPO_FILE.read_text(encoding="utf-8").strip(), run_mode.MODES)

    def test_the_suite_runs_in_production_unless_a_test_asks_otherwise(self):
        self.assertEqual(os.environ.get("EPC_RUN_MODE"), "production")


class TheGateCheck(unittest.TestCase):
    def test_edit_is_refused_on_main_on_a_release_and_on_a_pull_request_to_main(self):
        for branch, env in (("main", {}), ("dev", {"EPC_RELEASE": "1"}), ("feat/x", {"GITHUB_BASE_REF": "main"}), ("", {"GITHUB_REF": "refs/heads/main"})):
            with self.subTest(branch=branch, env=env):
                self.assertTrue(CHK.problems("edit", branch, env))

    def test_edit_is_allowed_on_dev_and_work_branches_and_production_everywhere(self):
        for branch in ("dev", "feat/modo-por-defecto", ""):
            self.assertEqual(CHK.problems("edit", branch, {}), [])
        for branch, env in (("main", {}), ("dev", {"EPC_RELEASE": "1"}), ("dev", {})):
            self.assertEqual(CHK.problems("production", branch, env), [])

    def test_a_value_that_is_not_a_mode_is_an_error_everywhere(self):
        for value in (None, "", "sandbox"):
            self.assertTrue(CHK.problems(value, "dev", {}))


class TheDefaultReachesTheRun(RM.Base):
    def test_a_run_without_a_mode_takes_the_default_and_an_explicit_mode_wins(self):
        with mock.patch.dict(os.environ, {"EPC_RUN_MODE": "edit"}):
            res = self.run_it()
        self.assertEqual((res["ok"], res["data"].get("mode")), (True, "edit"))
        self.assertEqual(self.manifest()["mode"], "edit")
        with self.store.pipeline_session("seed") as token:
            self.store.write_workflow(token, {"state": "corrected", "history": []})
        with mock.patch.dict(os.environ, {"EPC_RUN_MODE": "edit"}):
            explicit = self.run_it(mode="production", revision="R1")
        self.assertNotIn("mode", explicit["data"])

    def test_the_cli_without_the_flag_takes_the_default_and_the_flag_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api.init_project(root, "API-1", A.ANSWERS, clock=A.CLOCK, actor=A.ORC)
            (root / "loads.json").write_text(json.dumps(RM.loads()), encoding="utf-8")
            (root / "inputs.json").write_text(json.dumps(RM.inputs()), encoding="utf-8")
            args = ["--projects-root", str(root), "run", "API-1", "--loads", str(root / "loads.json"), "--engine-inputs", str(root / "inputs.json"), "--stop-after", "3", "--json"]
            env = {"EPC_ACTOR_ROLE": "orchestrator", "EPC_ACTOR_ID": "o1"}
            with mock.patch.dict(os.environ, {"EPC_RUN_MODE": "edit"}):
                out, err = io.StringIO(), io.StringIO()
                main(args, stdout=out, stderr=err, env=env)
                self.assertEqual(json.loads(out.getvalue() or err.getvalue())["data"].get("mode"), "edit")
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.dict(os.environ, {"EPC_RUN_MODE": "edit"}):
                main(args[:-1] + ["--mode", "production", "--json"], stdout=out, stderr=err, env=env)
            self.assertNotIn("mode", json.loads(out.getvalue() or err.getvalue())["data"])


if __name__ == "__main__":
    unittest.main()
