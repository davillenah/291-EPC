"""Where the data of the norm lives: inside the engine package, so it travels with it."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_aea90364 import aea_rules, aea_tables, norm_data   # noqa: E402


class TestNormData(unittest.TestCase):
    def test_the_norm_data_is_in_the_normative_folder_and_the_review_state_stays_in_the_package(self):
        import epc_aea90364
        pkg = Path(epc_aea90364.__file__).resolve().parent                # the review state stays with the AEA 90364 package (norm_data itself is in epc_calc_common since MIG-37b)
        folder = norm_data.normative_dir().resolve()
        for f in (norm_data.criteria_file("electrical"), Path(aea_tables.RUTA_JSON), Path(aea_rules.CARPETA)):
            self.assertTrue(f.exists(), f)
            self.assertIn(folder, f.resolve().parents)                    # norm data lies in harness/config/normative/AR/electrical/aea90364
        for f in (norm_data.REVIEW, norm_data.REVIEW_LOG):
            self.assertTrue(f.exists(), f)
            self.assertIn(pkg, f.resolve().parents)                       # the owner's review state is not norm data
        self.assertEqual(norm_data.criteria_file("electrical").parent, folder)

    def test_a_discipline_the_norm_has_no_catalog_for_gets_none(self):
        self.assertIsNone(norm_data.criteria_file("hvac"))

    def test_the_catalog_lists_criteria_with_a_default_inside_their_limits(self):
        import json
        cat = json.loads(norm_data.criteria_file("electrical").read_text(encoding="utf-8-sig"))
        self.assertTrue(cat["criteria"])
        for c in cat["criteria"]:
            if c["type"] == "number":
                self.assertTrue(c.get("min", float("-inf")) <= c["default"] <= c.get("max", float("inf")), c["id"])
            else:
                self.assertIn(c["default"], c["options"], c["id"])


if __name__ == "__main__":
    unittest.main()
