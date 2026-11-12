"""CAL-016 · aea_earthing — Puesta a tierra, protección diferencial (TT) y electrodos.

ESTADO: BORRADOR — pendiente de validación por el usuario.

OBJETIVO
    Resistencia de puesta a tierra admisible para esquema TT (Tabla 771.3.I), tiempos máximos
    de desconexión (Tabla 771.18.III) y resistencia de electrodos (jabalina, conductor horizontal,
    placa circular, 771-C.10).

FÓRMULAS
    Ra ≤ UL/IΔn  (UL = 50 V col. 1; 24 V col. 2); adoptado (D11): min(0,5·24/IΔn, 40 Ω)
    Jabalina:     R = ρ/(2πL)·(ln(8L/d) − 1)
                  simplificada: 0,75ρ/L (25≤L/d≤100); ρ/L (100<L/d≤600); 1,2ρ/L (600<L/d≤3000)
    Horizontal:   R = ρ/(2πL)·(ln(4L/d) + ln(L/h) − 2 + 2h/L − h²/L² + h⁴/(2L⁴))
                  simplificada: 2ρ/L
    Placa:        R = ρ/(2D)·(1/2 + D/(4πh) + 7D³/(384h³) + 99D⁵/(81920h⁵))
    Conductor PE (Tabla 771-C.II): S≤16 → S; 16<S≤35 → 16; S>35 → S/2 (a la serie comercial superior); mínimo 2,5 mm²; otro material ×k1/k2

UNIDADES
    ρ [Ω·m], L, d, h, D [m], R [Ω], IΔn [A].

LIMITACIONES
    - Las series de la placa y del conductor horizontal se truncan en los términos citados.
    - Ra máximo permanente 40 Ω; electrodos a ≥ 10 radios equivalentes entre sí.

NORMA DE REFERENCIA
    AEA 90364-7-771 §3, §18, Anexo C.10 y C.II.  [VERIFICAR]
"""
import math
from epc_calc_common._validate import num as _num
from epc_feeder_sizing import aea_conductors as CO
from epc_calc_common import aea_rounding as RND
from epc_calc_common import aea_tables as T

__version__ = "0.1.0"

# The norm values live in `aea_tables.json` (single source, ADR-0012); the module names are built from there when used (module `__getattr__`, PEP 562)
# and are renewed with `aea_tables.limpiar_cache_tablas()`. Shape of each one:
#   UL_V, UL_COL1_V       limit touch voltage [V], column 2 (24 V) and column 1 (50 V) of Table 771.3.I
#   RA_MAX_OHM            permanent maximum Ra [ohm]
#   TIEMPOS_DESCONEXION_S Table 771.18.III (the number is to be verified against the official text): {scheme: ((Un max [V], t ac [s], t dc [s] or None), ...)};
#                         ranges 50-120 V, >120-230 V, >230-400 V
#   T_SECCIONAL_S         maximum disconnection time of sectional circuits [s]: {"TT": ..., "TN": ...} (TN: 2 s by default, decision D25)
_BUILD = {
    "UL_V": lambda d: d["constantes"]["771.18_ul_v"]["general"],
    "UL_COL1_V": lambda d: d["constantes"]["771.18_ul_v"]["col1"],
    "RA_MAX_OHM": lambda d: d["constantes"]["771.18_ra_max_ohm"],
    "TIEMPOS_DESCONEXION_S": lambda d: {esq: tuple(tuple(f) for f in filas) for esq, filas in d["constantes"]["771.18.III_tiempos_desconexion_s"].items()},
    "T_SECCIONAL_S": lambda d: dict(d["constantes"]["771.18_t_seccional_s"]),
}


def _g(nombre):
    return T.derived(f"{__name__}.{nombre}", _BUILD[nombre])


def __getattr__(nombre):
    if nombre in _BUILD:
        return _g(nombre)
    raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")


def ra_maxima(i_dn_a):
    """Tabla 771.3.I (decisión D11): {'col1_50v','col2_24v','adoptada'} [Ω]; adoptada = min(0,5·24/IΔn ; 40 Ω) redondeada hacia abajo a dos decimales (D11, `aea_rounding`). Es la única función que calcula la Ra máxima TT:
    `aea_protection` y `board_memo` la usan."""
    _num(i_dn_a, "i_dn_a", 0.0, True)
    c2 = _g("UL_V") / i_dn_a
    adoptada = min(T.value("771.18_ra_factor_adopcion") * c2, _g("RA_MAX_OHM"))
    return {"col1_50v": _g("UL_COL1_V") / i_dn_a, "col2_24v": c2, "adoptada": RND.round_down_2(adoptada)}


