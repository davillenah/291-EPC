"""Shading of the direct beam: the far horizon and the row-to-row shade (pure geometry), and their place in the pipeline."""
import unittest

from epc_pv import PvError, nearshade, run, shading

from test_pv import doc

HILL = [{"azimuth_deg": 0, "elevation_deg": 10}, {"azimuth_deg": 180, "elevation_deg": 30}]


class TestHorizon(unittest.TestCase):
    def test_points_are_joined_in_a_straight_line_around_the_circle(self):
        pts = shading.horizon_points(HILL, "h")
        self.assertAlmostEqual(shading.horizon_elevation_deg(pts, 90), 20.0)
        self.assertAlmostEqual(shading.horizon_elevation_deg(pts, 270), 20.0)       # back to the first point across north
        self.assertAlmostEqual(shading.horizon_elevation_deg(pts, 0), 10.0)

    def test_one_point_is_a_flat_horizon(self):
        self.assertEqual(shading.horizon_elevation_deg(shading.horizon_points([{"azimuth_deg": 40, "elevation_deg": 5}], "h"), 200), 5.0)

    def test_a_bad_profile_is_an_error_in_both_languages(self):
        for bad in ([], [{"azimuth_deg": 0}], [{"azimuth_deg": 0, "elevation_deg": 95}]):
            with self.assertRaises(PvError) as ctx:
                shading.horizon_points(bad, "site.horizon")
            self.assertTrue(ctx.exception.en and ctx.exception.es)

    def test_the_sun_below_the_horizon_gives_no_direct_beam(self):
        pts = shading.horizon_points(HILL, "h")
        self.assertEqual(shading.direct_factor(15, 90, 30, 0, horizon=pts), 0.0)       # horizon 20 at azimuth 90
        self.assertEqual(shading.direct_factor(25, 90, 30, 0, horizon=pts), 1.0)


class TestRows(unittest.TestCase):
    def test_a_high_sun_shades_nothing_and_a_low_one_shades_part_of_the_row(self):
        far = shading.row_shaded_fraction(2.0, 6.0, 30, 0, 80, 0)
        low = shading.row_shaded_fraction(2.0, 4.0, 30, 0, 12, 0)
        self.assertEqual(far, 0.0)
        self.assertGreater(low, 0.0)
        self.assertLessEqual(low, 1.0)

    def test_the_design_pitch_leaves_the_design_hour_unshaded(self):
        from epc_pv import layout
        altitude = 20.0
        pitch = layout.row_pitch_m(2.0, 30, altitude)
        self.assertAlmostEqual(shading.row_shaded_fraction(2.0, pitch, 30, 0, altitude, 0), 0.0, places=6)
        self.assertGreater(shading.row_shaded_fraction(2.0, pitch, 30, 0, altitude - 3, 0), 0.0)

    def test_a_sun_behind_the_surface_shades_no_row(self):
        self.assertEqual(shading.row_shaded_fraction(2.0, 3.0, 30, 0, 10, 180), 0.0)

    def test_the_front_row_is_never_shaded(self):
        rows = {"slope_m": 2.0, "pitch_m": 3.0, "n_rows": 1}
        self.assertEqual(shading.direct_factor(10, 0, 30, 0, rows=rows), 1.0)


ARRAY = {"width_m": 10.0, "slope_m": 4.0, "base_height_m": 0.5}


