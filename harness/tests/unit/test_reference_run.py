"""GEN-02, OPT-14: the comparison of two reference reports ignores times and names what really changed."""
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("reference_run", Path(__file__).resolve().parents[2] / "tools" / "ci" / "reference_run.py")
RR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RR)

BASE = {"exit_code": 0, "stages": [{"stage": 1, "status": "ok"}], "findings": 6, "files": ["a.pdf"], "seconds": 1.0}


class Compare(unittest.TestCase):
    def test_times_never_count(self):
        self.assertEqual(RR.compare(BASE, dict(BASE, seconds=99.0, stage_seconds={"x": 5})), [])

    def test_a_changed_status_a_finding_and_a_file_are_named(self):
        new = dict(BASE, stages=[{"stage": 1, "status": "blocked"}], findings=7, files=["b.pdf"])
        text = " | ".join(RR.compare(BASE, new))
        for part in ("stage statuses differ", "findings 6 -> 7", "no longer delivered: a.pdf", "new file delivered: b.pdf"):
            self.assertIn(part, text)


if __name__ == "__main__":
    unittest.main()
