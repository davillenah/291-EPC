"""OPT-13: invariants of the transformer sizing over many generated inputs (seeded, standard library only; no norm value is used)."""
import random
import unittest

from epc_transformer_sizing import apparent_power_kva, loading_pct, select_rating, standard_ratings_kva

SAMPLES = 300


class TransformerSizingProperties(unittest.TestCase):
    def test_the_chosen_rating_is_a_listed_one_and_covers_the_need(self):
        top = max(standard_ratings_kva())
        rng = random.Random(1)
        for _ in range(SAMPLES):
            need = rng.uniform(1.0, top)
            with self.subTest(need=need):
                chosen = select_rating(need)
                self.assertIn(chosen, standard_ratings_kva())
                self.assertGreaterEqual(chosen, need)
                self.assertFalse([r for r in standard_ratings_kva() if need <= r < chosen])

    def test_a_larger_need_never_picks_a_smaller_rating(self):
        top = max(standard_ratings_kva())
        rng = random.Random(2)
        for _ in range(SAMPLES):
            need = rng.uniform(1.0, top / 2)
            with self.subTest(need=need):
                self.assertGreaterEqual(select_rating(need * 1.7), select_rating(need))

    def test_loading_is_proportional_to_the_demand_and_inverse_to_the_rating(self):
        rng = random.Random(3)
        for _ in range(SAMPLES):
            demand, rating = rng.uniform(1.0, 2000.0), rng.uniform(10.0, 2500.0)
            with self.subTest(demand=demand, rating=rating):
                self.assertAlmostEqual(loading_pct(demand * 2, rating), 2 * loading_pct(demand, rating), places=9)
                self.assertAlmostEqual(loading_pct(demand, rating * 2) * 2, loading_pct(demand, rating), places=9)

    def test_the_apparent_power_is_linear_in_current_and_voltage(self):
        rng = random.Random(4)
        for _ in range(SAMPLES):
            i, un = rng.uniform(1.0, 5000.0), rng.uniform(100.0, 700.0)
            with self.subTest(i=i, un=un):
                self.assertAlmostEqual(apparent_power_kva(i * 3, un), 3 * apparent_power_kva(i, un), places=9)
                self.assertAlmostEqual(apparent_power_kva(i, un * 3), 3 * apparent_power_kva(i, un), places=9)


if __name__ == "__main__":
    unittest.main()
