"""Horizontal single-axis tracker: rotation angle, backtracking, the plane it gives and its place in the pipeline."""
import unittest

from epc_pv import PvError, run, tracker

from test_pv import doc

NS = {"axis_azimuth_deg": 0.0, "max_angle_deg": 60.0, "backtracking": False, "gcr": None}      # axis north-south: the plane turns east to west


class TestRotation(unittest.TestCase):
    def test_the_sun_over_the_axis_gives_no_rotation(self):
        self.assertAlmostEqual(tracker.rotation_deg(50.0, 0.0, NS), 0.0)           # due north, in the plane of the axis
        self.assertAlmostEqual(tracker.rotation_deg(50.0, 180.0, NS), 0.0)

    def test_the_morning_sun_turns_the_plane_east_and_the_afternoon_sun_west(self):
        east, west = tracker.rotation_deg(30.0, 90.0, NS), tracker.rotation_deg(30.0, 270.0, NS)
        self.assertGreater(east, 0.0)
        self.assertAlmostEqual(east, -west)
        self.assertEqual(tracker.surface(east, 0.0), (east, 90.0))
        self.assertEqual(tracker.surface(west, 0.0), (-west, 270.0))

    def test_a_sun_on_the_horizon_east_gives_ninety_before_the_limit(self):
        free = dict(NS, max_angle_deg=90.0)
        self.assertAlmostEqual(tracker.rotation_deg(0.5, 90.0, free), 89.5, places=1)

    def test_the_angle_is_clipped(self):
        self.assertAlmostEqual(tracker.rotation_deg(5.0, 90.0, NS), 60.0)

    def test_the_sun_below_the_horizon_gives_zero(self):
        self.assertEqual(tracker.rotation_deg(-3.0, 90.0, NS), 0.0)

    def test_backtracking_eases_the_angle_and_never_exceeds_the_ideal(self):
        free, back = dict(NS, max_angle_deg=90.0), dict(NS, max_angle_deg=90.0, backtracking=True, gcr=0.4)
        ideal, eased = tracker.rotation_deg(10.0, 90.0, free), tracker.rotation_deg(10.0, 90.0, back)
        self.assertGreater(ideal, eased)
        self.assertGreaterEqual(eased, 0.0)
        self.assertAlmostEqual(tracker.rotation_deg(80.0, 90.0, back), tracker.rotation_deg(80.0, 90.0, free), places=6)       # a high sun needs no backtracking

    def test_bad_blocks_are_errors_in_both_languages(self):
        for bad in ("x", {"axis_azimuth_deg": 0}, {"axis_azimuth_deg": 400, "max_angle_deg": 60, "backtracking": False},
                    {"axis_azimuth_deg": 0, "max_angle_deg": 60}, {"axis_azimuth_deg": 0, "max_angle_deg": 60, "gcr": 2}):
            with self.assertRaises(PvError) as ctx:
                tracker.check(bad, "arrays[0].tracker")
            self.assertTrue(ctx.exception.en and ctx.exception.es)


class TestPipeline(unittest.TestCase):
    TRACKER = {"axis_azimuth_deg": 0, "max_angle_deg": 60, "backtracking": True, "gcr": 0.4}

    def run_with(self, **array):
        d = doc(**array)
        for key in ("tilt_deg", "azimuth_deg"):
            d["arrays"][0].pop(key, None)
        return run(d)

    def test_a_tracker_array_needs_no_fixed_plane_and_collects_more_than_a_fixed_one(self):
        fixed = run(doc(tilt_deg=0, azimuth_deg=0))
        tracked = self.run_with(tracker=self.TRACKER)
        self.assertGreater(tracked.arrays[0]["poa_kwh_m2"], fixed.arrays[0]["poa_kwh_m2"])

    def test_the_caller_document_is_not_changed(self):
        d = doc(tracker=dict(self.TRACKER))
        before = repr(d)
        run(d)
        self.assertEqual(repr(d), before)

    def test_row_or_near_shade_with_a_tracker_is_an_error(self):
        with self.assertRaises(PvError) as ctx:
            run(doc(tracker=self.TRACKER, row_shading={"slope_m": 2.0, "pitch_m": 5.0, "n_rows": 3}))
        self.assertEqual(ctx.exception.code, "err_tracker_shade")
        self.assertTrue(ctx.exception.es)


if __name__ == "__main__":
    unittest.main()
