"""CAL-015 · aea_voltage_drop — Caída de tensión por tablas y coeficientes de AEA 771/770.

ESTADO: BORRADOR — pendiente de validación por el usuario.

OBJETIVO
    Complementar `voltage_drop.py` (fórmula general con R y X del catálogo) con los
    métodos simplificados y los LÍMITES normativos de AEA 90364-7-771 (§19.7) y
    AEA 90364-7-770 (§15.6): método de la Tabla 771.19.IV (V/A·km), método de los
    coeficientes GDC y límites por tipo de circuito. NO repite ΔU = k·I·L·(R cosφ + X senφ):
    para eso usar `voltage_drop.caida_tension`.

FÓRMULAS
    Método a) tabla: ΔU = (V/A·km)(S)·I·L[km]          (monofásico, cosφ 0,8; Tabla 771.19.IV)
    Método c) GDC:   ΔU = GDC·I·L/S                     (L [m], S [mm²]; Tabla de coeficientes GDC)
    Longitud máx.:   L = ΔU_adm·S/(GDC·I)
    Sección mín.:    S = GDC·I·L/ΔU_adm
    Carga en el extremo (iluminación): 66 % (771) o 2/3 (770) de la corriente total;
                     tomacorrientes: 100 % de la corriente.
    Límites: terminales 3 % (iluminación y tomas); motores 5 % régimen / 15 % arranque;
             seccionales ≤ 1 %.  Total = ΔU_seccional + ΔU_terminal.

HIPÓTESIS
    - cosφ 0,8 (carga común) o 0,3 (arranque); cables a 70 °C (ver nota de la norma).
    - GDC en V·mm²/(A·m) para L en metros y S en mm².

UNIDADES
    I [A], L [m], S [mm²], ΔU [V], % sobre Un.

LIMITACIONES
    - Para otros cosφ o secciones fuera de 1,5–120 mm² usar `voltage_drop.caida_tension`.
    - GDC de arranque definido para 1,5–25 mm² y 35–70 mm².

NORMA DE REFERENCIA
    AEA 90364-7-771 §19.7 (Tabla 771.19.IV); AEA 90364-7-770 §15.6.  [VERIFICAR]
"""
import math
from epc_calc_common import aea_tables as T
from epc_calc_common._validate import num as _num

__version__ = "0.1.0"

# Los valores viven en `aea_tables.json` y los nombres se arman desde allí al usarlos (`__getattr__` de módulo, como en aea_conductors):
#   VA_KM_TABLA     Tabla 771.19.IV: caída unitaria [V/(A·km)] monofásica, cosφ 0,8: {S: valor}
#   GDC_COMUN       GDC [V·mm²/(A·m)]: {(material, fases): valor}
#   GDC_ARRANQUE    GDC de arranque: {(material, fases): (S ≤ corte, corte < S ≤ máximo)}
#   LIMITES_PCT     límites de caída [%] por tipo de circuito
#   FRACCION_ILUM_771 / FRACCION_ILUM_770   fracción de la corriente de iluminación concentrada en el extremo
#   GDC_ARRANQUE_CORTE_MM2 / GDC_ARRANQUE_MAX_MM2   secciones de corte (25) y máxima (70) del GDC de arranque
#   U_MONO_DEFECTO_V / U_TRI_DEFECTO_V   tensión nominal por defecto
def _gdc(d, clave, conv):
    return {(k.split("|")[0], int(k.split("|")[1])): conv(v) for k, v in d["constantes"][clave].items()}


_BUILD = {
    "VA_KM_TABLA": lambda d: {T.numeric_key(s): v for s, v in d["constantes"]["771.19.IV_caida_unitaria_va_km"].items()},
    "GDC_COMUN": lambda d: _gdc(d, "771.19_gdc_comun", lambda v: v),
    "GDC_ARRANQUE": lambda d: _gdc(d, "771.19_gdc_arranque", tuple),
    "LIMITES_PCT": lambda d: dict(d["constantes"]["771.19_limites_caida_pct"]),
    "FRACCION_ILUM_771": lambda d: d["constantes"]["771.9.1_fraccion_iluminacion"]["valor"]["vivienda"],
    "FRACCION_ILUM_770": lambda d: d["constantes"]["770.8.I_fraccion_iluminacion"]["valor"]["numerador"] / d["constantes"]["770.8.I_fraccion_iluminacion"]["valor"]["denominador"],
    "GDC_ARRANQUE_CORTE_MM2": lambda d: d["constantes"]["771.19_gdc_arranque_secciones_mm2"]["valor"]["corte"],
    "GDC_ARRANQUE_MAX_MM2": lambda d: d["constantes"]["771.19_gdc_arranque_secciones_mm2"]["valor"]["maximo"],
    "U_MONO_DEFECTO_V": lambda d: float(d["constantes"]["tension_nominal_defecto_v"]["valor"]["mono"]),
    "U_TRI_DEFECTO_V": lambda d: float(d["constantes"]["tension_nominal_defecto_v"]["valor"]["tri"]),
}


def _g(nombre):
    return T.derived(f"{__name__}.{nombre}", _BUILD[nombre])


def __getattr__(nombre):
    if nombre in _BUILD:
        return _g(nombre)
    raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")


