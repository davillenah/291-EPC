"""Tests of harness/tools/ci/harness_metrics.py (PRO-13) on an invented projects folder."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ci"))
import harness_metrics as hm  # noqa: E402


def _project(root, name, statuses, seconds):
    epc = Path(root) / name / ".epc"
    (epc / "runs" / "run-1").mkdir(parents=True)
    (epc / "master_project_state.json").write_text(json.dumps({"stages": [{"number": n, "slug": f"s{n}", "status": s} for n, s in enumerate(statuses, 1)]}), encoding="utf-8")
    (epc / "runs" / "run-1" / "stage_timings.json").write_text(json.dumps({"stages": [{"stage": n, "slug": f"s{n}", "seconds": t} for n, t in enumerate(seconds, 1)]}), encoding="utf-8")


class HarnessMetrics(unittest.TestCase):
    def test_counts_projects_runs_failures_and_times(self):
        with tempfile.TemporaryDirectory() as root:
            _project(root, "A", ["ok", "error"], [1.0, 3.0])
            _project(root, "B", ["ok", "not_available"], [3.0, 5.0])
            m = hm.collect(root)
            self.assertEqual((m["projects"], m["runs"], m["runs_with_timings"]), (2, 2, 2))
            first, second = m["stages"]
            self.assertEqual((first["failed"], first["mean_seconds"], first["max_seconds"]), (0, 2.0, 3.0))
            self.assertEqual((second["failed"], second["mean_seconds"], second["max_seconds"]), (1, 4.0, 5.0))
            self.assertIn("projects: 2", hm.render(m))

    def test_an_empty_or_unreadable_project_does_not_break_it(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "X" / ".epc").mkdir(parents=True)
            (Path(root) / "X" / ".epc" / "master_project_state.json").write_text("not json", encoding="utf-8")
            self.assertEqual(hm.collect(root), {"projects": 1, "runs": 0, "runs_with_timings": 0, "stages": []})

    def test_a_missing_folder_exits_with_2(self):
        self.assertEqual(hm.main(["--root", "/no/such/folder"]), 2)


if __name__ == "__main__":
    unittest.main()
