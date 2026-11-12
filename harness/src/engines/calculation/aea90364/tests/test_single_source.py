"""Single source of truth (ENG-13): the norm values of conductors, ampacity, voltage drop, route, demand and panel thermal live in
`aea_tables.json` and the modules build their public names from it. These tests catch a literal copy coming back."""
import ast
import copy
import json
import math
import os
import engine_sources
import tempfile
import unittest

from epc_aea90364 import aea_ampacity as A
from epc_aea90364 import aea_conductors as C
from epc_aea90364 import aea_demand as D
from epc_aea90364 import aea_earthing as EA
from epc_aea90364 import aea_icc_decay as ID
from epc_aea90364 import aea_icc_factors as IF
from epc_aea90364 import aea_panel_thermal as P
from epc_aea90364 import aea_route as R
from epc_aea90364 import aea_special_locations as SL
from epc_aea90364 import aea_tables as T
from epc_aea90364 import aea_voltage_drop as V
from epc_aea90364 import board_memo as BM
from epc_aea90364 import cable_thermal as CT
from epc_aea90364 import short_circuit as SC

SRC = os.path.dirname(os.path.abspath(T.__file__))
MODULES = {C: "aea_conductors.py", A: "aea_ampacity.py", R: "aea_route.py", V: "aea_voltage_drop.py", D: "aea_demand.py", P: "aea_panel_thermal.py",
           EA: "aea_earthing.py", CT: "cable_thermal.py", BM: "board_memo.py", SC: "short_circuit.py", IF: "aea_icc_factors.py", ID: "aea_icc_decay.py",
           SL: "aea_special_locations.py"}


def _raw():
    with open(T.RUTA_JSON, encoding="utf-8") as f:
        return json.load(f)


def _num(k):
    f = float(k)
    return int(f) if f == int(f) else f


def _inf(v):
    return math.inf if v is None else v


