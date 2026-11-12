"""Tests of harness/tools/build/review_list.py: the file is generated from the engines' data (no web backend since MIG-38b).

  python -m pytest harness/tools/build/tests/test_review_list.py     (engines and harness/src on PYTHONPATH, as in the gate)
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "harness" / "tools" / "build"))
import review_list as rl  # noqa: E402


class ReviewList(unittest.TestCase):
    def test_comment_text_strips_hash_on_python_310(self):
        self.assertEqual(rl._comment_text("#  [VERIFICAR] x"), "[VERIFICAR] x")

    def test_the_units_come_from_the_engines_without_the_backend(self):
        units = rl._norm_units()
        self.assertGreaterEqual(len(units), 15)
        self.assertNotIn("epc.modules.norms", sys.modules)
        for name, total, pending in units:
            self.assertTrue(name)
            self.assertTrue(0 <= pending <= total)

    def test_the_text_lists_every_unit_and_the_pending_total(self):
        text = rl.text()
        units = rl._norm_units()
        self.assertIn(f"Pendientes: **{sum(p for _, _, p in units)}**", text)
        for name, total, pending in units:
            self.assertIn(f"| {name} | {total} | {pending} |", text)

    def test_the_committed_file_is_up_to_date(self):
        self.assertEqual(rl.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
