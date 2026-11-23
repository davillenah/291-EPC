"""OPT-13: invariants of the earthing formulas over many generated inputs (seeded, standard library only; no norm value is used)."""
import random
import unittest

from epc_grounding import resistance_parallel, resistance_rod

SAMPLES = 300


class GroundingProperties(unittest.TestCase):
    def test_electrodes_in_parallel_are_below_the_best_one_and_above_the_best_over_n(self):
        rng = random.Random(1)
        for _ in range(SAMPLES):
            rs = [rng.uniform(0.5, 500.0) for _ in range(rng.randint(1, 8))]
            total = resistance_parallel(rs)
            with self.subTest(rs=rs):
                self.assertLessEqual(total, min(rs) * (1 + 1e-12))
                self.assertGreaterEqual(total, min(rs) / len(rs) * (1 - 1e-12))

    def test_the_order_of_the_electrodes_does_not_matter(self):
        rng = random.Random(2)
        for _ in range(SAMPLES):
            rs = [rng.uniform(0.5, 500.0) for _ in range(rng.randint(2, 8))]
            with self.subTest(rs=rs):
                self.assertAlmostEqual(resistance_parallel(rs), resistance_parallel(list(reversed(rs))), places=9)

    def test_adding_an_electrode_never_raises_the_resistance(self):
        rng = random.Random(3)
        for _ in range(SAMPLES):
            rs = [rng.uniform(0.5, 500.0) for _ in range(rng.randint(1, 6))]
            with self.subTest(rs=rs):
                self.assertLess(resistance_parallel(rs + [rng.uniform(0.5, 500.0)]), resistance_parallel(rs))

    def test_the_rod_resistance_grows_with_soil_resistivity_and_falls_with_length(self):
        rng = random.Random(4)
        for _ in range(SAMPLES):
            rho, length, d = rng.uniform(10, 1000), rng.uniform(1.0, 6.0), rng.uniform(0.01, 0.03)
            with self.subTest(rho=rho, length=length):
                self.assertGreater(resistance_rod(rho * 2, length, d), resistance_rod(rho, length, d))
                self.assertLess(resistance_rod(rho, length * 1.5, d), resistance_rod(rho, length, d))


if __name__ == "__main__":
    unittest.main()
