"""MIG-42p: the owner templates in harness/docs/validation/ are up to date with the norm register (stale workbook = failing test)."""
import subprocess
import sys
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "tools" / "build" / "validation_templates.py"


class TemplatesAreFresh(unittest.TestCase):
    def test_check_passes(self):
        done = subprocess.run([sys.executable, str(TOOL), "--check"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
