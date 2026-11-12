"""Descargas atmosféricas: superficie de captación, frecuencia de impactos, eficiencia requerida y nivel de protección."""
import math
import unittest

from epc_aea90364 import aea_lightning as L


class TestLightning(unittest.TestCase):
    def test_collection_area_and_direct_strikes(self):
        ad = L.superficie_captacion_m2(30.0, 20.0, 10.0)
        self.assertAlmostEqual(ad, 600 + 2 * 30 * 50 + math.pi * 900, places=6)         # L·W + 2·(3H)·(L+W) + π·(3H)²
        self.assertAlmostEqual(L.impactos_directos_anuales(4.0, ad, "aislada"), 4.0 * ad * 1e-6, places=9)
        self.assertGreater(L.impactos_directos_anuales(4.0, ad, "aislada_en_colina"), L.impactos_directos_anuales(4.0, ad, "rodeada_mas_alta"))
        with self.assertRaises(ValueError):
            L.impactos_directos_anuales(4.0, ad, "marte")

    def test_tolerable_frequency_falls_with_the_consequences(self):
        low = L.frecuencia_tolerable("comun_techo_comun", "valor_normal", "normal", "sin_continuidad_de_servicio")
        high = L.frecuencia_tolerable("comun_techo_comun", "valor_alto", "dificil_evacuacion", "con_continuidad_de_servicio")
        self.assertAlmostEqual(low, 0.0055 / 2.0, places=9)
        self.assertLess(high, low)

    def test_level_by_efficiency_and_its_design_parameters(self):
        self.assertEqual([L.nivel_proteccion(e) for e in (0.99, 0.96, 0.92, 0.85, 0.5, 0.0, -1.0)], ["I+", "I", "II", "III", "IV", "none", "none"])
        self.assertEqual(L.parametros_nivel("II"), {"esfera_m": 30, "malla_m": 10, "bajadas_m": 10})
        self.assertEqual(L.parametros_nivel("I+"), L.parametros_nivel("I"))

    def test_evaluation_of_a_whole_structure(self):
        big = L.evaluar(60, 40, 25, 8.0, "aislada", "comun_techo_comun", "valor_alto", "normal", "con_continuidad_de_servicio")
        self.assertIn(big["nivel"], ("I", "I+"))                                      # large, tall and critical: the strictest level
        small = L.evaluar(5, 5, 3, 1.0, "rodeada_mas_alta", "comun_techo_comun", "valor_normal", "normal", "sin_continuidad_de_servicio")
        self.assertEqual((small["nivel"], small["parametros"], small["eficiencia"]), ("none", None, 0.0))


if __name__ == "__main__":
    unittest.main()
