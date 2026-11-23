"""OPT-13: invariants of the protection formulas over many generated inputs (seeded, standard library only; no norm value is used)."""
import random
import unittest

from epc_selectivity import corriente_falla_tt, i2_convencional, in_max_por_iz

SAMPLES = 300


class SelectivityProperties(unittest.TestCase):
    def test_a_larger_rated_current_never_gives_a_smaller_conventional_current(self):
        rng = random.Random(1)
        for _ in range(SAMPLES):
            in_a = rng.uniform(2.0, 630.0)
            with self.subTest(in_a=in_a):
                self.assertGreater(i2_convencional(in_a * 1.5), i2_convencional(in_a))
                self.assertGreaterEqual(i2_convencional(in_a), in_a)

    def test_the_largest_allowed_rating_is_below_the_cable_capacity_and_a_larger_cable_never_allows_less(self):
        rng = random.Random(2)
        for _ in range(SAMPLES):
            iz = rng.uniform(20.0, 800.0)
            with self.subTest(iz=iz):
                allowed = in_max_por_iz(iz)
                self.assertLessEqual(allowed, iz)
                self.assertGreaterEqual(in_max_por_iz(iz * 1.4), allowed)

    def test_more_earthing_resistance_never_raises_the_first_fault_current(self):
        rng = random.Random(3)
        for _ in range(SAMPLES):
            u0, ra, rb = rng.uniform(100, 300), rng.uniform(1.0, 100.0), rng.uniform(1.0, 100.0)
            with self.subTest(ra=ra, rb=rb):
                base = corriente_falla_tt(u0, ra, rb)
                self.assertLess(corriente_falla_tt(u0, ra * 1.5, rb), base)
                self.assertLess(corriente_falla_tt(u0, ra, rb * 1.5), base)
                self.assertAlmostEqual(corriente_falla_tt(u0, ra, rb), corriente_falla_tt(u0, rb, ra), places=9)


if __name__ == "__main__":
    unittest.main()
