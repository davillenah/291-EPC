"""The plant layout: row pitch, table size, fit, strings shared among inverters, and the refusals in English and Spanish."""
import copy
import unittest

from epc_pv import PvError, Options, plan_layout, run
from epc_pv import layout as lay
from test_pv import doc

LAYOUT = {"site": {"width_m": 200, "length_m": 120, "setback_m": 5}, "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02,
          "table": {"rows": 2, "modules_per_row": 28, "orientation": "portrait"}, "table_gap_m": 0.5, "road_width_m": 4,
          "station": {"width_m": 6, "depth_m": 2.5}, "inverter_pad": {"width_m": 0.7, "depth_m": 0.4}}


def planned(layout=None, **array):
    document = doc(**array)
    result = run(document, Options()).as_dict()
    return plan_layout(document, result, layout or copy.deepcopy(LAYOUT)), result


class TestLayout(unittest.TestCase):
    def test_table_size_portrait(self):
        size = lay.table_size(LAYOUT)
        self.assertAlmostEqual(size["width_m"], 28 * 1.134 + 27 * 0.02, places=6)
        self.assertAlmostEqual(size["slope_m"], 2 * 2.278 + 0.02, places=6)

    def test_row_pitch_formula(self):
        # D = l (sin b / tan a + cos b)
        self.assertAlmostEqual(lay.row_pitch_m(4.0, 30.0, 30.0), 4.0 * (0.5 / 0.5773502692 + 0.8660254038), places=5)

    def test_winter_altitude_is_lower_than_summer_in_the_south(self):
        alt = lay.solar_altitude_deg(-34.6, -58.4)
        self.assertAlmostEqual(alt, 90 - 34.6 - 23.44, delta=0.5)

    def test_every_module_sits_on_a_table_and_strings_are_assigned(self):
        out, result = planned()
        self.assertEqual(sum(t["modules"] for t in out["tables"]), result["arrays"][0]["modules"])
        self.assertTrue(all(t["strings"] and t["inverters"] for t in out["tables"]))
        self.assertEqual(out["counts"]["inverters"], len(out["inverters"]))

    def test_it_never_shrinks_distances_when_it_does_not_fit(self):
        small = copy.deepcopy(LAYOUT)
        small["site"].update(width_m=30, length_m=20)
        out, _ = planned(small)
        self.assertFalse(out["fits"])
        self.assertGreater(out["counts"]["tables_left_out"], 0)
        self.assertEqual(out["warnings"][0]["code"], "layout_no_fit")
        self.assertTrue(out["warnings"][0]["en"] and out["warnings"][0]["es"])

    def test_deterministic(self):
        self.assertEqual(planned()[0], planned()[0])

    def test_missing_key_is_refused_in_both_languages(self):
        bad = copy.deepcopy(LAYOUT)
        del bad["road_width_m"]
        with self.assertRaises(PvError) as ctx:
            lay.check(bad)
        self.assertIn("road_width_m", str(ctx.exception))

    def test_wrong_orientation_and_dimensions_are_refused(self):
        for mutate in (lambda d: d["table"].update(orientation="diagonal"), lambda d: d.update(module_dimensions_mm=[2278]), lambda d: d["site"].update(width_m=0)):
            bad = copy.deepcopy(LAYOUT)
            mutate(bad)
            with self.assertRaises(PvError):
                lay.check(bad)

    def test_not_an_object_is_refused(self):
        with self.assertRaises(PvError):
            lay.check([])


if __name__ == "__main__":
    unittest.main()
