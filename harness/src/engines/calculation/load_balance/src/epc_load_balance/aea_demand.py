"""CAL-014 · aea_demand — Demanda de potencia máxima simultánea (DPMS) y corrientes de proyecto.

ESTADO: BORRADOR — pendiente de validación por el usuario.

OBJETIVO
    Determinar el grado de electrificación, la DPMS de un inmueble (viviendas, oficinas,
    locales) y la corriente de proyecto I_B, con los criterios de AEA 90364-7-771 (Ed. 2006)
    y de su sucesora AEA 90364-7-770 (Ed. 2017). Incluye alimentador de motores, reducción
    por agrupamiento en paralelo y desequilibrio entre fases.

FÓRMULAS (numeración de la norma entre corchetes)
    DPMS total = DPMS(circuitos de uso general, por grado) + DPMS(cargas específicas)  [771.9 / 770.8]
    Iluminación general (771.9.1): 66 % de n·150 VA (viviendas), 100 % (oficinas/locales);
                       (770.8.I):  2/3 de n·60 VA.
    TUG: 2200 VA por circuito; TUE: 3300 VA por circuito.
    DPMS = Σ(circuitos) · coeficiente de simultaneidad (Tablas 771.9.II / 770.8.II / 771.9.III)
    I_B monofásica = DPMS/220 ; trifásica = DPMS/(√3·380)
    Desequilibrio de fases = (Imax − Imin)/Imax ≤ 30 % [770.8.3.4]
    Alimentador de motores: I ≥ 1,25·In(mayor) + Σ In(resto)·fs
    Paralelo: fs = 1 (2 y 4 cables/fase), 0,8 en otros casos y multipolares; 0,85 por radiación solar.

HIPÓTESIS
    - Tensiones nominales 220 V / 380 V (AEA 771/770).
    - El grado de electrificación se decide por superficie; la potencia de la tabla
      (kVA) se devuelve como referencia y no condiciona el grado.
    - Los coeficientes por grado (771) y por cantidad de circuitos (770) se aplican
      al conjunto de circuitos de uso general, no a los específicos (TUE).

UNIDADES
    Superficie [m²], potencia [VA], corriente [A].

LIMITACIONES
    - Edificios en propiedad horizontal: el 771.9.4.2 es transitorio; se codifica solo la Tabla 771.9.III.
    - La norma 770 define el grado solo por superficie (cubierta + 50 % semicubierta).

NORMA DE REFERENCIA
    AEA 90364-7-771 (2006) §8 (grados), §9 (DPMS), §13; AEA 90364-7-770 (2017) §7 (grados), §8 (DPMS); IEC 60364-5-52 (paralelo).  [VERIFICAR]
"""
import math
from epc_calc_common import aea_tables as T
from epc_calc_common._validate import num as _num

__version__ = "0.1.0"

# Los valores viven en `aea_tables.json` y los nombres se arman desde allí al usarlos (`__getattr__` de módulo, como en aea_conductors):
#   U_MONO_V / U_TRI_V     tensión nominal por defecto [V]            VA_BOCA_VIVIENDA / VA_BOCA_770   potencia por boca [VA]   (771.9.1 / 770.8.I)
#   VA_TUG / VA_TUE        potencia por circuito de uso general / específico [VA]
#   COEF_GRADO_771         Tabla 771.9.II: {grado: coeficiente}       COEF_CIRCUITS_770   Tabla 770.8.II: ((circuitos mínimos, coeficiente), ...)
#   DESEQUILIBRIO_MAX_PCT  770.8.3.4 [%]
#   _GRADOS_771            {tipo: ((superficie límite [m²], grado, DPMS de referencia [kVA]), ...)}; el último límite es math.inf (null en el JSON)
#   _GRADOS_770            ((superficie límite [m²], grado), ...) con el último límite math.inf
#   _CONJUNTOS_771_III     Tabla 771.9.III: ((unidades mínimas, Mín/Medio, Elev/Sup), ...)
def _inf(v):
    return math.inf if v is None else v


def _c(d, clave):
    return d["constantes"][clave]


