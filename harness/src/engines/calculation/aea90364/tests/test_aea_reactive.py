"""Compensación de reactiva: factor de potencia, reactiva a compensar y banco en escalones comerciales."""
import math
import unittest

from epc_aea90364 import aea_reactive as R


class TestReactive(unittest.TestCase):
    def test_the_balance_adds_p_and_q_and_not_the_apparent_powers(self):
        b = R.balance([(100.0, 0.8), (100.0, 1.0)])
        self.assertAlmostEqual(b["p_kw"], 200.0)
        self.assertAlmostEqual(b["q_kvar"], 75.0)                                  # 100 kW at 0,8 carry 75 kvar; the other none
        self.assertAlmostEqual(b["fp"], 200 / math.hypot(200, 75), places=6)

    def test_what_is_missing_to_reach_the_target(self):
        self.assertAlmostEqual(R.reactiva_a_compensar(100.0, 0.8, 0.95), 100 * (0.75 - math.tan(math.acos(0.95))), places=6)
        self.assertEqual(R.reactiva_a_compensar(100.0, 0.97, 0.95), 0.0)            # already above the target
        self.assertAlmostEqual(R.reactiva_a_compensar(100.0, 0.8), R.reactiva_a_compensar(100.0, 0.8, 0.95))     # the default target is the one of the tables
        with self.assertRaises(ValueError):
            R.reactiva_a_compensar(100.0, 1.2)

    def test_the_bank_uses_the_biggest_step_that_still_gives_four_stages(self):
        b = R.banco(100.0, 400.0)
        self.assertEqual((b["escalon_kvar"], b["escalones"], b["instalado_kvar"]), (25.0, 4, 100.0))
        small = R.banco(8.0, 400.0)
        self.assertEqual((small["escalon_kvar"], small["escalones"]), (5.0, 2))        # no step gives four stages of 8 kvar: the smallest
        odd = R.banco(90.0, 400.0)
        self.assertEqual((odd["escalon_kvar"], odd["escalones"], odd["instalado_kvar"]), (12.5, 8, 100.0))     # 25 kvar would give 3.6 stages

    def test_the_current_of_the_bank_and_the_one_the_cable_and_the_protection_carry(self):
        b = R.banco(100.0, 400.0)
        self.assertAlmostEqual(b["corriente_a"], 100000 / (math.sqrt(3) * 400), places=1)
        self.assertAlmostEqual(b["corriente_diseno_a"], 1.43 * b["corriente_a"], delta=0.02)
        self.assertEqual(R.banco(0.0, 400.0)["escalones"], 0)


if __name__ == "__main__":
    unittest.main()