def _expected(raw):
    """Every converted name, built here by hand from the raw JSON (independent of the loader helpers)."""
    c, t = raw["constantes"], raw["tablas_capacidad"]
    imp = c["impedancias_estandar"]
    pvc_cu = next(b for b in t["771.16.I"]["bloques"] if b["aislacion"] == "pvc")["filas"]["cu"]
    gdc = lambda key, conv: {(k.split("|")[0], int(k.split("|")[1])): conv(v) for k, v in c[key].items()}
    frac770 = c["770.8.I_fraccion_iluminacion"]["valor"]
    return {
        C: {"SECCIONES_MIN_MM2": dict(c["771.13.I_secciones_minimas_mm2"]), "PEN_MIN_MM2": dict(c["771.13_pen_minima_mm2"]),
            "K_TABLA_771": {tuple(k.split("|")): v for k, v in c["771.19.II_k_adiabatico"].items()},
            "IZ_771_16_I": {_num(s): tuple(v) for s, v in pvc_cu.items()},
            "R20_CU_OHM_KM": {_num(s): v for s, v in imp["r20_ohm_km"].items()},
            "ALFA_CU": c["conductor_alfa_cu"]["valor"], "X_CABLE_OHM_KM": imp["reactancia_ohm_km"],
            "FACTORS_HARMONICS": tuple((_inf(a), b, d) for a, b, d in c["771.16.XIII_factores_armonicos"]["valor"])},
        A: {"SECCION_MIN_AL_MM2": c["771.13_seccion_minima_al_mm2"]["valor"],
            "ALFA": {"cu": c["conductor_alfa_cu"]["valor"], "al": c["conductor_alfa_al"]["valor"]},
            "R20_AL_OHM_KM": {_num(s): v for s, v in c["conductor_r20_al_ohm_km"]["valor"].items()},
            "TEMP_CONDUCTOR_C": {k: float(v) for k, v in t["771.16.III"]["referencia"]["temp_conductor_c"].items()}},
        R: {"KINDS": {k: tuple(v) for k, v in c["ruta_tipos_tramo_metodos"]["valor"].items()},
            "DEPTH_REFERENCE_M": float(t["771.16.V"]["referencia"]["profundidad_m"])},
        V: {"VA_KM_TABLA": {_num(s): v for s, v in c["771.19.IV_caida_unitaria_va_km"].items()},
            "GDC_COMUN": gdc("771.19_gdc_comun", lambda v: v), "GDC_ARRANQUE": gdc("771.19_gdc_arranque", tuple),
            "LIMITES_PCT": dict(c["771.19_limites_caida_pct"]),
            "FRACCION_ILUM_771": c["771.9.1_fraccion_iluminacion"]["valor"]["vivienda"],
            "FRACCION_ILUM_770": frac770["numerador"] / frac770["denominador"]},
        D: {"U_MONO_V": c["tension_nominal_defecto_v"]["valor"]["mono"], "U_TRI_V": c["tension_nominal_defecto_v"]["valor"]["tri"],
            "VA_BOCA_VIVIENDA": c["771.9.1_va_boca_vivienda"]["valor"], "VA_BOCA_770": c["770.8.I_va_boca"]["valor"],
            "VA_TUG": c["771.9_va_tug"]["valor"], "VA_TUE": c["771.9_va_tue"]["valor"],
            "COEF_GRADO_771": dict(c["770_coef_grado_771"]), "COEF_CIRCUITS_770": tuple(tuple(x) for x in c["770_coef_circuitos"]),
            "DESEQUILIBRIO_MAX_PCT": c["770.8.3.4_desequilibrio_max_pct"]["valor"],
            "_GRADOS_771": {k: tuple((_inf(a), b, d) for a, b, d in f) for k, f in c["771.8_grados_electrificacion"]["valor"].items()},
            "_CONJUNTOS_771_III": tuple(tuple(x) for x in c["771.9.III_conjuntos_coeficientes"]["valor"])},
        P: {"K_E": c["770-B_k_e"]["valor"], "K_CABLEADO": c["770-B_k_cableado"]["valor"],
            "_K_CIRCUITOS": tuple(tuple(x) for x in c["770-B.XII_k_circuitos"]["valor"]),
            "_PD_POLO": tuple(tuple(x) for x in c["770-B.XI_pd_polo_w"]["valor"]),
            "_PDC_DIF": tuple(tuple(x) for x in c["770-B.X_pdc_diferencial_a"]["valor"])},
        # ENG-14: protection / earthing / short-circuit family
        EA: {"UL_V": c["771.18_ul_v"]["general"], "UL_COL1_V": c["771.18_ul_v"]["col1"], "RA_MAX_OHM": c["771.18_ra_max_ohm"],
             "TIEMPOS_DESCONEXION_S": {e: tuple(tuple(f) for f in fs) for e, fs in c["771.18.III_tiempos_desconexion_s"].items()},
             "T_SECCIONAL_S": dict(c["771.18_t_seccional_s"])},
        CT: {"K_ADIABATICO": {(m, a): c["771.19.II_k_adiabatico"][f"{i}|{m.lower()}"] for m in ("Cu", "Al") for a, i in (("PVC", "pvc_hasta_300"), ("XLPE", "epr_xlpe"))},
             "T_ADIABATICO_MAX_S": c["cable_t_adiabatico_max_s"]["valor"], "T_CORTO_S": c["cable_t_corto_s"]["valor"]},
        BM: {"K_MAG": {k: tuple(v) for k, v in c["curva_disparo_magnetico_k"]["valor"].items()}, "RATIO_TERMICO": c["termico_ratio_min"]["valor"]},
        SC: {"C_MAX_BT_TOL_6": imp["c_fuente_max"], "C_MAX_BT_TOL_10": c["icc_c_max_tol_10"]["valor"], "C_MIN_BT": imp["c_tension_min"],
             "TEMP_MIN_C": c["icc_temp_min_c"]["valor"], "XR_RED_DEFECTO": c["icc_xr_red_defecto"]["valor"],
             "UMBRAL_MOTORES_DESPRECIABLE": c["icc_motores_despreciable_pct"]["valor"] / 100.0},
        IF: {"C_MAX_RED": c["icc_c_max_tol_10"]["valor"], "RIGIDO_MAX_U_RATIO": c["icc_rigido_max_u_ratio"]["valor"],
             "LIM_MOTORES_I_PCT": c["icc_motores_despreciable_pct"]["valor"], "LIM_MOTORES_SUMA_IRM_PCT": c["icc_motores_suma_irm_pct"]["valor"]},
        ID: {"U_FMAX": {(k.split("|")[0], int(k.split("|")[1])): v for k, v in c["icc_u_fmax"]["valor"].items()}},
        SL: {"B_LIM_T": c["701_b_lim_t"]["valor"], "RADIO_ZONA2_M": c["701_radio_zona2_m"]["valor"],
             "MAX_OUTLETS_LOAD_MULTIPLE": c["722_carga_multiple"]["valor"]["max_tomas"], "I_MIN_LOAD_MULTIPLE_TO": c["722_carga_multiple"]["valor"]["i_min_a"],
             "IDN_DIFERENCIAL_EV_MA": c["ev_idn_diferencial_ma"]["valor"], "I_CC_DETECCION_MA": c["ev_i_cc_deteccion_ma"]["valor"]},
    }


