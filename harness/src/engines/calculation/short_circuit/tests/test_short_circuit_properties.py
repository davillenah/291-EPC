"""OPT-13: invariants of the short-circuit formulas over many generated inputs (seeded, standard library only; no norm value is used)."""
import random
import unittest

from epc_short_circuit import factor_kappa, ik_desde_impedancia

SAMPLES = 300


class ShortCircuitProperties(unittest.TestCase):
    def test_a_larger_impedance_never_raises_the_fault_current(self):
        rng = random.Random(1)
        for _ in range(SAMPLES):
            un, c, r, x = rng.uniform(100, 700), rng.uniform(0.95, 1.1), rng.uniform(0.0001, 0.5), rng.uniform(0.0001, 0.5)
            with self.subTest(un=un, r=r, x=x):
                self.assertLess(ik_desde_impedancia(un, c, r * 2, x * 2), ik_desde_impedancia(un, c, r, x))

    def test_the_fault_current_is_linear_in_voltage_and_in_c(self):
        rng = random.Random(2)
        for _ in range(SAMPLES):
            un, c, r, x = rng.uniform(100, 700), rng.uniform(0.95, 1.1), rng.uniform(0.0001, 0.5), rng.uniform(0.0001, 0.5)
            base = ik_desde_impedancia(un, c, r, x)
            with self.subTest(un=un):
                self.assertAlmostEqual(ik_desde_impedancia(un * 3, c, r, x), 3 * base, delta=1e-9 * base)
                self.assertAlmostEqual(ik_desde_impedancia(un, c * 2, r, x), 2 * base, delta=1e-9 * base)

    def test_scaling_both_parts_of_the_impedance_scales_the_current_inversely(self):
        rng = random.Random(3)
        for _ in range(SAMPLES):
            un, c, r, x = rng.uniform(100, 700), rng.uniform(0.95, 1.1), rng.uniform(0.0001, 0.5), rng.uniform(0.0001, 0.5)
            with self.subTest(r=r, x=x):
                self.assertAlmostEqual(ik_desde_impedancia(un, c, r * 5, x * 5) * 5, ik_desde_impedancia(un, c, r, x), delta=1e-9 * ik_desde_impedancia(un, c, r, x))

    def test_kappa_stays_between_its_limits_and_falls_as_resistance_rises(self):
        rng = random.Random(4)
        for _ in range(SAMPLES):
            x, r = rng.uniform(0.001, 1.0), rng.uniform(0.0, 2.0)
            with self.subTest(r=r, x=x):
                self.assertTrue(1.02 <= factor_kappa(r, x) <= 2.0)
                self.assertGreaterEqual(factor_kappa(r, x), factor_kappa(r * 1.5, x))


if __name__ == "__main__":
    unittest.main()
