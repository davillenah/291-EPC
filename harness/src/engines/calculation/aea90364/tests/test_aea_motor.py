"""Fuerza motriz: corriente de arranque según el arrancador y caída de tensión del cable en el arranque."""
import unittest

from epc_aea90364 import aea_motor as M


class TestMotorStart(unittest.TestCase):
    def test_starting_current_follows_the_starter(self):
        self.assertEqual(M.corriente_arranque(10.0, "dol"), 60.0)
        self.assertEqual(M.corriente_arranque(10.0, "star_delta"), 20.0)
        self.assertEqual(M.corriente_arranque(10.0, "softstarter"), 30.0)
        self.assertEqual(M.corriente_arranque(10.0, "vfd"), 12.0)

    def test_the_drop_while_starting_uses_the_starting_gdc(self):
        r = M.caida_arranque(20.0, "dol", 250.0, 6.0, "cu", 3)
        self.assertEqual(r["i_arranque_a"], 120.0)
        self.assertGreater(r["caida_pct"], 15.0)                                   # 120 A in 6 mm² over 250 m is a big drop
        self.assertFalse(r["cumple"])
        soft = M.caida_arranque(20.0, "softstarter", 250.0, 6.0, "cu", 3)
        self.assertLess(soft["caida_pct"], r["caida_pct"])                         # a gentler starter lowers it
        self.assertTrue(M.caida_arranque(20.0, "vfd", 250.0, 6.0, "cu", 3)["cumple"])

    def test_above_70_mm2_the_table_has_no_starting_value(self):
        r = M.caida_arranque(200.0, "dol", 30.0, 95.0, "cu", 3)
        self.assertIsNone(r["caida_pct"])
        self.assertIsNone(r["cumple"])

    def test_the_motor_protection_is_set_from_the_rated_current(self):
        p = M.proteccion_motor(10.0, "dol")
        self.assertEqual((p["ajuste_termico_a"], p["rango_a"], p["clase_disparo"]), (10.0, (7, 10), 10))    # the smallest commercial range that holds 10 A
        self.assertEqual(p["magnetico_min_a"], 72.0)                                                      # 1.2 times the starting current (6 x 10 A)
        self.assertLess(M.proteccion_motor(10.0, "softstarter")["magnetico_min_a"], p["magnetico_min_a"])
        self.assertIsNone(M.proteccion_motor(500.0, "dol")["rango_a"])                                    # no commercial relay range holds it
        with self.assertRaises(ValueError):
            M.proteccion_motor(0, "dol")


if __name__ == "__main__":
    unittest.main()