_BUILD = {
    "U_MONO_V": lambda d: float(_c(d, "tension_nominal_defecto_v")["valor"]["mono"]),
    "U_TRI_V": lambda d: float(_c(d, "tension_nominal_defecto_v")["valor"]["tri"]),
    "VA_BOCA_VIVIENDA": lambda d: float(_c(d, "771.9.1_va_boca_vivienda")["valor"]),
    "VA_BOCA_770": lambda d: float(_c(d, "770.8.I_va_boca")["valor"]),
    "VA_TUG": lambda d: float(_c(d, "771.9_va_tug")["valor"]),
    "VA_TUE": lambda d: float(_c(d, "771.9_va_tue")["valor"]),
    "COEF_GRADO_771": lambda d: dict(_c(d, "770_coef_grado_771")),
    "COEF_CIRCUITS_770": lambda d: tuple(tuple(x) for x in _c(d, "770_coef_circuitos")),
    "DESEQUILIBRIO_MAX_PCT": lambda d: float(_c(d, "770.8.3.4_desequilibrio_max_pct")["valor"]),
    "_GRADOS_771": lambda d: {tipo: tuple((_inf(lim), grado, kva) for lim, grado, kva in filas) for tipo, filas in _c(d, "771.8_grados_electrificacion")["valor"].items()},
    "_GRADOS_770": lambda d: tuple((_inf(lim), grado) for lim, grado in _c(d, "770.7.I_grados_electrificacion")["valor"]),
    "_CONJUNTOS_771_III": lambda d: tuple(tuple(x) for x in _c(d, "771.9.III_conjuntos_coeficientes")["valor"]),
}


def _g(nombre):
    return T.derived(f"{__name__}.{nombre}", _BUILD[nombre])


def __getattr__(nombre):
    if nombre in _BUILD:
        return _g(nombre)
    raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")


def grade_electrification_771(tipo, superficie_m2):
    """Grado según 771 (Tablas 771.8.I viviendas, 771.8.IV oficinas y locales, 771.8.IX otros locales). tipo: 'vivienda' | 'oficina' | 'local'.
    Devuelve {'grado', 'dpms_ref_kva'}."""
    _num(superficie_m2, "superficie_m2", 0.0, True)
    grados = _g("_GRADOS_771")
    if tipo not in grados:
        raise ValueError(f"tipo debe ser uno de {sorted(grados)} (recibido: {tipo!r})")
    for limite, grado, kva in grados[tipo]:
        if superficie_m2 <= limite:
            return {"grado": grado, "dpms_ref_kva": kva}


def grade_electrification_770(superficie_cubierta_m2, superficie_semicubierta_m2=0.0):
    """Grado según 770 (Tabla 770.7.I): superficie = cubierta + 50 % de semicubierta; ≤60, ≤130, ≤200, >200 m²."""
    _num(superficie_cubierta_m2, "superficie_cubierta_m2")
    _num(superficie_semicubierta_m2, "superficie_semicubierta_m2")
    s = superficie_cubierta_m2 + 0.5 * superficie_semicubierta_m2
    _num(s, "superficie equivalente", 0.0, True)
    for limite, grado in _g("_GRADOS_770"):
        if s <= limite:
            return {"grado": grado, "superficie_equivalente_m2": s}


def coef_simultaneity_771(grado):
    """Tabla 771.9.II: Mínimo 1; Medio 0,9; Elevado 0,8; Superior 0,7."""
    coef = _g("COEF_GRADO_771")
    if grado not in coef:
        raise ValueError(f"grado debe ser uno de {sorted(coef)}")
    return coef[grado]


def coef_simultaneity_770(n_circuitos):
    """Tabla 770.8.II por cantidad mínima de circuitos: 2→1; 3→0,8; 5→0,7; 6→0,6 (1 circuito: 1,0)."""
    _num(n_circuitos, "n_circuitos", 1)
    for n_min, c in _g("COEF_CIRCUITS_770"):
        if n_circuitos >= n_min:
            return c
    return 1.0


def coef_simultaneidad_conjunto(n_unidades, grado):
    """Tabla 771.9.III para conjuntos de viviendas/locales: columna Mín/Medio o Elev/Sup."""
    _num(n_unidades, "n_unidades", 2)
    if grado not in _g("COEF_GRADO_771"):
        raise ValueError(f"grado debe ser uno de {sorted(_g('COEF_GRADO_771'))}")
    alto = grado in ("elevado", "superior")
    for n_min, bajo, hi in _g("_CONJUNTOS_771_III"):
        if n_unidades >= n_min:
            return hi if alto else bajo


