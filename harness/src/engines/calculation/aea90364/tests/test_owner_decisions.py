"""Owner decisions of 2026-11-10 that change results (docs/harness/OWNER_DECISIONS_2026-11-10.md): D11 (TT), D12 (adiabatic k), PE section (cases s1, s2),
D25 (TN sectional time, one disconnection table) and D13 (Zs maximum with c_min in every module)."""
import ast
import json
import math
import os
import engine_sources
import unittest

from epc_aea90364 import aea_conductors as CO
from epc_aea90364 import aea_earthing as E
from epc_aea90364 import aea_protection as PR
from epc_aea90364 import aea_tables as T
from epc_aea90364 import board_memo as BM
from epc_aea90364 import cable_thermal as CT
from epc_aea90364 import system_voltage as SV

SRC = os.path.dirname(os.path.abspath(T.__file__))


def memo_ra_max(idn_ma):
    """Ra max printed by the board memo for a receptacle circuit protected by an RCBO of `idn_ma` mA."""
    tag = "T1"
    circ = {tag: {"description": "receptacles", "parent_tag": ""}}
    dat = {"In": 16, "Ib": 10.0, "S": 2.5, "icu": 10, "disp": "MCB"}
    det = {tag: {"tipo": "tomacorrientes", "kind": "rcbo", "topologia": "single", "cumple": True, "iz_a": 24.0, "icc_min_a": 500.0,
                 "s_termica_mm2": 2.5, "largo_m": 10.0, "ruta": [], "padre": ""}}
    return BM._circuit(tag, circ, dat, det, {}, idn_ma, "TT", 6000.0)["diferencial"]["ra_max_tt_ohm"]


class TtRaD11(unittest.TestCase):
    def test_30_and_300_ma_give_40_ohm_in_the_three_entry_points(self):
        for idn_a in (0.03, 0.3):
            with self.subTest(idn_a=idn_a):
                self.assertEqual(E.ra_maxima(idn_a)["adoptada"], 40.0)
                self.assertEqual(PR.ra_maxima_tt(idn_a), 40.0)
                self.assertEqual(PR.verifica_tt(10.0, idn_a)["ra_max_ohm"], 40.0)
                self.assertEqual(memo_ra_max(idn_a * 1000.0), 40.0)

    def test_above_the_cap_the_limit_is_half_of_24_v_over_idn(self):
        self.assertAlmostEqual(E.ra_maxima(1.0)["adoptada"], 12.0)
        self.assertAlmostEqual(PR.ra_maxima_tt(1.0), 12.0)
        self.assertAlmostEqual(memo_ra_max(1000.0), 12.0)

    def test_verifica_tt_decides_with_the_adopted_value(self):
        self.assertTrue(PR.verifica_tt(40.0, 0.03)["cumple"])
        self.assertFalse(PR.verifica_tt(41.0, 0.03)["cumple"])
        self.assertFalse(PR.verifica_tt(1666.0, 0.03)["cumple"])       # was True with UL = 50 V
        self.assertTrue(E.verifica_ra(40.0, 0.03))

    def test_the_50_v_column_is_only_available_when_asked_for(self):
        self.assertAlmostEqual(PR.ra_maxima_tt(0.03, ul_v=50.0), 50.0 / 0.03)
        self.assertAlmostEqual(E.ra_maxima(0.03)["col1_50v"], 50.0 / 0.03)
        self.assertTrue(PR.verifica_tt(1666.0, 0.03, ul_v=50.0)["cumple"])

    def test_the_adoption_factor_is_data(self):
        self.assertEqual(T.value("771.18_ra_factor_adopcion"), 0.5)
        self.assertEqual(T.constante("771.18_ul_v")["general"], 24.0)
        self.assertEqual(T.constante("771.18_ra_max_ohm"), 40.0)


class AdiabaticKD12(unittest.TestCase):
    def test_cu_pvc_above_300_mm2_is_103(self):
        for i_cc, t_s in ((10000.0, 1.0), (40000.0, 1.0)):
            with self.subTest(i_cc=i_cc):
                k = CT.k_material("Cu", "PVC", 400)
                self.assertEqual(k, 103.0)
                self.assertAlmostEqual(CT.seccion_minima_mm2(i_cc, t_s, k), i_cc * math.sqrt(t_s) / 103.0)

    def test_al_pvc_above_300_mm2_is_68(self):
        self.assertEqual(CT.k_material("Al", "PVC", 301), 68.0)

    def test_up_to_300_mm2_and_without_section_nothing_changes(self):
        self.assertEqual(CT.k_material("Cu", "PVC"), 115.0)
        self.assertEqual(CT.k_material("Cu", "PVC", None), 115.0)
        self.assertEqual(CT.k_material("Cu", "PVC", 300), 115.0)
        self.assertEqual(CT.k_material("Al", "PVC", 240), 76.0)
        self.assertEqual(CT.k_material("Cu", "XLPE", 400), 143.0)
        self.assertEqual(CT.k_material("Al", "XLPE"), 94.0)
        with self.assertRaises(ValueError):
            CT.k_material("Cu", "EPR")

    def test_one_lookup_in_both_modules(self):
        self.assertEqual(CO.k_adiabatico_771("pvc", "cu", 400), 103.0)
        self.assertEqual(CO.k_adiabatico_771("pvc", "cu", 95), 115.0)
        self.assertEqual(CO.k_adiabatico_771("pvc", "al"), 76.0)
        self.assertEqual(CO.k_adiabatico_771("xlpe", "cu"), 143.0)
        self.assertEqual(CO.k_adiabatico_771("pvc_sobre_300", "al"), 68.0)       # the full keys still resolve
        self.assertEqual(CO.k_adiabatico_771("epr_xlpe", "cu"), 143.0)
        with self.assertRaises(ValueError):
            CO.k_adiabatico_771("pvc", "xx")

    def test_the_i2t_check_with_the_larger_k(self):
        r = CT.verificar_i2t(40000.0, 1.0, CT.k_material("Cu", "PVC", 400), 400.0)
        self.assertEqual(r["k2s2"], (103.0 * 400.0) ** 2)
        self.assertTrue(r["cumple"])


