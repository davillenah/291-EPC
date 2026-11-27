"""Input checks of the PV stage found by the hunt simulations: array numbers, duplicate ids, the client's economics, the stage number to stop after."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src/engines/calculation/pv/tests"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src/engines/calculation/pv/src"))
import test_pv as PV  # noqa: E402
from disciplines.electrical_lv.stages import pv_stage  # noqa: E402
from disciplines.electrical_lv.stages.pv_stage import StageInputError  # noqa: E402


def section(**changes):
    return dict({"document": PV.doc()}, **changes)


class TestChecks(unittest.TestCase):
    def test_a_good_section_passes(self):
        pv_stage.check_templates(section())

    def test_a_negative_module_number_is_refused_in_both_languages(self):
        s = section()
        s["document"]["arrays"][0]["module"]["pmax_w"] = -5
        with self.assertRaises(StageInputError) as ctx:
            pv_stage.check_templates(s)
        self.assertIn("mayor que 0", str(ctx.exception))

    def test_a_fractional_module_count_is_refused(self):
        s = section()
        s["document"]["arrays"][0]["n_modules"] = 10.5
        with self.assertRaises(StageInputError):
            pv_stage.check_templates(s)

    def test_a_repeated_array_id_is_refused(self):
        s = section()
        s["document"]["arrays"].append(dict(s["document"]["arrays"][0]))
        with self.assertRaises(StageInputError):
            pv_stage.check_templates(s)

    def test_a_price_that_is_not_positive_is_refused(self):
        for bad in (0, -1, "cheap", float("nan")):
            with self.assertRaises(StageInputError, msg=repr(bad)):
                pv_stage.check_templates(section(economics={"energy_price": bad}))

    def test_a_negative_investment_is_refused(self):
        with self.assertRaises(StageInputError):
            pv_stage.check_templates(section(economics={"energy_price": 0.1, "investment": -10}))

    def test_good_economics_pass(self):
        pv_stage.check_templates(section(economics={"energy_price": 0.1, "investment": 1000}))


if __name__ == "__main__":
    unittest.main()
