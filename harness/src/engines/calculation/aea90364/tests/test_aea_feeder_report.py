"""Pruebas de la Memoria de Cálculo y Síntesis del alimentador principal."""
import os
import shutil
import tempfile
import unittest

from epc_aea90364 import aea_feeder_report as AFR
from epc_aea90364 import aea_pipeline as P


def _leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def _datos():
    tablero = {"TENSION_V": 380, "ICC_KA": 36, "FP_DEFAULT": 0.85, "SISTEMA": "TN-S"}
    circuitos = [
        {"TAG": "C-01", "DESCRIPCION": "ALIMENTADOR TD-PB", "CARGA": 250, "UNIDAD_CARGA": "A",
         "PARENT_TAG": None, "KIND": "mccb", "TOPOLOGY": "single", "FASE": "3F", "LONGITUD_m": 40,
         "CABLE_TIPO": "tetra_sep"},
        {"TAG": "M-01", "DESCRIPCION": "EXTRACTOR", "CARGA": 11, "UNIDAD_CARGA": "kW", "PARENT_TAG": None,
         "KIND": "auto", "TOPOLOGY": "dol_ol", "FASE": "3F", "LONGITUD_m": 30, "FP": 0.85, "RENDIMIENTO": 0.9},
    ]
    datos, _ = P.calculate(tablero, circuitos)
    return tablero, circuitos, datos


class TestMismasReglasQueElPipeline(unittest.TestCase):
    def test_xlpe_sin_metodo_es_b2_tambien_en_el_informe(self):
        tablero, circuitos, datos = _datos()
        c = {**circuitos[0], "AISLACION": "xlpe", "MATERIAL": "al"}
        v = AFR.verificaciones(tablero, c, {"S": 240, "In": 250, "icu": 36, "disp": "MCCB"})
        self.assertEqual(v["par"]["metodo"], "B2")                                      # B1 has no table for XLPE: the pipeline puts B2

    def test_un_metodo_dado_no_se_cambia(self):
        tablero, circuitos, _ = _datos()
        v = AFR.verificaciones(tablero, {**circuitos[0], "AISLACION": "xlpe", "METODO": "E"}, {"S": 95, "In": 250, "icu": 36, "disp": "MCCB"})
        self.assertEqual(v["par"]["metodo"], "E")

    def test_la_iluminacion_cae_con_el_66_por_ciento_de_ib(self):
        tablero, circuitos, _ = _datos()
        c = {**circuitos[0], "TAG": "L-01", "DESCRIPCION": "ILUMINACION PLANTA", "KIND": "mcb", "CARGA": 20}
        reg = {"S": 4, "In": 20, "icu": 6, "disp": "MCB"}
        luz = AFR.verificaciones(tablero, c, reg)["du"]
        toma = AFR.verificaciones(tablero, {**c, "TAG": "T-01", "DESCRIPCION": "TOMAS"}, reg)["du"]
        self.assertAlmostEqual(luz, toma * 0.66, places=6)


class TestAlimentadorPrincipal(unittest.TestCase):
    def test_elige_primer_mccb_sin_padre(self):
        _, circuitos, _ = _datos()
        self.assertEqual(AFR.alimentador_principal(circuitos)["TAG"], "C-01")

    def test_tag_explicito(self):
        _, circuitos, _ = _datos()
        self.assertEqual(AFR.alimentador_principal(circuitos, "M-01")["TAG"], "M-01")

    def test_sin_alimentador(self):
        with self.assertRaises(ValueError):
            AFR.alimentador_principal([{"TAG": "X", "KIND": "mcb", "PARENT_TAG": None}])


class TestDocumentos(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.base = os.path.join(self.dir, "P")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_genera_mc_y_sp_solo_del_principal(self):
        tablero, circuitos, datos = _datos()
        rutas = AFR.generar_documentos(self.base, tablero, circuitos, datos)
        self.assertEqual(len(rutas), 2)
        mc = _leer(self.base + "_MC.md")
        sp = _leer(self.base + "_SP.md")
        for etapa in ("Etapa 1", "Etapa 2", "Etapa 3", "Etapa 4", "Etapa 5", "Etapa 6"):
            self.assertIn(etapa, mc)
        self.assertIn("C-01", mc)
        self.assertNotIn("M-01", mc)
        self.assertIn("Requisito normativo", sp)
        self.assertNotIn("M-01", sp)

    def test_numeros_con_coma_y_resultado(self):
        tablero, circuitos, datos = _datos()
        AFR.generar_documentos(self.base, tablero, circuitos, datos)
        mc = _leer(self.base + "_MC.md")
        self.assertIn("Resultado global:", mc)
        self.assertIn(" %", mc)

    def test_sintesis_maximo_tres_observaciones(self):
        tablero, circuitos, datos = _datos()
        AFR.generar_documentos(self.base, tablero, circuitos, datos)
        sp = _leer(self.base + "_SP.md")
        obs = sp.split("**Observaciones**")[1].strip().splitlines()
        self.assertLessEqual(len([l for l in obs if l[:1].isdigit()]), 3)


if __name__ == "__main__":
    unittest.main()
