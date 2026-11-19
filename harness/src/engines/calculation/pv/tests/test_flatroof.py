"""Flat roof: the structure proposed when nothing is known about the roof."""
import copy
import unittest

from epc_pv import PvError, flatroof, plan_layout, run
from test_pv import INVERTER, MODULE, doc

SPEC = {"width_m": 14.0, "length_m": 8.0, "setback_m": 0.6, "walkway_m": 0.8, "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02, "table": {"rows": 1, "modules_per_row": 4, "orientation": "landscape"},
        "table_gap_m": 0.3, "front_clearance_m": 0.3, "station": {"width_m": 1.0, "depth_m": 1.0}, "inverter_pad": {"width_m": 0.7, "depth_m": 0.4}, "array": {"module": dict(MODULE), "inverter": dict(INVERTER), "dc_ac_ratio": 1.1}}


class TestFlatRoof(unittest.TestCase):
    def test_a_steeper_tilt_needs_more_row_pitch_and_holds_fewer_tables(self):
        low, steep = flatroof.capacity(SPEC, 5, 30.0), flatroof.capacity(SPEC, 40, 30.0)
        self.assertGreater(steep["pitch_m"], low["pitch_m"])
        self.assertGreaterEqual(low["tables"], steep["tables"])
        self.assertEqual(low["modules"], low["tables"] * 4)

    def test_the_proposal_keeps_the_assumption_the_tilt_and_the_schedule(self):
        p = flatroof.propose(doc(), copy.deepcopy(SPEC))
        self.assertEqual(p["assumption"], "flat roof, tilted frames facing the equator")
        self.assertEqual(p["azimuth_deg"], 0.0)
        self.assertIn(p["tilt_deg"], flatroof.TILTS_DEG)
        s = p["structure"]
        self.assertEqual((s["frames"] * s["modules_per_frame"], s["tilt_deg"]), (p["capacity_modules"], p["tilt_deg"]))
        self.assertGreater(s["rear_height_m"], s["front_height_m"])
        self.assertTrue(s["not_calculated"]["en"] and s["not_calculated"]["es"])
        self.assertEqual(len(p["options"]), len(flatroof.TILTS_DEG))

    def test_the_best_tilt_is_the_one_with_most_energy_from_the_roof(self):
        p = flatroof.propose(doc(), copy.deepcopy(SPEC))
        energy = lambda o: o["modules"] * o["specific_yield_kwh_kwp"]      # noqa: E731
        self.assertEqual(max(energy(o) for o in p["options"]), energy(next(o for o in p["options"] if o["tilt_deg"] == p["tilt_deg"])))

    def test_a_target_is_kept_when_the_roof_holds_it_and_said_when_it_does_not(self):
        spec = copy.deepcopy(SPEC)
        spec["target_modules"] = 4
        p = flatroof.propose(doc(), spec)
        self.assertEqual((p["modules"], p["fits"]), (4, True))
        spec["target_modules"] = 500
        p = flatroof.propose(doc(), spec)
        self.assertFalse(p["fits"])
        self.assertEqual(p["warnings"][0]["code"], "roof_short")
        self.assertEqual(p["modules"], p["capacity_modules"])

    def test_the_layout_is_the_input_of_the_plan_and_the_plant_fits(self):
        d = doc()
        spec = copy.deepcopy(SPEC)
        spec["target_modules"] = 8
        p = flatroof.propose(d, spec)
        d["arrays"] = [dict(spec["array"], id="A1", tilt_deg=p["tilt_deg"], azimuth_deg=p["azimuth_deg"], n_modules=p["modules"])]
        geometry = plan_layout(d, run(d).as_dict(), p["layout"])
        self.assertGreater(geometry["counts"]["tables"], 0)

    def test_wrong_input_is_refused_in_both_languages(self):
        for bad in ({}, {"width_m": 0}, {"table": {"rows": 1}}):
            with self.assertRaises(PvError) as ctx:
                flatroof.propose(doc(), dict(copy.deepcopy(SPEC), **bad) if bad else {})
            self.assertTrue(ctx.exception.es)

    def test_a_roof_smaller_than_one_frame_holds_nothing(self):
        spec = dict(copy.deepcopy(SPEC), width_m=2.0, length_m=1.0)
        self.assertEqual(flatroof.propose(doc(), spec)["capacity_modules"], 0)


if __name__ == "__main__":
    unittest.main()
