"""Respaldo de energía: grupo electrógeno con el arranque del motor más exigente, UPS con su batería y el interruptor de transferencia."""
import unittest

from epc_aea90364 import aea_backup as B


class TestGenerator(unittest.TestCase):
    def test_without_motors_the_set_is_sized_by_the_continuous_load(self):
        g = B.grupo([("L1", 60.0, "single"), ("L2", 40.0, "single")], 400.0)
        self.assertEqual((g["s_marcha_kva"], g["s_arranque_kva"], g["motor"]), (100.0, 100.0, ""))
        self.assertEqual(g["grupo_kva"], 125.0)                                    # 100 / 0,8 = 125 kVA, which is commercial
        self.assertAlmostEqual(g["corriente_a"], 125000 / (3 ** 0.5 * 400), places=1)

    def test_the_motor_that_starts_hardest_may_set_the_size(self):
        g = B.grupo([("L1", 20.0, "single"), ("M1", 30.0, "dol"), ("M2", 30.0, "star_delta")], 400.0)
        self.assertEqual(g["motor"], "M1")                                         # 6 x 30 kVA direct beats 2 x 30 kVA star-delta
        self.assertEqual(g["s_arranque_kva"], 80.0 - 30.0 + 180.0)                 # the others run (50 kVA) while M1 starts at 6 x 30
        self.assertEqual(g["grupo_kva"], 125.0)                                    # start 230 kVA / 2 = 115 beats continuous 80 / 0,8 = 100
        slow = B.grupo([("L1", 20.0, "single"), ("M1", 30.0, "softstarter")], 400.0)
        self.assertLess(slow["grupo_kva"], g["grupo_kva"])                          # a soft starter asks for a smaller set

    def test_no_loads_no_set(self):
        self.assertEqual(B.grupo([], 400.0)["grupo_kva"], 0.0)
        self.assertEqual(B.multiplo_arranque("single"), 1.0)


class TestUpsAndTransfer(unittest.TestCase):
    def test_the_ups_has_a_reserve_and_the_battery_covers_the_autonomy(self):
        u = B.ups(8.0, 7.2, 30)
        self.assertEqual(u["ups_kva"], 10.0)                                       # 8 x 1,25 = 10 kVA
        self.assertAlmostEqual(u["bateria_kwh"], 7.2 * 0.5 / (0.92 * 0.8), places=2)
        self.assertEqual(B.ups(0.0, 0.0, 30), {"ups_kva": 0.0, "bateria_kwh": 0.0})
        self.assertGreater(B.ups(8.0, 7.2, 60)["bateria_kwh"], u["bateria_kwh"])

    def test_the_transfer_switch_takes_a_margin_over_the_current(self):
        self.assertEqual(B.transferencia(100.0, [63, 100, 125, 160, 200]), 125.0)   # 100 x 1,25
        self.assertEqual(B.transferencia(0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
