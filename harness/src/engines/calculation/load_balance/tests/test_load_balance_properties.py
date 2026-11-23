"""OPT-13: invariants of the load formulas over many generated inputs (seeded, standard library only; no norm value is used)."""
import math
import random
import unittest

from epc_load_balance import corriente_monofasica, corriente_trifasica, imbalance_phases, power_apparent_three_phase

SAMPLES = 300


class LoadBalanceProperties(unittest.TestCase):
    def test_more_power_never_lowers_the_current(self):
        rng = random.Random(1)
        for _ in range(SAMPLES):
            p, v, fp, eta = rng.uniform(100, 200000), rng.uniform(100, 700), rng.uniform(0.5, 1.0), rng.uniform(0.6, 1.0)
            with self.subTest(p=p, v=v):
                self.assertGreaterEqual(corriente_trifasica(p * 1.3, v, fp, eta), corriente_trifasica(p, v, fp, eta))
                self.assertGreaterEqual(corriente_monofasica(p * 1.3, v, fp, eta), corriente_monofasica(p, v, fp, eta))

    def test_a_lower_power_factor_or_efficiency_never_lowers_the_current(self):
        rng = random.Random(2)
        for _ in range(SAMPLES):
            p, v, fp = rng.uniform(100, 200000), rng.uniform(100, 700), rng.uniform(0.6, 1.0)
            with self.subTest(p=p, v=v, fp=fp):
                self.assertGreaterEqual(corriente_trifasica(p, v, fp * 0.9), corriente_trifasica(p, v, fp))
                self.assertGreaterEqual(corriente_trifasica(p, v, fp, 0.8), corriente_trifasica(p, v, fp, 0.9))

    def test_the_three_phase_current_is_the_single_phase_one_over_root_three(self):
        rng = random.Random(3)
        for _ in range(SAMPLES):
            p, v, fp = rng.uniform(100, 200000), rng.uniform(100, 700), rng.uniform(0.5, 1.0)
            with self.subTest(p=p, v=v):
                self.assertAlmostEqual(corriente_trifasica(p, v, fp) * math.sqrt(3.0), corriente_monofasica(p, v, fp), delta=1e-9 * corriente_monofasica(p, v, fp))

    def test_power_and_current_are_inverse_of_each_other(self):
        rng = random.Random(4)
        for _ in range(SAMPLES):
            v, i = rng.uniform(100, 700), rng.uniform(0.5, 900)
            s = power_apparent_three_phase(v, i)
            with self.subTest(v=v, i=i):
                self.assertAlmostEqual(corriente_trifasica(s, v, 1.0, 1.0), i, delta=1e-9 * i)

    def test_the_imbalance_is_a_percentage_independent_of_the_order_and_the_scale(self):
        rng = random.Random(5)
        for _ in range(SAMPLES):
            currents = [rng.uniform(1.0, 200.0) for _ in range(rng.randint(2, 3))]
            base = imbalance_phases(currents)["desequilibrio_pct"]
            shuffled = list(reversed(currents))
            with self.subTest(currents=currents):
                self.assertTrue(0.0 <= base < 100.0)
                self.assertAlmostEqual(imbalance_phases(shuffled)["desequilibrio_pct"], base, places=9)
                self.assertAlmostEqual(imbalance_phases([c * 4 for c in currents])["desequilibrio_pct"], base, places=9)
                self.assertEqual(imbalance_phases([currents[0]] * 3)["desequilibrio_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
