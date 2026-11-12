"""CAL-021 · aea_special_locations — Baños (701) y alimentación de vehículos eléctricos (722).

ESTADO: BORRADOR — pendiente de validación por el usuario.

OBJETIVO
    Cálculos y criterios numéricos de AEA 90364-7-701 (Ed. 2012) y AEA 90364-7-722 (Ed. 2018).

FÓRMULAS
    701: B = μ0·i/(2π·R), μ0 = 4π·10⁻⁷ H/m, límite B ≤ 2,5·10⁻⁵ T
         Radio de la zona 2 con tabique de ancho a: r = 0,60 − a [m]
    722: factor de demanda = demanda máxima/carga instalada
         carga múltiple: ≤ 8 tomacorrientes y circuito ≥ mitad de las bocas a corriente máxima
         y ≥ 10 A
         diferencial: clase A ≤ 30 mA con detección de c.c. > 6 mA, o clase B
         IP ≥ 44 (55 en exterior según el caso)

UNIDADES
    I [A], distancia [m], B [T], ancho [m].

LIMITACIONES
    - Los requisitos IP, IRAM 2071 y de modo de carga se devuelven como constantes/avisos;
      la elección final es de proyecto.

NORMA DE REFERENCIA
    AEA 90364-7-701 (2012); AEA 90364-7-722 (2018).  [VERIFICAR]
"""
import math
from epc_aea90364._validate import num as _num
from epc_aea90364 import aea_tables as T

__version__ = "0.1.0"

MU0 = 4.0e-7 * math.pi   # physics constant: stays in the code

# Los valores normativos viven en `aea_tables.json` (una sola fuente, ADR-0012); los nombres de módulo se arman desde allí al usarlos (`__getattr__` de módulo, PEP 562)
# y se renuevan con `aea_tables.limpiar_cache_tablas()`. Forma de cada uno:
#   B_LIM_T [T]  RADIO_ZONA2_M [m]  MAX_OUTLETS_LOAD_MULTIPLE (int)  I_MIN_LOAD_MULTIPLE_TO [A]  IDN_DIFERENCIAL_EV_MA [mA]  I_CC_DETECCION_MA [mA]
_BUILD = {
    "B_LIM_T": lambda d: d["constantes"]["701_b_lim_t"]["valor"],
    "RADIO_ZONA2_M": lambda d: d["constantes"]["701_radio_zona2_m"]["valor"],
    "MAX_OUTLETS_LOAD_MULTIPLE": lambda d: d["constantes"]["722_carga_multiple"]["valor"]["max_tomas"],
    "I_MIN_LOAD_MULTIPLE_TO": lambda d: d["constantes"]["722_carga_multiple"]["valor"]["i_min_a"],
    "IDN_DIFERENCIAL_EV_MA": lambda d: d["constantes"]["ev_idn_diferencial_ma"]["valor"],
    "I_CC_DETECCION_MA": lambda d: d["constantes"]["ev_i_cc_deteccion_ma"]["valor"],
}


def _g(nombre):
    return T.derived(f"{__name__}.{nombre}", _BUILD[nombre])


def __getattr__(nombre):
    if nombre in _BUILD:
        return _g(nombre)
    raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")


def induccion_conductor_t(i_a, distancia_m):
    """B = μ0·i/(2π·R) [T] a la distancia R del conductor (701)."""
    _num(i_a, "i_a")
    _num(distancia_m, "distancia_m", 0.0, True)
    return MU0 * i_a / (2 * math.pi * distancia_m)


def induccion_admisible(i_a, distancia_m):
    """True si B ≤ 2,5·10⁻⁵ T."""
    return induccion_conductor_t(i_a, distancia_m) <= _g("B_LIM_T")


def radio_zona2_con_tabique_m(ancho_tabique_m):
    """Radio de la zona 2 [m] = 0,60 − a (701)."""
    _num(ancho_tabique_m, "ancho_tabique_m")
    return max(0.0, _g("RADIO_ZONA2_M") - ancho_tabique_m)


def factor_demand(demanda_max, carga_instalada):
    """722: factor de demanda = demanda máxima/carga instalada (mismas unidades)."""
    _num(demanda_max, "demanda_max")
    _num(carga_instalada, "carga_instalada", 0.0, True)
    return demanda_max / carga_instalada


def load_multiple_complies(n_tomas, n_bocas, i_circuito_a, i_max_boca_a):
    """722: ≤ 8 tomas; circuito ≥ ½·(bocas·I_máx) y ≥ 10 A. Devuelve dict."""
    _num(n_tomas, "n_tomas", 1)
    _num(n_bocas, "n_bocas", 1)
    _num(i_circuito_a, "i_circuito_a")
    _num(i_max_boca_a, "i_max_boca_a", 0.0, True)
    r = {"tomas_ok": n_tomas <= _g("MAX_OUTLETS_LOAD_MULTIPLE"),
         "mitad_bocas_ok": i_circuito_a >= T.value("722_carga_multiple")["fraccion_bocas"] * n_bocas * i_max_boca_a,
         "minimo_10a_ok": i_circuito_a >= _g("I_MIN_LOAD_MULTIPLE_TO")}
    r["cumple"] = all(r.values())
    return r
