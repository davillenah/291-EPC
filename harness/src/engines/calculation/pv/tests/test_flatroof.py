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


class TestCatalogPick(unittest.TestCase):
    def test_the_pick_is_the_closest_ratio_and_the_isc_gap_is_assumed_and_said(self):
        from epc_pv import catalog
        rec = catalog.pick_inverter(40, 670, 1.2)
        n = max(1, round(40 * 670 / (1.2 * rec["inverter"]["pac0_w"])))
        self.assertLess(abs(40 * 670 / (n * rec["inverter"]["pac0_w"]) - 1.2), 0.3)
        self.assertIsNone(catalog.with_isc(rec)["isc_max_input_a"])      # the data sheet gap stays a gap: nothing is invented
        self.assertEqual(catalog.with_isc(rec, 50)["isc_max_input_a"], 50.0)

    def test_a_ground_site_spec_fills_with_a_fixed_tilt_when_given(self):
        layout = {"site": {"width_m": 40, "length_m": 30, "setback_m": 2}, "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02, "table": {"rows": 2, "modules_per_row": 14, "orientation": "portrait"},
                  "table_gap_m": 0.5, "road_width_m": 4, "front_clearance_m": 0.5, "station": {"width_m": 6, "depth_m": 2.5}, "inverter_pad": {"width_m": 0.7, "depth_m": 0.4}}
        array = dict(SPEC["array"], tilt_deg=20, azimuth_deg=0)
        p = flatroof.propose(doc(), flatroof.spec_from_layout(layout, array))
        self.assertEqual((p["tilt_deg"], len(p["options"])), (20.0, 1))
        self.assertTrue(p["assumption"].startswith("ground"))
        capped = flatroof.spec_from_layout(layout, array, 10)
        self.assertEqual(capped["target_modules"], 10)

    def test_a_table_too_big_for_the_site_is_reduced_never_enlarged_and_the_clearance_is_asked(self):
        layout = {"site": {"width_m": 40, "length_m": 30, "setback_m": 5}, "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02, "table": {"rows": 2, "modules_per_row": 28, "orientation": "portrait"},
                  "table_gap_m": 0.5, "road_width_m": 4, "front_clearance_m": 0.5, "station": {"width_m": 6, "depth_m": 2.5}, "inverter_pad": {"width_m": 0.7, "depth_m": 0.4}}
        fitted = flatroof.fit_table(layout)
        self.assertLess(fitted["table"]["modules_per_row"], 28)
        self.assertEqual(fitted["table"]["rows"], 2)
        self.assertGreater(flatroof.propose(doc(), flatroof.spec_from_layout(fitted, dict(SPEC["array"])))["modules"], 0)
        self.assertIs(flatroof.fit_table(fitted), fitted)      # already fits: untouched
        tiny = dict(layout, site={"width_m": 14, "length_m": 8, "setback_m": 1}, table={"rows": 3, "modules_per_row": 4, "orientation": "portrait"})
        self.assertLess(flatroof.fit_table(tiny)["table"]["rows"], 3)
        del layout["front_clearance_m"]
        with self.assertRaises(PvError):
            flatroof.spec_from_layout(layout, dict(SPEC["array"]))


class TestModulePick(unittest.TestCase):
    def test_the_most_total_power_wins_not_the_biggest_module(self):
        from epc_pv import modulepick
        # a toy geometry: the count falls with the module area, so a small module can win on total power
        def count(rec, _o):
            d = rec["dimensions_mm"]
            return int(60.0 / (d[0] * d[1] / 1e6))
        row, rows = modulepick.best(count)
        self.assertEqual(row["dc_kwp"], max(r["dc_kwp"] for r in rows))
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows, sorted(rows, key=lambda r: (-r["dc_kwp"], -r["modules"])))
        self.assertIn("kWp", modulepick.summary(rows))
        self.assertEqual(modulepick.block(row["record"])["id"], row["record"]["id"])