def _typed(x):
    """Value plus the type of every element and key, so int/float and tuple/list differences are visible."""
    if isinstance(x, dict):
        return ("dict", [(_typed(k), _typed(v)) for k, v in x.items()])
    if isinstance(x, (list, tuple)):
        return (type(x).__name__, [_typed(v) for v in x])
    return (type(x).__name__, x)


class NamesComeFromJson(unittest.TestCase):
    def test_every_name_equals_the_json_content(self):
        for mod, names in _expected(_raw()).items():
            for name, want in names.items():
                with self.subTest(module=mod.__name__, name=name):
                    self.assertEqual(_typed(getattr(mod, name)), _typed(want))

    def test_names_are_not_assigned_in_the_source(self):
        """No module-level assignment of a converted name: a literal copy would shadow the JSON."""
        for mod, fname in MODULES.items():
            with open(engine_sources.join(fname), encoding="utf-8") as f:
                tree = ast.parse(f.read())
            assigned = {t.id for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign))
                        for t in (n.targets if isinstance(n, ast.Assign) else [n.target]) if isinstance(t, ast.Name)}
            for name in _expected(_raw())[mod]:
                with self.subTest(module=fname, name=name):
                    self.assertNotIn(name, assigned)

    def test_unknown_name_still_raises_attribute_error(self):
        for mod in MODULES:
            with self.assertRaises(AttributeError):
                getattr(mod, "NO_SUCH_NAME")