def _un_defecto(fases):
    """Tensión nominal por defecto [V]: monofásica o trifásica."""
    return _g("U_MONO_DEFECTO_V") if fases == 1 else _g("U_TRI_DEFECTO_V")


def drop_unit_table(seccion_mm2):
    """V/(A·km) de la Tabla 771.19.IV (monofásico, cosφ 0,8)."""
    tabla = _g("VA_KM_TABLA")
    if seccion_mm2 not in tabla:
        raise ValueError(f"sección {seccion_mm2} no está en la Tabla 771.19.IV: {sorted(tabla)}")
    return tabla[seccion_mm2]


def drop_by_table(i_a, longitud_m, seccion_mm2, un_v=None):
    """ΔU = (V/A·km)·I·L[km]. Devuelve {'delta_u_v','delta_u_pct'}."""
    _num(i_a, "i_a")
    _num(longitud_m, "longitud_m")
    un_v = _un_defecto(1) if un_v is None else un_v      # the single-phase default of aea_tables.json (220 V)
    _num(un_v, "un_v", 0.0, True)
    du = drop_unit_table(seccion_mm2) * i_a * longitud_m / 1000.0
    return {"delta_u_v": du, "delta_u_pct": 100.0 * du / un_v}


def coeficiente_gdc(material, fases, arranque=False, seccion_mm2=None):
    """GDC [V·mm²/(A·m)]. En arranque (cosφ 0,3) requiere seccion_mm2 (≤70)."""
    clave = (material.lower(), fases)
    comun = _g("GDC_COMUN")
    if clave not in comun:
        raise ValueError("material 'cu'|'al' y fases 1|3")
    if not arranque:
        return comun[clave]
    _num(seccion_mm2, "seccion_mm2", 0.0, True)
    maximo = _g("GDC_ARRANQUE_MAX_MM2")
    if seccion_mm2 > maximo:
        raise ValueError(f"GDC de arranque definido hasta {maximo} mm²")
    return _g("GDC_ARRANQUE")[clave][0 if seccion_mm2 <= _g("GDC_ARRANQUE_CORTE_MM2") else 1]


def caida_gdc(i_a, longitud_m, seccion_mm2, material="cu", fases=1, un_v=None, arranque=False):
    """ΔU = GDC·I·L/S. un_v por defecto 220 (mono) o 380 (tri)."""
    _num(i_a, "i_a")
    _num(longitud_m, "longitud_m")
    _num(seccion_mm2, "seccion_mm2", 0.0, True)
    g = coeficiente_gdc(material, fases, arranque, seccion_mm2)
    un = un_v if un_v is not None else _un_defecto(fases)
    du = g * i_a * longitud_m / seccion_mm2
    return {"delta_u_v": du, "delta_u_pct": 100.0 * du / un}


def longitud_maxima_gdc(i_a, seccion_mm2, du_adm_pct, material="cu", fases=1, un_v=None, arranque=False):
    """L = ΔU_adm·S/(GDC·I) [m]."""
    _num(i_a, "i_a", 0.0, True)
    _num(du_adm_pct, "du_adm_pct", 0.0, True)
    g = coeficiente_gdc(material, fases, arranque, seccion_mm2)
    un = un_v if un_v is not None else _un_defecto(fases)
    return (du_adm_pct / 100.0 * un) * seccion_mm2 / (g * i_a)


def seccion_minima_gdc(i_a, longitud_m, du_adm_pct, material="cu", fases=1, un_v=None):
    """S = GDC·I·L/ΔU_adm [mm²] (régimen, cosφ 0,8)."""
    _num(i_a, "i_a")
    _num(longitud_m, "longitud_m")
    _num(du_adm_pct, "du_adm_pct", 0.0, True)
    un = un_v if un_v is not None else _un_defecto(fases)
    return coeficiente_gdc(material, fases) * i_a * longitud_m / (du_adm_pct / 100.0 * un)


def limite_caida_pct(tipo):
    """Límite [%] por tipo: iluminacion, tomacorrientes, motor_regimen, motor_arranque, seccional."""
    limites = _g("LIMITES_PCT")
    if tipo not in limites:
        raise ValueError(f"tipo debe ser uno de {sorted(limites)}")
    return limites[tipo]


def corriente_extremo(i_total_a, tipo, norma="771"):
    """Corriente equivalente concentrada en el extremo: iluminación 66 % (771) o 2/3 (770); tomas 100 %."""
    _num(i_total_a, "i_total_a")
    if tipo == "iluminacion":
        return i_total_a * (_g("FRACCION_ILUM_770") if norma == "770" else _g("FRACCION_ILUM_771"))
    if tipo == "tomacorrientes":
        return i_total_a
    raise ValueError("tipo debe ser 'iluminacion' o 'tomacorrientes'")


def caida_disponible_terminal_pct(limite_total_pct, caida_seccional_pct):
    """Margen del circuito terminal = límite total − caída ya consumida aguas arriba (≥ 0)."""
    _num(limite_total_pct, "limite_total_pct")
    _num(caida_seccional_pct, "caida_seccional_pct")
    return max(0.0, limite_total_pct - caida_seccional_pct)


def verify_drop(caida_pct, tipo):
    """True si la caída no supera el límite del tipo."""
    _num(caida_pct, "caida_pct")
    return caida_pct <= limite_caida_pct(tipo)