def verifica_ra(ra_ohm, i_dn_a):
    """True si Ra ≤ valor adoptado (Ra redondeada hacia arriba a dos decimales, D11)."""
    _num(ra_ohm, "ra_ohm")
    return RND.round_up_2(ra_ohm) <= ra_maxima(i_dn_a)["adoptada"]


def tiempo_desconexion_max_s(esquema, un_v, corriente="ca"):
    """Tabla 771.18.III (el número oficial de la tabla está por verificar). esquema 'TN'|'TT'; un_v entre 50 y 400; corriente 'ca'|'cc'."""
    tabla = _g("TIEMPOS_DESCONEXION_S")
    if esquema not in tabla:
        raise ValueError("esquema 'TN' o 'TT'")
    _num(un_v, "un_v", 50.0)
    for lim, t_ca, t_cc in tabla[esquema]:
        if un_v <= lim:
            if corriente == "ca":
                return t_ca
            if corriente == "cc":
                if t_cc is None:
                    raise ValueError("sin valor cc en ese rango")
                return t_cc
            raise ValueError("corriente 'ca' o 'cc'")
    raise ValueError("un_v fuera de la tabla (≤ 400 V)")


def tiempo_seccional_max_s(esquema, selectividad=False):
    """Circuitos seccionales: TT ≤ 1 s, TN ≤ 2 s (decisión D25). Con `selectividad=True` y esquema TN se admite hasta 5 s (solo cuando la selectividad lo justifica);
    en TT el indicador no tiene efecto. Los valores están en `aea_tables.json`."""
    return _sectional_time(esquema, selectividad)


def _sectional_time(esquema, selectividad):
    if esquema == "TN" and selectividad:
        return T.value("771.18_t_seccional_selectividad_tn_s")
    return _g("T_SECCIONAL_S")[esquema]


def resistance_rod(rho, largo_m, diametro_m, simplificada=False):
    """R de una jabalina vertical [Ω]. Simplificada: 0,75/1,0/1,2 ·ρ/L según L/d."""
    for v, n in ((rho, "rho"), (largo_m, "largo_m"), (diametro_m, "diametro_m")):
        _num(v, n, 0.0, True)
    if simplificada:
        r = largo_m / diametro_m
        if r < 25 or r > 3000:
            raise ValueError("L/d fuera de 25–3000")
        k = 0.75 if r <= 100 else (1.0 if r <= 600 else 1.2)
        return k * rho / largo_m
    return rho / (2 * math.pi * largo_m) * (math.log(8 * largo_m / diametro_m) - 1)


def resistance_conductor_horizontal(rho, largo_m, diametro_m, prof_m, simplificada=False):
    """R de un conductor desnudo enterrado horizontalmente [Ω]."""
    for v, n in ((rho, "rho"), (largo_m, "largo_m"), (diametro_m, "diametro_m"), (prof_m, "prof_m")):
        _num(v, n, 0.0, True)
    if simplificada:
        return 2 * rho / largo_m
    L, h = largo_m, prof_m
    return rho / (2 * math.pi * L) * (math.log(4 * L / diametro_m) + math.log(L / h) - 2
                                      + 2 * h / L - (h / L) ** 2 + h ** 4 / (2 * L ** 4))


def resistencia_placa_circular(rho, diametro_m, prof_m):
    """R de una placa circular de diámetro D a profundidad h [Ω]."""
    for v, n in ((rho, "rho"), (diametro_m, "diametro_m"), (prof_m, "prof_m")):
        _num(v, n, 0.0, True)
    D, h = diametro_m, prof_m
    return rho / (2 * D) * (0.5 + D / (4 * math.pi * h) + 7 * D ** 3 / (384 * h ** 3)
                            + 99 * D ** 5 / (81920 * h ** 5))


def resistance_parallel(resistencias_ohm):
    """Electrodos suficientemente separados: 1/R = Σ 1/Ri."""
    if not resistencias_ohm:
        raise ValueError("lista vacía")
    for r in resistencias_ohm:
        _num(r, "R", 0.0, True)
    return 1.0 / sum(1.0 / r for r in resistencias_ohm)


