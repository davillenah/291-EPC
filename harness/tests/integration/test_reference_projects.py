"""GEN-02: the fictional reference projects (office floor, dwelling, shed, photovoltaic plant) each run the whole pipeline to the end, and the PV one carries its plant."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic_lv as S   # noqa: E402

PROJECTS = ("synthetic_lv_small", "reference_dwelling", "reference_shed", "reference_pv_plant")
FOLDERS = S.REPO / "harness" / "tests" / "golden_projects"


class ReferenceProjects(unittest.TestCase):
    def test_each_project_has_the_four_input_files_and_only_fictional_names(self):
        for name in PROJECTS:
            with self.subTest(project=name):
                for file in ("intake_answers.json", "loads.json", "engine_inputs.json"):
                    self.assertTrue((FOLDERS / name / file).is_file(), file)
                answers = json.loads((FOLDERS / name / "intake_answers.json").read_text(encoding="utf-8"))
                self.assertRegex(answers["client"]["name"] + answers["site"]["address"] + answers["supply"]["source"], r"(?i)invented|fictional|synthetic")

    def test_each_project_runs_every_stage_to_the_end(self):
        for name in PROJECTS:
            with self.subTest(project=name):
                run = S.SyntheticRun(drawing_date="2026-03-04", folder=FOLDERS / name)
                self.addCleanup(run.cleanup)
                run.init()
                code, answer = run.run()
                self.assertEqual(code, 0, answer)
                stages = run.ssot("../master_project_state.json")["stages"]
                self.assertEqual([e["status"] for e in stages], ["ok"] * 12)

    def test_the_pv_plant_gives_a_pv_result_in_stage_three(self):
        run = S.SyntheticRun(drawing_date="2026-03-04", folder=FOLDERS / "reference_pv_plant")
        self.addCleanup(run.cleanup)
        run.init()
        run.run()
        stage = next(p for p in run.stage_files() if p.name.startswith("stage_03"))
        self.assertIn("pv", S.read_json(stage)["outputs"])


if __name__ == "__main__":
    unittest.main()