class PeSection(unittest.TestCase):
    def test_minimum_2_5_mm2(self):
        self.assertEqual(E.seccion_pe_mm2(1.5), 2.5)                    # case s1
        self.assertEqual(CO.pe_section(1.5), 2.5)

    def test_half_goes_up_to_the_commercial_series(self):
        self.assertEqual(E.seccion_pe_mm2(95), 50)                      # case s2: 47.5 -> 50
        self.assertEqual(CO.pe_section(95), 50)
        self.assertEqual(E.seccion_pe_mm2(70), 35)
        self.assertEqual(E.seccion_pe_mm2(120), 70)
        self.assertEqual(E.seccion_pe_mm2(185), 95)
        self.assertEqual(E.seccion_pe_mm2(240), 120)

    def test_steps_up_to_35_are_unchanged(self):
        self.assertEqual([E.seccion_pe_mm2(s) for s in (2.5, 10, 16, 25, 35)], [2.5, 10, 16, 16, 16])

    def test_one_implementation_for_both_modules(self):
        for s in (1.5, 4, 16, 25, 35, 50, 95, 150, 300):
            with self.subTest(s=s):
                self.assertEqual(E.seccion_pe_mm2(s), CO.pe_section(s))
        self.assertEqual(E.seccion_pe_mm2(25, 1.5, 1.0), 24.0)          # a different material scales the step

    def test_the_series_comes_from_the_repo_data(self):
        self.assertIn(50, CO.IZ_771_16_I)


class DisconnectionTimeD25(unittest.TestCase):
    def test_tn_sectional_default_is_2_s(self):
        self.assertEqual(E.tiempo_seccional_max_s("TN"), 2.0)
        self.assertEqual(E.T_SECCIONAL_S["TN"], 2.0)

    def test_5_s_only_with_the_selectivity_flag(self):
        self.assertEqual(E.tiempo_seccional_max_s("TN", selectividad=True), 5.0)
        self.assertEqual(E.tiempo_seccional_max_s("TN", False), 2.0)

    def test_tt_sectional_is_not_affected(self):
        self.assertEqual(E.tiempo_seccional_max_s("TT"), 1.0)
        self.assertEqual(E.tiempo_seccional_max_s("TT", selectividad=True), 1.0)

    def test_one_table_in_the_json(self):
        raw = json.load(open(T.RUTA_JSON, encoding="utf-8"))
        data = raw["constantes"]["771.18.III_tiempos_desconexion_s"]
        self.assertEqual({k: [list(f) for f in v] for k, v in E.TIEMPOS_DESCONEXION_S.items()}, data)
        with open(engine_sources.join("aea_earthing.py"), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        assigned = {t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
        self.assertNotIn("TIEMPOS_DESCONEXION_S", assigned)
        self.assertNotIn("T_SECCIONAL_S", assigned)
        self.assertEqual(E.tiempo_desconexion_max_s("TN", 230), 0.2)
        self.assertEqual(E.tiempo_desconexion_max_s("TT", 400, "cc"), 0.02)


class ZsMaximumD13(unittest.TestCase):
    def test_verifica_tn_uses_the_limit_of_zs_maxima(self):
        for u0, ia in ((230.0, 160.0), (220.0, 160.0), (230.0, 30.0)):
            with self.subTest(u0=u0, ia=ia):
                r = PR.verifica_tn(1.0, ia, u0)
                self.assertEqual(r["zs_max_ohm"], E.zs_maxima(u0, ia))
                self.assertAlmostEqual(r["limite_v"] / ia, E.zs_maxima(u0, ia))
                self.assertAlmostEqual(r["limite_v"], 0.95 * u0)

    def test_case_l4(self):
        self.assertAlmostEqual(E.zs_maxima(230.0, 160.0), 1.365625)
        self.assertTrue(PR.verifica_tn(1.36, 160.0, un_v=400.0)["cumple"])      # D16: explicit 230/400 V system (the default is now 220/380 V)
        self.assertFalse(PR.verifica_tn(1.40, 160.0, un_v=400.0)["cumple"])        # passed with the old U0/Ia = 1.4375 limit

    def test_memo_zs_max_uses_the_same_function(self):
        tag = "T1"
        circ = {tag: {"description": "receptacles", "parent_tag": ""}}
        dat = {"In": 16, "Ib": 10.0, "S": 2.5, "icu": 10, "disp": "MCB"}
        det = {tag: {"tipo": "tomacorrientes", "kind": "rcbo", "topologia": "single", "cumple": True, "iz_a": 24.0, "icc_min_a": 500.0,
                     "s_termica_mm2": 2.5, "largo_m": 10.0, "ruta": [], "padre": ""}}
        zs = BM._circuit(tag, circ, dat, det, {}, 30.0, "TN", 6000.0)["diferencial"]["zs_max_ohm"]
        self.assertEqual(zs, round(E.zs_maxima(SV.board_u0({}), 0.03), 0))      # D16: U0 of the board system (default 220/380 V)


if __name__ == "__main__":
    unittest.main()
