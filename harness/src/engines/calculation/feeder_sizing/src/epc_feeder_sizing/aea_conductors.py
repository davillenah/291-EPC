"""CAL-017 · aea_conductors — Secciones mínimas, sobrecarga, armónicos y paralelo de conductores.

ESTADO: BORRADOR — pendiente de validación por el usuario.

OBJETIVO
    Criterios de AEA 90364-7-771/770 para conductores que NO están en `cable_thermal.py`:
    secciones mínimas (Tabla 771.13.I), tabla k completa (Tabla 771.19.II), coordinación
    de la protección contra sobrecarga, factores por armónicos (Tabla 771.16.XIII),
    corriente de neutro y volumen de material combustible.
    La verificación térmica ante cortocircuito se hace con `cable_thermal`
    (S ≥ I√t/k; k²S²≥I²t); aquí solo se aporta la tabla k ampliada.

FÓRMULAS
    Sobrecarga:     I_B ≤ I_n ≤ I_Z ;  I_2 ≤ 1,45·I_Z
    Poder de corte: PdC ≥ I''k
    THD = 100·√(Σ_{n≥2} h_n²)/h_ef ; h_ef = √(Σ_{n≥1} h_n²)
    D   = 100·√(Σ_{n≥2} h_n²)/h_1 ; D² = THD²/(1−THD²) ; THD² = D²/(1+D²)  (THD, D en p.u.)
    I_N = 3·I_f·(h_3/100)  (neutro con terceras armónicas) ; I' = I/f_arm
    Tabla 771.16.XIII: THD ≤15 %→1,00 (línea); 15–33 %→0,86 (línea); 33–45 %→0,86 (neutro); >45 %→1,00 (neutro)
    I_f = P/(√3·U·cosφ)
    Volumen combustible [dm³/m] = π·De²/4000 − ΣS/1000  (De [mm], S [mm²])

UNIDADES
    I [A], S [mm²], De [mm], h_n [% o p.u. según se indique].

LIMITACIONES
    - El factor armónico depende de la tabla de la norma por rangos de THD de 3.º armónica.
    - Sin cálculo de ampacidad (I_Z) desde la instalación: I_Z viene de las tablas del cable.

NORMA DE REFERENCIA
    AEA 90364-7-771 §13, §16, §19, Anexo H; AEA 90364-7-770 §11.  [VERIFICAR]
"""
import math
from epc_calc_common._validate import num as _num
from epc_calc_common import aea_tables as T
from epc_calc_common import policy
from epc_feeder_sizing.errors import FeederSizingError

__version__ = "0.1.0"


# Los valores normativos viven en `aea_tables.json` (una sola fuente, ADR-0012); los nombres de módulo se arman desde allí al usarlos
# (`__getattr__` de módulo, PEP 562) y se renuevan con `aea_tables.limpiar_cache_tablas()`. Forma de cada uno:
#   SECCIONES_MIN_MM2  Tabla 771.13.I [mm²] (cobre): {tipo: S}            PEN_MIN_MM2  {"cu": 10.0, "al": 16.0}
#   K_TABLA_771        Tabla 771.19.II k [A·s^½/mm²]: {(aislación, material): k}
#   IZ_771_16_I        Tabla 771.16.I [A], Cu, PVC, 40 °C, método B1 (cañería): {S: (2x, 3x)}
#   R20_CU_OHM_KM      resistencia del cobre a 20 °C [Ω/km] (IEC 60228, clase 2): {S: R}
#   ALFA_CU            coeficiente de temperatura del cobre [1/°C]         X_CABLE_OHM_KM  reactancia típica de cable en cañería [Ω/km]  [VERIFICAR]
#   FACTORS_HARMONICS  Tabla 771.16.XIII: ((THD máx [%], factor, aplicado a), ...); el último límite es math.inf (null en el JSON)
_BUILD = {
    "SECCIONES_MIN_MM2": lambda d: dict(d["constantes"]["771.13.I_secciones_minimas_mm2"]),
    "PEN_MIN_MM2": lambda d: dict(d["constantes"]["771.13_pen_minima_mm2"]),
    "K_TABLA_771": lambda d: {tuple(k.split("|")): v for k, v in d["constantes"]["771.19.II_k_adiabatico"].items()},
    "IZ_771_16_I": lambda d: {T.numeric_key(s): tuple(v) for s, v in next(b for b in d["tablas_capacidad"]["771.16.I"]["bloques"] if b["aislacion"] == "pvc")["filas"]["cu"].items()},
    "R20_CU_OHM_KM": lambda d: {T.numeric_key(s): v for s, v in d["constantes"]["impedancias_estandar"]["r20_ohm_km"].items()},
    "ALFA_CU": lambda d: float(d["constantes"]["conductor_alfa_cu"]["valor"]),
    "X_CABLE_OHM_KM": lambda d: float(d["constantes"]["impedancias_estandar"]["reactancia_ohm_km"]),
    "FACTORS_HARMONICS": lambda d: tuple((math.inf if lim is None else lim, f, donde) for lim, f, donde in d["constantes"]["771.16.XIII_factores_armonicos"]["valor"]),
}