class TestNearObstacles(unittest.TestCase):
    def points(self):
        return nearshade.sample_points(ARRAY, 30, 0)

    def test_no_obstacle_leaves_the_array_in_the_sun(self):
        self.assertEqual(nearshade.sunlit_fraction(self.points(), [], 30, 0), 1.0)

    def test_a_tall_box_between_the_array_and_the_sun_shades_it(self):
        box = {"x_m": 0.0, "y_m": 6.0, "width_m": 20.0, "depth_m": 1.0, "height_m": 30.0}      # a wall to the north, the side of the sun
        self.assertEqual(nearshade.sunlit_fraction(self.points(), [box], 30, 0), 0.0)
        self.assertEqual(nearshade.sunlit_fraction(self.points(), [box], 30, 180), 1.0)         # sun from the south: the wall is behind

    def test_a_low_box_shades_part_of_the_array_only_with_a_low_sun(self):
        box = {"x_m": 0.0, "y_m": 7.0, "width_m": 20.0, "depth_m": 1.0, "height_m": 2.0}
        high = nearshade.sunlit_fraction(self.points(), [box], 70, 0)
        low = nearshade.sunlit_fraction(self.points(), [box], 8, 0)
        self.assertEqual(high, 1.0)
        self.assertLess(low, 1.0)

    def test_the_sun_below_the_horizon_shades_nothing(self):
        self.assertEqual(nearshade.sunlit_fraction(self.points(), [{"x_m": 0, "y_m": 6, "width_m": 5, "depth_m": 5, "height_m": 9}], -5, 0), 1.0)

    def test_bad_data_is_an_error_in_both_languages(self):
        for bad in ({}, {"array": ARRAY}, {"array": dict(ARRAY, slope_m=0), "boxes": []}, {"array": ARRAY, "boxes": [{"x_m": 0}]}):
            with self.assertRaises(PvError) as ctx:
                nearshade.check(bad, "near_obstacles")
            self.assertTrue(ctx.exception.en and ctx.exception.es)

    def test_in_the_pipeline_a_wall_to_the_north_costs_energy_and_replaces_the_typical_loss(self):
        wall = {"array": ARRAY, "boxes": [{"x_m": 0.0, "y_m": 4.0, "width_m": 40.0, "depth_m": 1.0, "height_m": 12.0}]}
        base, shaded = run(doc()), run(doc(near_obstacles=wall))
        self.assertGreater(shaded.arrays[0]["shading_loss_pct"], 0.0)
        self.assertLess(shaded.arrays[0]["poa_kwh_m2"], base.arrays[0]["poa_kwh_m2"])


class TestApply(unittest.TestCase):
    def test_only_the_direct_part_is_reduced(self):
        poa = {"direct": 600.0, "sky": 100.0, "ground": 20.0, "global": 720.0, "effective": 700.0, "cos_aoi": 0.8}
        out = shading.apply(poa, 0.5)
        self.assertAlmostEqual(out["global"], 420.0)
        self.assertAlmostEqual(out["effective"], 700.0 - (700.0 - 120.0) * 0.5)
        self.assertEqual(shading.apply(poa, 1.0), poa)


class TestPipeline(unittest.TestCase):
    def test_without_shade_data_nothing_changes(self):
        base = run(doc())
        self.assertNotIn("shading_loss_pct", base.arrays[0])

    def test_a_horizon_lowers_the_yield_and_replaces_the_typical_loss(self):
        base, shaded = run(doc()), None
        d = doc()
        d["site"]["horizon"] = [{"azimuth_deg": 0, "elevation_deg": 45}]
        shaded = run(d)
        self.assertGreater(shaded.arrays[0]["shading_loss_pct"], 0.0)
        self.assertTrue(any("shade is computed" in w["en"] or "shade is computed" in str(w) for w in shaded.warnings))
        self.assertLess(shaded.arrays[0]["poa_kwh_m2"], base.arrays[0]["poa_kwh_m2"])

    def test_a_flat_horizon_at_zero_loses_nothing(self):
        d = doc()
        d["site"]["horizon"] = [{"azimuth_deg": 0, "elevation_deg": 0}]
        self.assertEqual(run(d).arrays[0]["shading_loss_pct"], 0.0)

    def test_close_rows_lose_more_than_far_rows(self):
        close, far = doc(row_shading={"slope_m": 2.0, "pitch_m": 1.75, "n_rows": 8}), doc(row_shading={"slope_m": 2.0, "pitch_m": 9.0, "n_rows": 8})
        self.assertGreater(run(close).arrays[0]["shading_loss_pct"], run(far).arrays[0]["shading_loss_pct"])

    def test_same_input_same_result(self):
        d = doc(row_shading={"slope_m": 2.0, "pitch_m": 3.0, "n_rows": 5})
        self.assertEqual(run(d).arrays, run(d).arrays)

    def test_bad_row_data_is_an_error(self):
        with self.assertRaises(PvError):
            run(doc(row_shading={"slope_m": 2.0, "pitch_m": -1.0, "n_rows": 3}))
        with self.assertRaises(PvError):
            run(doc(row_shading={"slope_m": 2.0}))


if __name__ == "__main__":
    unittest.main()
