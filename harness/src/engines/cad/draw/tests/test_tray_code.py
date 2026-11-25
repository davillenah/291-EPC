"""The own, maker-free names of the tray models (epc_plan.tray_code)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from epc_draw.plan import tray_code   # noqa: E402
from epc_draw.plan import PlanError   # noqa: E402


class TestTrayCode(unittest.TestCase):
    def test_codes_follow_prefix_kind_fitting_size(self):
        self.assertEqual(tray_code.code("escalera", 300, 90), "BN-ESC-300x90")
        self.assertEqual(tray_code.code("perforada", 200, 60, "elbow90"), "BN-PER-C90-200x60")

    def test_fittings_of_parts(self):
        self.assertEqual(tray_code.fitting_of("elbow", 45), "elbow45")
        self.assertEqual(tray_code.fitting_of("elbow", 90), "elbow90")
        self.assertEqual(tray_code.fitting_of("tee"), "tee")
        self.assertIsNone(tray_code.fitting_of("bracket"))

    def test_names_are_bilingual_and_free_of_makers(self):
        n = tray_code.name("escalera", "tee")
        self.assertTrue(n["en"] and n["es"])
        text = Path(tray_code.__file__).with_name("tray_names.json").read_text(encoding="utf-8").lower()
        for maker in ("samet", "smarttray", "pptres"):
            self.assertNotIn(maker, text)

    def test_unknown_kind_is_an_error(self):
        with self.assertRaises(PlanError):
            tray_code.code("x", 1, 1)


if __name__ == "__main__":
    unittest.main()