def _g(nombre):
    return T.derived(f"{__name__}.{nombre}", _BUILD[nombre])


def __getattr__(nombre):
    if nombre in _BUILD:
        return _g(nombre)
    raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")


def section_min_circuit(tipo):
    """Tabla 771.13.I [mm²]."""
    tabla = _g("SECCIONES_MIN_MM2")
    if tipo not in tabla:
        raise FeederSizingError("err_type_invalid", opciones=sorted(tabla))
    return tabla[tipo]


def iz_admisible(seccion_mm2, cargados=3):
    """Tabla 771.16.I [A]: Cu/PVC, 40 °C, método B1. cargados = 2 (monofásico) o 3 (trifásico)."""
    tabla = _g("IZ_771_16_I")
    if seccion_mm2 not in tabla:
        raise FeederSizingError("err_section_outside_table", seccion_mm2=seccion_mm2, opciones=sorted(tabla))
    if cargados not in (2, 3):
        raise FeederSizingError("err_loaded_conductors")
    return tabla[seccion_mm2][0 if cargados == 2 else 1]


def pe_section(seccion_mm2, k_fase=1.0, k_pe=1.0):
    """Sección del conductor de protección [mm²] (AEA 771.18.3): igual a la de fase hasta 16 mm², 16 mm² hasta 35 mm² y la mitad por encima, llevada hacia arriba a la
    serie comercial (47,5 -> 50); mínimo 2,5 mm². Con un material distinto al de la fase se multiplica por k_fase/k_pe. Es la única implementación (`aea_earthing.seccion_pe_mm2` la llama)."""
    _num(seccion_mm2, "seccion_mm2", 0.0, True)
    _num(k_fase, "k_fase", 0.0, True)
    _num(k_pe, "k_pe", 0.0, True)
    v, mitad = _pe_initial(seccion_mm2)
    if k_fase != k_pe:
        v = v * k_fase / k_pe
    if mitad:
        v = _to_commercial_series(v)
    return max(_g("SECCIONES_MIN_MM2")["pe"], v)


def _pe_initial(s):
    """(PE section before the material correction, whether it is half the phase section) per the 771.18.3 steps."""
    pasos = T.value("771.18.3_pe_pasos")
    mitad = s > pasos["fija_hasta_mm2"]
    if s <= pasos["igual_a_fase_hasta_mm2"]:
        return s, mitad
    return (s / pasos["divisor_superior"] if mitad else pasos["fija_mm2"]), mitad


def _to_commercial_series(v):
    """Smallest commercial-series section >= v (v itself if none)."""
    return next((x for x in sorted(_g("IZ_771_16_I")) if x >= v - 1e-9), v)


def neutral_section(seccion_mm2):
    """Sección del neutro [mm²]: igual a la de fase hasta 16 mm²; por encima, la mitad llevada a la serie comercial."""
    _num(seccion_mm2, "seccion_mm2", 0.0, True)
    s = seccion_mm2
    serie = sorted(_g("IZ_771_16_I"))
    return s if s <= T.value("neutro_seccion_igual_hasta_mm2") else next((v for v in serie if v >= s / 2 - 1e-9), serie[-1])


def resistencia_cu_ohm_km(seccion_mm2, temp_c=70.0):
    """R(θ) = R20·(1 + 0,00393·(θ − 20)) [Ω/km]; 70 °C = temperatura máxima del PVC en servicio."""
    r20 = _g("R20_CU_OHM_KM")
    if seccion_mm2 not in r20:
        raise FeederSizingError("err_no_resistance", seccion_mm2=seccion_mm2)
    return r20[seccion_mm2] * (1.0 + _g("ALFA_CU") * (temp_c - 20.0))


def k_adiabatico_771(aislacion, material, seccion_mm2=None):
    """Tabla 771.19.II: k [A·s^½/mm²]. Es la única búsqueda de k (`cable_thermal.k_material` la llama). `aislacion` es una clave de la tabla ('pvc_sobre_300',
    'epr_xlpe', ...) o un nombre corriente: 'xlpe' equivale a 'epr_xlpe' y 'pvc' se resuelve con la sección (decisión D12): hasta 300 mm² o sin dar la sección ->
    'pvc_hasta_300' (compatible hacia atrás), por encima de 300 mm² -> 'pvc_sobre_300' (Cu 103, Al 68)."""
    ais = _insulation_key(str(aislacion).lower(), seccion_mm2)
    clave = (ais, material.lower())
    tabla = _g("K_TABLA_771")
    if clave not in tabla:
        raise FeederSizingError("err_no_k_value", clave=(aislacion, material.lower()))
    return tabla[clave]


