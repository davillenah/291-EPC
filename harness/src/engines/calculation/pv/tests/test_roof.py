"""Roof layout and the orientation the engine chooses."""
import copy
import unittest

from epc_pv import PvError, orient, plan_roof, run
from test_pv import INVERTER, MODULE, doc

ARRAY = {"module": dict(MODULE), "inverter": dict(INVERTER), "dc_ac_ratio": 1.1}


def roof(**changes):
    r = {"planes": [{"id": "N1", "width_m": 10.0, "slope_m": 5.0, "tilt_deg": 25, "azimuth_deg": 0, "setback_m": 0.5, "obstacles": []}], "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02,
         "array": copy.deepcopy(ARRAY)}
    r.update(changes)
    return r


class TestRoof(unittest.TestCase):
    def test_the_modules_fill_the_usable_area_on_the_better_orientation(self):
        p = plan_roof(roof())["planes"][0]
        self.assertEqual(p["orientation"], "landscape")      # 9 m x 4 m usable: 3 columns x 3 rows of 2.278 x 1.134 beats portrait
        self.assertEqual(p["capacity"], 9)
        self.assertEqual(p["modules"], 9)
        for c in p["cells"]:
            self.assertGreaterEqual(c["x"], 0.5 - 1e-9)
            self.assertLessEqual(c["x"] + p["module"]["width_m"], 9.5 + 1e-9)
            self.assertLessEqual(c["y"] + p["module"]["depth_m"], 4.5 + 1e-9)

    def test_an_obstacle_removes_the_cells_it_touches_and_never_overlaps_a_module(self):
        r = copy.deepcopy(roof())
        free = plan_roof(r)["counts"]["capacity"]
        r["planes"][0]["obstacles"] = [{"x": 4.0, "y": 2.0, "width_m": 1.0, "depth_m": 1.0}]
        got = plan_roof(r)["planes"][0]
        self.assertLess(got["capacity"], free)
        for c in got["cells"]:
            m = got["module"]
            self.assertFalse(c["x"] < 5.0 and 4.0 < c["x"] + m["width_m"] and c["y"] < 3.0 and 2.0 < c["y"] + m["depth_m"])

    def test_the_target_is_filled_from_the_eave_and_a_short_roof_is_said(self):
        r = roof(target_modules=5)
        got = plan_roof(r)
        self.assertEqual((got["counts"]["modules"], got["fits"]), (5, True))
        self.assertEqual({c["row"] for c in got["planes"][0]["cells"]}, {1, 2})
        short = plan_roof(roof(target_modules=40))
        self.assertEqual((short["fits"], short["counts"]["short"], short["warnings"][0]["code"]), (False, 31, "roof_short"))
        self.assertTrue(short["warnings"][0]["es"])

    def test_one_array_per_plane_with_the_plane_orientation(self):
        r = roof()
        r["planes"].append({"id": "E1", "width_m": 6.0, "slope_m": 4.0, "tilt_deg": 20, "azimuth_deg": 90, "setback_m": 0.5})
        arrays = plan_roof(r)["arrays"]
        self.assertEqual([(a["id"], a["tilt_deg"], a["azimuth_deg"]) for a in arrays], [("N1", 25, 0), ("E1", 20, 90)])
        self.assertTrue(all(a["module"] == MODULE for a in arrays))

    def test_a_plane_too_small_gives_no_array_and_wrong_input_is_refused_in_both_languages(self):
        self.assertEqual(plan_roof(roof(planes=[{"id": "S", "width_m": 1.0, "slope_m": 1.0, "tilt_deg": 10, "azimuth_deg": 0, "setback_m": 0.5}]))["arrays"], [])
        for bad in ({"planes": []}, {"module_gap_m": -1}, {"target_modules": 0}, {"planes": [{"id": "x"}]}):
            with self.assertRaises(PvError) as ctx:
                plan_roof(roof(**bad))
            self.assertTrue(ctx.exception.es)
        with self.assertRaises(PvError):
            plan_roof({})

    def test_the_planned_arrays_run_in_the_yield_engine(self):
        d = doc()
        d["arrays"] = plan_roof(roof())["arrays"]
        self.assertGreater(run(d).as_dict()["totals"]["dc_kwp"], 0)


class TestOrientation(unittest.TestCase):
    def test_the_azimuth_faces_the_equator(self):
        self.assertEqual((orient.equator_azimuth_deg(-34.6), orient.equator_azimuth_deg(40.0)), (0.0, 180.0))

    def test_the_modules_for_a_power_are_whole_and_reach_it(self):
        self.assertEqual(orient.modules_for_kwp(560, 560), 1000)
        self.assertEqual(orient.modules_for_kwp(1, 550), 2)
        self.assertEqual(orient.modules_for_kwp(0.0001, 550), 1)

    def test_the_best_tilt_is_found_by_the_yield_engine_and_is_repeatable(self):
        d = doc()
        got = orient.optimal(d)
        self.assertEqual(got["azimuth_deg"], 0.0)
        self.assertTrue(0 <= got["tilt_deg"] <= 60)
        self.assertEqual(got, orient.optimal(d))
        flat = orient._yield(d, 0, 0.0)
        self.assertGreaterEqual(got["specific_yield_kwh_kwp"], flat)


if __name__ == "__main__":
    unittest.main()
