"""The shading abacus: the standard cells A1 to D14, their weights and the loss an obstacle profile causes."""
import unittest

from epc_pv import PvError, abacus, run

from test_pv import doc
from test_disk import site_doc


def with_horizon(elevation, lat=-34.6):
    d = site_doc(lat=lat)
    d["site"]["horizon"] = [{"azimuth_deg": a, "elevation_deg": elevation} for a in (0, 90, 180, 270)]
    return d


class TestLayout(unittest.TestCase):
    def test_the_standard_ids(self):
        self.assertEqual(abacus.cell_id(0, 1, True), "A1")
        self.assertEqual(abacus.cell_id(0, 1, False), "A2")
        self.assertEqual(abacus.cell_id(1, 2, True), "B3")
        self.assertEqual(abacus.cell_id(3, 7, False), "D14")

    def test_the_bands_are_cut_by_equal_declinations_from_the_lowest_sun(self):
        south, north = abacus._edges(-34.6), abacus._edges(40.0)
        self.assertEqual(south[0], 23.44)
        self.assertEqual(south[-1], -23.44)
        self.assertEqual(north[0], -23.44)
        self.assertAlmostEqual(south[1] - south[0], -11.72)

    def test_the_noon_sun_of_the_extreme_bands_is_at_the_known_elevation(self):
        x, low = abacus.sun_xy(-34.6, 23.44, 0.0)
        _, high = abacus.sun_xy(-34.6, -23.44, 0.0)
        self.assertAlmostEqual(low, 90 - 34.6 - 23.44, places=2)
        self.assertAlmostEqual(high, 90 - abs(-34.6 + 23.44), places=2)
        self.assertEqual(x, 0.0)

    def test_the_morning_is_on_the_east_side_in_the_south_and_the_afternoon_on_the_west(self):
        east, _ = abacus.sun_xy(-34.6, 0.0, -45.0)
        west, _ = abacus.sun_xy(-34.6, 0.0, 45.0)
        self.assertGreater(east, 0)
        self.assertLess(west, 0)

    def test_cells_cover_the_four_bands_and_both_sides(self):
        ids = {c["id"] for c in abacus.layout(-34.6)}
        for expected in ("A1", "A2", "B1", "C2", "D1", "D2", "D13", "D14"):
            self.assertIn(expected, ids)
        self.assertTrue(all(c["outline"] for c in abacus.layout(-34.6)))
        self.assertTrue(all(el >= 0 for c in abacus.layout(-34.6) for _, el in c["outline"]))

    def test_the_north_hemisphere_is_centred_on_the_south(self):
        x, el = abacus.sun_xy(40.0, 0.0, 0.0)
        self.assertEqual(x, 0.0)
        self.assertAlmostEqual(el, 50.0, places=1)

    def test_no_profile_hides_nothing(self):
        self.assertTrue(all(c["cover"] == 0.0 for c in abacus.layout(-34.6)))

    def test_quantize_to_the_filling_factors(self):
        self.assertEqual([abacus.quantize(v) for v in (0.0, 0.1, 0.3, 0.6, 0.9, 1.0)], [0.0, 0.0, 0.25, 0.5, 1.0, 1.0])


class TestWeights(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.share = abacus.weights(site_doc(), 30.0, 0.0)

    def test_the_shares_add_up_to_one(self):
        self.assertAlmostEqual(sum(self.share.values()), 1.0, places=9)

    def test_noon_cells_weigh_more_than_the_ends_of_the_day(self):
        noon = sum(v for k, v in self.share.items() if k[1:] in ("1", "2"))
        ends = sum(v for k, v in self.share.items() if k[1:] in ("13", "14"))
        self.assertGreater(noon, ends)

    def test_a_json_text_and_a_document_without_arrays_work(self):
        import json
        self.assertEqual(abacus.weights(json.dumps(site_doc()), 30.0, 0.0), self.share)

    def test_no_light_is_an_error(self):
        d = site_doc()
        for k in ("ghi", "dni", "dhi"):
            d["weather"][k] = [0.0] * len(d["weather"][k])
        with self.assertRaises(PvError):
            abacus.weights(d, 30.0, 0.0)


class TestCompute(unittest.TestCase):
    def test_without_a_profile_the_loss_is_zero(self):
        got = abacus.compute(site_doc(), 30.0, 0.0)
        self.assertEqual(got["loss_pct"], 0.0)
        self.assertEqual(got["profile"], [])
        self.assertAlmostEqual(sum(c["weight_pct"] for c in got["cells"]), 100.0, places=2)

    def test_a_wall_all_around_hides_everything(self):
        self.assertAlmostEqual(abacus.compute(with_horizon(90.0), 30.0, 0.0)["loss_pct"], 100.0, places=2)

    def test_a_low_horizon_hides_the_low_sun_only(self):
        low, high = abacus.compute(with_horizon(10.0), 30.0, 0.0)["loss_pct"], abacus.compute(with_horizon(40.0), 30.0, 0.0)["loss_pct"]
        self.assertLessEqual(low, high)
        self.assertGreater(high, 0.0)
        self.assertLess(high, 100.0)

    def test_the_ray_cast_loss_and_the_abacus_loss_are_both_positive_for_the_same_profile(self):
        ray = doc()
        ray["site"]["horizon"] = with_horizon(40.0)["site"]["horizon"]
        self.assertGreater(run(ray).arrays[0]["shading_loss_pct"], 0.0)
        self.assertGreater(abacus.compute(with_horizon(40.0), 30.0, 0.0)["loss_pct"], 0.0)

    def test_the_profile_is_given_on_the_chart_sorted(self):
        got = abacus.compute(with_horizon(40.0), 30.0, 0.0)
        self.assertEqual(got["profile"], sorted(got["profile"]))
        self.assertEqual(len(got["profile"]), 4)

    def test_same_input_same_abacus(self):
        self.assertEqual(abacus.compute(with_horizon(30.0), 30.0, 0.0), abacus.compute(with_horizon(30.0), 30.0, 0.0))


if __name__ == "__main__":
    unittest.main()