class ChangingTheJsonChangesTheCalculation(unittest.TestCase):
    """Point the loader at a modified copy of the JSON: results must follow it (no value left in the code)."""

    def setUp(self):
        self.raw = _raw()
        self.old_path = T.RUTA_JSON

    def tearDown(self):
        T.RUTA_JSON = self.old_path
        T.limpiar_cache_tablas()

    def _use(self, mutate):
        data = copy.deepcopy(self.raw)
        mutate(data)
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        self.addCleanup(os.remove, path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        T.RUTA_JSON = path
        T.limpiar_cache_tablas()

    def test_constants_reach_the_functions(self):
        def mutate(d):
            c = d["constantes"]
            c["771.13.I_secciones_minimas_mm2"]["pe"] = 6.0
            c["771.19_limites_caida_pct"]["seccional"] = 2.0
            c["771.19_gdc_comun"]["cu|1"] = 0.05
            c["771.19_gdc_arranque_secciones_mm2"]["valor"]["maximo"] = 95
            c["771.16_factor_clase5"]["valor"] = 0.9
            c["771.16.XIII_factores_armonicos"]["valor"][0][1] = 0.5
            c["770.8.I_va_boca"]["valor"] = 100.0
            c["771.9_va_tug"]["valor"] = 1000.0
            c["770.8.3.4_desequilibrio_max_pct"]["valor"] = 10.0
            c["motor_alimentador_factor_mayor"]["valor"] = 2.0
            c["770-B_k_cableado"]["valor"] = 0.5
            c["770-B.XI_pd_polo_w"]["valor"][0][1] = 9.0
            c["neutro_seccion_igual_hasta_mm2"]["valor"] = 25
            c["771.16_metodos_tabla_fuente"]["valor"]["C"]["columna"] = "E_{n}x"
            c["ruta_tipos_tramo_metodos"]["valor"]["tray_solid"] = ["F", "F"]
            c["tension_nominal_defecto_v"]["valor"]["mono"] = 230.0
        self._use(mutate)
        self.assertEqual(C.section_min_circuit("pe"), 6.0)
        self.assertEqual(V.limite_caida_pct("seccional"), 2.0)
        self.assertEqual(V.coeficiente_gdc("cu", 1), 0.05)
        self.assertEqual(V.coeficiente_gdc("cu", 1, True, 80), 0.0205)
        self.assertEqual(T.iz_corregida(100.0, 1, True), 90.0)
        self.assertEqual(C.factor_harmonics(10)["factor"], 0.5)
        self.assertEqual(D.msd_lighting_general(10, "770"), 10 * 100.0 * 2.0 / 3.0)
        self.assertEqual(D.msd_circuits(n_tug=1), 1000.0)
        self.assertFalse(D.imbalance_phases([10, 8])["cumple"])
        self.assertEqual(D.corriente_alimentador_motores([10, 2]), 22.0)
        self.assertEqual(P.potencia_tablero_w(100.0), 150.0)
        self.assertEqual(P.potencia_disipada_polo_w(5), 9.0)
        self.assertEqual(C.neutral_section(25), 25)
        self.assertEqual(A._fuente({"metodo": "C", "aislacion": "pvc"}, 3)[2], "E_3x")
        self.assertEqual(R.KINDS["tray_solid"], ("F", "F"))
        self.assertEqual(V.caida_gdc(10, 10, 10)["delta_u_pct"], 100.0 * 0.05 * 10 * 10 / 10 / 230.0)

    def test_protection_earthing_short_circuit_constants_reach_the_functions(self):
        def mutate(d):
            c = d["constantes"]
            c["771.18_ul_v"]["general"] = 12.0
            c["771.18_ra_max_ohm"] = 10.0
            c["771.18_ra_factor_adopcion"]["valor"] = 0.25
            c["771.18_t_seccional_s"]["TN"] = 3.0
            c["771.18_t_seccional_selectividad_tn_s"]["valor"] = 7.0
            c["771.18.III_tiempos_desconexion_s"]["TN"][1][1] = 0.5
            c["771.19.II_k_adiabatico"]["pvc_sobre_300|cu"] = 99.0
            c["771.19.II_k_aislaciones"]["valor"]["pvc"]["limite_mm2"] = 150
            c["cable_t_corto_s"]["valor"] = 0.5
            c["curva_disparo_magnetico_k"]["valor"]["C"] = [4, 12]
            c["termico_ratio_min"]["valor"] = 3.0
            c["icc_motores_despreciable_pct"]["valor"] = 10.0
            c["icc_factor_kt"]["valor"]["k"] = 1.0
            c["icc_factor_kappa"]["valor"]["base"] = 1.0
            c["701_radio_zona2_m"]["valor"] = 1.0
            c["722_carga_multiple"]["valor"]["max_tomas"] = 2
            c["descargas_radio_captacion_factor_altura"]["valor"] = 1.0
            c["impedancias_estandar"]["c_tension_min"] = 0.9
        self._use(mutate)
        self.assertEqual(EA.ra_maxima(1.0)["adoptada"], 3.0)                         # min(0.25 * 12 / 1, 10)
        self.assertEqual(EA.tiempo_seccional_max_s("TN"), 3.0)
        self.assertEqual(EA.tiempo_seccional_max_s("TN", selectividad=True), 7.0)
        self.assertEqual(EA.tiempo_desconexion_max_s("TN", 230), 0.5)
        self.assertEqual(CT.k_material("Cu", "PVC", 200), 99.0)
        self.assertEqual(CT._advertencias_tiempo(0.3)[0][:9], "t = 0.3 s")
        self.assertEqual(BM.curve_band(10, "C")["max"][2][0], 120)
        self.assertEqual(SC.motors_negligible(0.1, 1.0), True)
        self.assertEqual(SC.factor_kt(0.0, 1.0), 1.0)
        self.assertEqual(SC.factor_kappa(1.0, 0.0), 1.0)
        self.assertEqual(SL.radio_zona2_con_tabique_m(0.0), 1.0)
        self.assertFalse(SL.load_multiple_complies(3, 1, 20, 1)["tomas_ok"])
        self.assertAlmostEqual(EA.zs_maxima(230, 100), 0.9 * 230 / 100)

    def test_tables_reach_the_names(self):
        def mutate(d):
            d["tablas_capacidad"]["771.16.I"]["bloques"][0]["filas"]["cu"]["4"] = [1, 2]
            d["tablas_capacidad"]["771.16.V"]["referencia"]["profundidad_m"] = 0.9
        self._use(mutate)
        self.assertEqual(C.iz_admisible(4, 2), 1)
        self.assertEqual(R.DEPTH_REFERENCE_M, 0.9)


if __name__ == "__main__":
    unittest.main()
