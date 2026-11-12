"""MIG-44p: the dry-run report harness/docs/validation/SPIKE_DRY_RUN.md is up to date (stale report = failing test).

`--check` runs the whole synthetic project (about half a minute), so this is the slow test of the folder.
"""
import subprocess
import sys
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "tools" / "build" / "spike_dry_run.py"


class DryRunReportIsFresh(unittest.TestCase):
    def test_check_passes(self):
        done = subprocess.run([sys.executable, str(TOOL), "--check"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
