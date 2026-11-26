"""The irradiation disk: the percentage of the best plane for every tilt and orientation of a site."""
import unittest

from epc_pv import PvError, disk

from test_pv import doc


def site_doc(lat=-34.6, lon=-58.4):
    d = doc()
    d["site"].update(latitude_deg=lat, longitude_deg=lon)
    d["weather"]["utc_offset_h"] = lon / 15.0          # the bell of the synthetic day is centred on the solar noon
    del d["arrays"]
    return d


class TestDisk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.south = disk.compute(site_doc(), tilt_step_deg=15, azimuth_step_deg=30)
        cls.north = disk.compute(site_doc(lat=40.4, lon=-3.7), tilt_step_deg=15, azimuth_step_deg=30)

    def test_the_best_plane_faces_the_equator(self):
        self.assertEqual(self.south["best"]["azimuth_deg"], 0.0)
        self.assertEqual(self.north["best"]["azimuth_deg"], 180.0)

    def test_the_best_cell_is_100_and_no_cell_is_above(self):
        flat = [v for row in self.south["pct"] for v in row]
        self.assertEqual(max(flat), 100.0)
        self.assertTrue(all(0.0 <= v <= 100.0 for v in flat))

    def test_a_vertical_plane_facing_away_gets_the_least(self):
        last = self.south["pct"][-1]
        self.assertLess(last[self.south["azimuth_deg"].index(180.0)], last[self.south["azimuth_deg"].index(0.0)])

    def test_a_flat_plane_has_the_same_value_at_every_orientation(self):
        self.assertEqual(len(set(self.south["pct"][0])), 1)

    def test_the_grid_has_the_asked_steps(self):
        self.assertEqual(self.south["tilt_deg"], [0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0])
        self.assertEqual(self.south["azimuth_deg"], [30.0 * k for k in range(12)])

    def test_pct_at_a_cell_is_the_cell_and_the_circle_wraps(self):
        self.assertEqual(disk.pct_at(self.south, 30.0, 60.0), self.south["pct"][2][2])
        self.assertEqual(disk.pct_at(self.south, 30.0, 360.0), disk.pct_at(self.south, 30.0, 0.0))

    def test_pct_between_cells_lies_between_them(self):
        a, b = self.south["pct"][2][0], self.south["pct"][2][1]
        self.assertTrue(min(a, b) <= disk.pct_at(self.south, 30.0, 15.0) <= max(a, b))

    def test_same_input_same_disk(self):
        self.assertEqual(self.south, disk.compute(site_doc(), tilt_step_deg=15, azimuth_step_deg=30))

    def test_the_isotropic_model_is_a_different_disk(self):
        from epc_pv import Options
        other = disk.compute(site_doc(), Options(transposition="isotropic"), tilt_step_deg=15, azimuth_step_deg=30)
        self.assertNotEqual(other["kwh_m2"], self.south["kwh_m2"])

    def test_bad_steps_are_an_error_in_both_languages(self):
        for step in (0, 7, 200):
            with self.assertRaises(PvError) as ctx:
                disk.compute(site_doc(), tilt_step_deg=step)
            self.assertTrue(ctx.exception.en and ctx.exception.es and ctx.exception.en != ctx.exception.es)

    def test_a_json_text_is_accepted_and_a_bad_one_is_an_error(self):
        import json
        got = disk.compute(json.dumps(site_doc()), tilt_step_deg=45, azimuth_step_deg=90)
        self.assertEqual(got["best"]["azimuth_deg"], 0.0)
        with self.assertRaises(PvError):
            disk.compute("{no", tilt_step_deg=45, azimuth_step_deg=90)

    def test_no_light_is_an_error(self):
        d = site_doc()
        for k in ("ghi", "dni", "dhi"):
            d["weather"][k] = [0.0] * len(d["weather"][k])
        with self.assertRaises(PvError):
            disk.compute(d, tilt_step_deg=45, azimuth_step_deg=90)


if __name__ == "__main__":
    unittest.main()


class TestRefine(unittest.TestCase):
    def test_a_finer_grid_keeps_the_coarse_values_and_the_best_plane(self):
        coarse = disk.compute(site_doc(), tilt_step_deg=15, azimuth_step_deg=30)
        fine = disk.refine(coarse, 5, 10)
        self.assertEqual(len(fine["tilt_deg"]), 19)
        self.assertEqual(len(fine["azimuth_deg"]), 36)
        self.assertEqual(fine["pct"][3][3], coarse["pct"][1][1])            # tilt 15, azimuth 30 sit on both grids
        self.assertEqual(fine["best"], coarse["best"])

    def test_a_bad_step_is_an_error(self):
        coarse = disk.compute(site_doc(), tilt_step_deg=45, azimuth_step_deg=90)
        with self.assertRaises(PvError):
            disk.refine(coarse, 7, 10)