def msd_lighting_general(n_bocas, norma="771", tipo="vivienda"):
    """771: 66 % de n·150 VA (vivienda) o 100 % (oficina/local); 770: 2/3 de n·60 VA."""
    _num(n_bocas, "n_bocas")
    if norma == "770":
        fr = T.value("770.8.I_fraccion_iluminacion")
        return n_bocas * _g("VA_BOCA_770") * fr["numerador"] / fr["denominador"]
    if norma != "771":
        raise ValueError("norma debe ser '771' o '770'")
    fr = T.value("771.9.1_fraccion_iluminacion")
    return n_bocas * _g("VA_BOCA_VIVIENDA") * (fr["vivienda"] if tipo == "vivienda" else fr["otros"])


def msd_circuits(n_tug=0, n_tue=0, n_ilum_con_tomas=0):
    """Σ VA de circuitos: TUG y alumbrado con tomas derivadas 2200 VA c/u; TUE 3300 VA c/u."""
    for v, n in ((n_tug, "n_tug"), (n_tue, "n_tue"), (n_ilum_con_tomas, "n_ilum_con_tomas")):
        _num(v, n)
    return (n_tug + n_ilum_con_tomas) * _g("VA_TUG") + n_tue * _g("VA_TUE")


def dpms_total(p_generales_va, coef, p_especificas_va=0.0):
    """DPMS = Σ(uso general)·coef + Σ(cargas específicas)."""
    _num(p_generales_va, "p_generales_va")
    _num(p_especificas_va, "p_especificas_va")
    _num(coef, "coef", 0.0, True)
    return p_generales_va * coef + p_especificas_va


def current_msd(dpms_va, fases):
    """I_B = DPMS/220 (mono) o DPMS/(√3·380) (tri)."""
    _num(dpms_va, "dpms_va")
    if fases == 1:
        return dpms_va / _g("U_MONO_V")
    if fases == 3:
        return dpms_va / (math.sqrt(3) * _g("U_TRI_V"))
    raise ValueError("fases debe ser 1 o 3")


def requiere_trifasico(dpms_va, i_a=None):
    """Trifásico recomendado si DPMS > 7 kVA o I > 32 A."""
    umbral = T.value("demanda_trifasico_recomendado")
    return dpms_va > umbral["dpms_va"] or (i_a is not None and i_a > umbral["i_a"])


def imbalance_phases(currents_to):
    """(Imax − Imin)/Imax en %; cumple si ≤ 30 % (770.8.3.4)."""
    if len(currents_to) < 2:
        raise ValueError("se requieren al menos 2 corrientes")
    for i in currents_to:
        _num(i, "corriente")
    mx, mn = max(currents_to), min(currents_to)
    pct = 0.0 if mx == 0 else 100.0 * (mx - mn) / mx
    return {"desequilibrio_pct": pct, "cumple": pct <= _g("DESEQUILIBRIO_MAX_PCT")}


def corriente_alimentador_motores(in_motores_a, fs_resto=1.0):
    """I ≥ 1,25·In(mayor) + Σ In(resto)·fs."""
    if not in_motores_a:
        raise ValueError("in_motores_a vacío")
    for i in in_motores_a:
        _num(i, "In motor", 0.0, True)
    _num(fs_resto, "fs_resto", 0.0, True)
    lista = sorted(in_motores_a, reverse=True)
    return float(T.value("motor_alimentador_factor_mayor")) * lista[0] + sum(lista[1:]) * fs_resto


def factor_parallel(cables_por_fase, multipolar=False, radiacion_solar=False):
    """fs = 1 con 2 o 4 cables/fase (unipolares), 0,8 en otros casos y en multipolares; ×0,85 con radiación solar."""
    _num(cables_por_fase, "cables_por_fase", 1)
    c = T.value("conductores_paralelo_factores")
    if cables_por_fase == 1:
        fs = c["un_cable"]
    else:
        fs = c["con_reduccion_unipolar"] if (cables_por_fase in c["unipolares_sin_reduccion"] and not multipolar) else c["otros"]
    return fs * (c["radiacion_solar"] if radiacion_solar else 1.0)


def factor_demanda_sistema(sistema: str) -> float:
    """Factor de demanda de un tipo de carga (`lighting`, `receptacles`, `power`, `hvac_power`; cualquier otro usa `otros`), de las constantes `factores_demanda_sistema` (valores típicos, a revisar)."""
    c = T.constante("factores_demanda_sistema")
    return float(c.get(sistema, c["otros"]))