def seccion_equipotencial_principal_mm2(pe_max_mm2):
    """Conductor de equipotencialidad principal (cobre): la mitad del PE más grande, no menos del mínimo ni más del máximo de las constantes `equipotencialidad_principal`."""
    _num(pe_max_mm2, "pe_max_mm2", 0.0, True)
    c = T.constante("equipotencialidad_principal")
    return min(max(pe_max_mm2 * float(c["factor_pe"]), float(c["minimo_mm2"])), float(c["maximo_mm2"]))


def seccion_pe_mm2(s_fase_mm2, k_fase=1.0, k_pe=1.0):
    """Sección del PE [mm²] (Tabla 771-C.II): una sola implementación, `aea_conductors.pe_section` (mínimo 2,5 mm²; la mitad de la fase se lleva hacia
    arriba a la serie comercial, 47,5 -> 50); con material distinto se multiplica por k_fase/k_pe."""
    return CO.pe_section(s_fase_mm2, k_fase, k_pe)


def _r_km(s_mm2, material):
    """Resistencia por km a temperatura de servicio [Ω/km] de la sección `s_mm2`: la de la tabla para la sección listada de igual o menor valor, escalada en 1/S (así una sección intermedia no queda por debajo); el aluminio con el factor de la constante."""
    c = T.constante("impedancias_estandar")
    tabla = sorted((float(k), v) for k, v in c["r20_ohm_km"].items())
    _num(s_mm2, "s_mm2", 0.0, True)
    s = float(s_mm2)
    k, v = ([t for t in tabla if t[0] <= s] or tabla[:1])[-1]
    return v * k / s * c["factor_temperatura_servicio"] * (c["factor_aluminio"] if material == "al" else 1.0)


def zs_lazo(u0_v, icc_barras_ka, s_fase_mm2, s_pe_mm2, largo_m, material="cu"):
    """Impedancia del lazo de falla fase-PE al final de un circuito TN [Ω] con valores estándar por sección:
    fuente = c_max·U0/Icc de barras; cable = (R fase + R PE)·L a temperatura de servicio; reactancia total del lazo = X·L. Devuelve {zs_ohm, zfuente_ohm, r_ohm, x_ohm}."""
    c = T.constante("impedancias_estandar")
    for v, n in ((u0_v, "u0_v"), (icc_barras_ka, "icc_barras_ka"), (s_fase_mm2, "s_fase_mm2"), (s_pe_mm2, "s_pe_mm2")):
        _num(v, n, 0.0, True)
    _num(largo_m, "largo_m", 0.0)
    largo = float(largo_m)
    zf = c["c_fuente_max"] * u0_v / (icc_barras_ka * 1e3)
    r = (_r_km(s_fase_mm2, material) + _r_km(s_pe_mm2, material)) * largo / 1e3
    x = c["reactancia_ohm_km"] * largo / 1e3
    return {"zs_ohm": math.hypot(zf + r, x), "zfuente_ohm": zf, "r_ohm": r, "x_ohm": x}


def zs_maxima(u0_v, ia_a):
    """Zs máxima que hace disparar con la corriente `ia_a`: c_min·U0/Ia [Ω]."""
    _num(u0_v, "u0_v", 0.0, True)
    _num(ia_a, "ia_a", 0.0, True)
    return T.constante("impedancias_estandar")["c_tension_min"] * u0_v / ia_a


def resistencia_malla(rho, area_m2, largo_conductor_m, prof_m=0.6):
    """R de una malla de tierra [Ω] (fórmula de Sverak, IEEE 80): ρ·[1/L + 1/√(20·A)·(1 + 1/(1 + h·√(20/A)))], con L el largo total de conductor enterrado, A el área que cubre y h la profundidad. [VERIFICAR]"""
    for v, n in ((rho, "rho"), (area_m2, "area_m2"), (largo_conductor_m, "largo_conductor_m"), (prof_m, "prof_m")):
        _num(v, n, 0.0, True)
    return rho * (1.0 / largo_conductor_m + 1.0 / math.sqrt(20.0 * area_m2) * (1.0 + 1.0 / (1.0 + prof_m * math.sqrt(20.0 / area_m2))))
