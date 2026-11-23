"""COD-16: every GitHub workflow file is valid YAML with jobs and steps. A workflow that does not parse runs no CI at all, and GitHub only says so on its site.
Run: python -m unittest discover -s harness/tests/architecture
"""
import unittest
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parents[3] / ".github" / "workflows"


class WorkflowsParse(unittest.TestCase):
    def test_there_are_workflows(self):
        self.assertTrue(sorted(WORKFLOWS.glob("*.yml")))

    def test_every_workflow_parses_and_has_jobs_with_steps(self):
        for path in sorted(WORKFLOWS.glob("*.yml")):
            with self.subTest(workflow=path.name):
                doc = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertIsInstance(doc, dict)
                self.assertTrue(doc.get("jobs"), "no jobs")
                for name, job in doc["jobs"].items():
                    self.assertTrue(job.get("steps"), f"job {name} has no steps")
                    for step in job["steps"]:
                        self.assertIsInstance(step.get("name", ""), str, f"job {name}: a step name is not text")

    def test_the_rule_sees_the_error_of_2026_11_23(self):
        with self.assertRaises(yaml.YAMLError):
            yaml.safe_load("steps:\n  - name: Gate (full battery: pushes)\n    run: x\n")


if __name__ == "__main__":
    unittest.main()
