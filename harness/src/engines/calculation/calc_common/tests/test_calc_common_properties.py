"""OPT-13: invariants of the shared rounding and correction helpers over many generated inputs (seeded, standard library only; no norm value is used)."""
import random
import unittest

from epc_calc_common import iz_corregida, round_down_2, round_up_2

SAMPLES = 300


class CalcCommonProperties(unittest.TestCase):
    def test_rounding_up_never_goes_below_and_down_never_above(self):
        rng = random.Random(1)
        for _ in range(SAMPLES):
            x = rng.uniform(0.0, 500.0)
            with self.subTest(x=x):
                self.assertGreaterEqual(round_up_2(x), x - 1e-9)
                self.assertLessEqual(round_down_2(x), x + 1e-9)
                self.assertLess(round_up_2(x) - round_down_2(x), 0.0100001 + 1e-9)

    def test_rounding_twice_gives_the_same_value(self):
        rng = random.Random(2)
        for _ in range(SAMPLES):
            x = rng.uniform(0.0, 500.0)
            with self.subTest(x=x):
                self.assertEqual(round_up_2(round_up_2(x)), round_up_2(x))
                self.assertEqual(round_down_2(round_down_2(x)), round_down_2(x))

    def test_a_smaller_correction_factor_never_raises_the_current_capacity(self):
        rng = random.Random(3)
        for _ in range(SAMPLES):
            iz0, f_temp, f_agrup = rng.uniform(10, 800), rng.uniform(0.5, 1.2), rng.uniform(0.3, 1.0)
            with self.subTest(iz0=iz0):
                base = iz_corregida(iz0, 1, False, f_temp, f_agrup, 1.0)
                self.assertLessEqual(iz_corregida(iz0, 1, False, f_temp * 0.9, f_agrup, 1.0), base)
                self.assertLessEqual(iz_corregida(iz0, 1, False, f_temp, f_agrup * 0.9, 1.0), base)

    def test_more_parallel_sets_never_lower_the_capacity(self):
        rng = random.Random(4)
        for _ in range(SAMPLES):
            iz0 = rng.uniform(10, 800)
            with self.subTest(iz0=iz0):
                self.assertGreaterEqual(iz_corregida(iz0, 2), iz_corregida(iz0, 1))


if __name__ == "__main__":
    unittest.main()