def _insulation_key(ais, seccion_mm2):
    """Table 771.19.II key for a lower-case insulation name (aliases and the D12 PVC rule)."""
    alias = T.value("771.19.II_k_aislaciones")
    if ais == "pvc":
        pvc = alias["pvc"]
        return pvc["sobre"] if seccion_mm2 is not None and seccion_mm2 > pvc["limite_mm2"] else pvc["hasta"]
    return alias[ais] if isinstance(alias.get(ais), str) else ais


def seccion_pen_minima_mm2(material):
    """PEN ≥ 10 mm² Cu / 16 mm² Al."""
    return _g("PEN_MIN_MM2")[material.lower()]


def verify_overload(i_b_a, i_n_a, i_z_a, i_2_a=None):
    """I_B ≤ I_n ≤ I_Z y, si se da I_2, I_2 ≤ 1,45·I_Z. Devuelve dict de comprobaciones."""
    for v, n in ((i_b_a, "i_b_a"), (i_n_a, "i_n_a"), (i_z_a, "i_z_a")):
        _num(v, n, 0.0, True)
    r = {"ib_le_in": i_b_a <= i_n_a, "in_le_iz": i_n_a <= i_z_a}
    if i_2_a is not None:
        _num(i_2_a, "i_2_a", 0.0, True)
        r["i2_le_1_45_iz"] = i_2_a <= policy.k_max_i2_iz() * i_z_a
    r["cumple"] = all(r.values())
    return r


def verifica_poder_corte(pdc_a, i_k_a):
    """PdC ≥ I''k."""
    _num(pdc_a, "pdc_a", 0.0, True)
    _num(i_k_a, "i_k_a")
    return pdc_a >= i_k_a


def thd_pct(armonicos):
    """THD [%] respecto del valor eficaz. armonicos = {n: h_n} (n=1 fundamental, cualquier unidad común)."""
    if 1 not in armonicos:
        raise FeederSizingError("err_no_fundamental")
    sup = sum(h ** 2 for n, h in armonicos.items() if n >= 2)
    h_ef = math.sqrt(sum(h ** 2 for h in armonicos.values()))
    _num(h_ef, "h_ef", 0.0, True)
    return 100.0 * math.sqrt(sup) / h_ef


def distorsion_d_pct(armonicos):
    """D [%] respecto de la fundamental."""
    if 1 not in armonicos:
        raise FeederSizingError("err_no_fundamental")
    _num(armonicos[1], "h1", 0.0, True)
    return 100.0 * math.sqrt(sum(h ** 2 for n, h in armonicos.items() if n >= 2)) / armonicos[1]


def thd_desde_d(d_pu):
    """THD² = D²/(1+D²) (p.u.)."""
    _num(d_pu, "d_pu")
    return d_pu / math.sqrt(1.0 + d_pu ** 2)


def d_desde_thd(thd_pu):
    """D² = THD²/(1−THD²) (p.u.)."""
    _num(thd_pu, "thd_pu")
    if thd_pu >= 1:
        raise FeederSizingError("err_thd_range")
    return thd_pu / math.sqrt(1.0 - thd_pu ** 2)


def factor_harmonics(thd3_pct):
    """Tabla 771.16.XIII: devuelve {'factor','aplicado_a'} según el THD (3.º armónica) [%]."""
    _num(thd3_pct, "thd3_pct")
    for lim, f, donde in _g("FACTORS_HARMONICS"):
        if thd3_pct <= lim:
            return {"factor": f, "aplicado_a": donde}


def current_neutral_harmonics(i_fase_a, h3_pct):
    """I_N = 3·I_f·h3/100."""
    _num(i_fase_a, "i_fase_a")
    _num(h3_pct, "h3_pct")
    return 3.0 * i_fase_a * h3_pct / 100.0


def current_corrected(i_a, factor):
    """I' = I/factor (corriente a considerar para elegir el cable)."""
    _num(i_a, "i_a")
    _num(factor, "factor", 0.0, True)
    return i_a / factor


def current_phase_three_phase(p_w, u_v, cos_fi):
    """I_f = P/(√3·U·cosφ)."""
    _num(p_w, "p_w")
    _num(u_v, "u_v", 0.0, True)
    _num(cos_fi, "cos_fi", 0.0, True)
    return p_w / (math.sqrt(3) * u_v * cos_fi)


def volumen_combustible_dm3_m(diametro_ext_mm, secciones_conductores_mm2):
    """V = π·De²/4000 − ΣS/1000 [dm³/m]."""
    _num(diametro_ext_mm, "diametro_ext_mm", 0.0, True)
    for s in secciones_conductores_mm2:
        _num(s, "S", 0.0, True)
    return math.pi * diametro_ext_mm ** 2 / 4000.0 - sum(secciones_conductores_mm2) / 1000.0
