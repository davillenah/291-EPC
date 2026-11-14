import json
import math
import unittest

import epc_transformer_sizing as T
from epc_short_circuit.short_circuit import corriente_asignada_trafo
from epc_transformer_sizing import ratings, sizing

SERIES = (25, 50, 63, 100, 160, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500)


class RatedCurrent(unittest.TestCase):
    def test_matches_the_short_circuit_function(self):
        self.assertAlmostEqual(T.rated_current_a(630, 400), corriente_asignada_trafo(630e3, 400), places=9)

    def test_value(self):
        self.assertAlmostEqual(T.rated_current_a(1000, 400), 1443.4, places=1)

    def test_invalid(self):
        for args in ((0, 400), (-1, 400), (100, 0), (True, 400), (float("nan"), 400), ("1", 400)):
            with self.assertRaises(ValueError):
                T.rated_current_a(*args)


class ApparentPower(unittest.TestCase):
    def test_is_the_inverse_of_the_rated_current(self):
        self.assertAlmostEqual(T.apparent_power_kva(T.rated_current_a(630, 400), 400), 630.0, places=9)

    def test_value(self):
        self.assertAlmostEqual(T.apparent_power_kva(100, 400), 69.282, places=3)

    def test_invalid(self):
        for args in ((0, 400), (-1, 400), (100, 0), (True, 400), (float("nan"), 400)):
            with self.assertRaises(ValueError):
                T.apparent_power_kva(*args)


class RequiredPower(unittest.TestCase):
    def test_reserve_applied(self):
        self.assertAlmostEqual(T.required_apparent_power_kva(400, 25), 500.0)
        self.assertEqual(T.required_apparent_power_kva(400, 0), 400)

    def test_reserve_is_required(self):
        with self.assertRaisesRegex(ValueError, "reserve_pct is required"):
            T.required_apparent_power_kva(400, None)

    def test_negative_reserve_rejected(self):
        with self.assertRaises(ValueError):
            T.required_apparent_power_kva(400, -1)

    def test_demand_must_be_positive(self):
        with self.assertRaises(ValueError):
            T.required_apparent_power_kva(0, 10)


class SelectRating(unittest.TestCase):
    def test_exact_match_keeps_the_rating(self):
        self.assertEqual(T.select_rating(630), 630)

    def test_just_above_takes_the_next(self):
        self.assertEqual(T.select_rating(630.01), 800)

    def test_below_smallest(self):
        self.assertEqual(T.select_rating(1), 25)

    def test_largest_is_accepted(self):
        self.assertEqual(T.select_rating(2500), 2500)

    def test_above_largest_rejected(self):
        with self.assertRaisesRegex(ValueError, "paralleling not modelled"):
            T.select_rating(2500.1)

    def test_custom_series_unsorted(self):
        self.assertEqual(T.select_rating(120, series=[300, 100, 200]), 200)

    def test_empty_series(self):
        with self.assertRaises(ValueError):
            T.select_rating(10, series=[])

    def test_invalid_required(self):
        with self.assertRaises(ValueError):
            T.select_rating(-5)


class Loading(unittest.TestCase):
    def test_value(self):
        self.assertAlmostEqual(T.loading_pct(400, 500), 80.0)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            T.loading_pct(400, 0)


class SizeTransformer(unittest.TestCase):
    def test_result(self):
        r = T.size_transformer(400, 400, 25)
        self.assertEqual((r["rating_kva"], r["required_kva"]), (500, 500.0))
        self.assertAlmostEqual(r["loading_pct"], 80.0)
        self.assertAlmostEqual(r["rated_current_a"], corriente_asignada_trafo(500e3, 400))
        self.assertEqual(r["series_used"], list(SERIES))
        self.assertEqual(r["norm_records"], ["transformer_sizing.params.standard_ratings"])
        self.assertTrue(any("pending review" in a for a in r["assumptions"]))
        self.assertTrue(any("25 %" in a for a in r["assumptions"]))

    def test_custom_series_has_no_norm_record(self):
        r = T.size_transformer(80, 400, 0, series=[100, 200])
        self.assertEqual((r["rating_kva"], r["norm_records"], r["series_used"]), (100, [], [100, 200]))
        self.assertTrue(any("given by the caller" in a for a in r["assumptions"]))

    def test_errors_propagate(self):
        with self.assertRaises(ValueError):
            T.size_transformer(400, 400, None)
        with self.assertRaises(ValueError):
            T.size_transformer(3000, 400, 0)
        with self.assertRaises(ValueError):
            T.size_transformer(400, 0, 10)


class DataAccessor(unittest.TestCase):
    def test_series_and_status(self):
        self.assertEqual(T.standard_ratings_kva(), SERIES)
        self.assertEqual(ratings.review_status(), "pending review")

    def test_cache_and_clear(self):
        ratings.clear_cache()
        a = ratings._load()
        self.assertIs(ratings._load(), a)
        T.clear_cache()
        self.assertIsNot(ratings._load(), a)

    def test_data_file_provenance(self):
        data = json.loads(ratings.DATA_FILE.read_text(encoding="utf-8"))
        self.assertEqual((data["clause"], data["review_status"]), ("no clause", "pending review"))
        self.assertIn("no clause located", data["provenance"])

    def test_sqrt3_used(self):
        self.assertAlmostEqual(sizing.rated_current_a(100, 400) * math.sqrt(3) * 400, 100e3)


if __name__ == "__main__":
    unittest.main()
