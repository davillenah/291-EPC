"""aea_ampacity — Capacidad de conducción de un circuito según aislación, material y método de instalación.

ESTADO: BORRADOR — pendiente de validación por el usuario.

OBJETIVO
    A partir de las columnas opcionales del Excel (AISLACION, MATERIAL, METODO, CLASE,
    N_TERNAS, AGRUP_CIRCUITOS, TEMP_AMBIENTE_C, TEMP_SUELO_C, RESIST_TERMICA_KMW, IZ_A;
    COLUMNA_D2 y SEPARACION_CABLES, obligatorias solo en el método D2 — D18)
    obtiene Iz de las tablas 771.16 y la resistencia del conductor. Sin esas columnas se
    comporta como antes: Cu, PVC, método B1, 40 °C (Tabla 771.16.I).

FÓRMULAS
    I_z = N · I_z0 · f_clase · f_temp · f_agrup · f_suelo
    R(θ) = R20 · (1 + α·(θ − 20)) ;  α_Cu = 0,00393 ; α_Al = 0,00403
    Si IZ_A está informada, se toma como I_z0 base del cable (por terna) y solo se aplican los factores.

UNIDADES
    I [A], S [mm²], R [Ω/km], T [°C], ρ [K·m/W].

LIMITACIONES
    - Aluminio solo desde 16 mm² (AEA 771.13) y con R20 de IEC 60228 clase 2 [VERIFICAR].
    - B1 solo existe para PVC en la Tabla 771.16.I; B1 con XLPE no tiene tabla: se informa.
    - F usa la disposición trébol para 3 cargados; G, horizontal separados.
    - Más de 3 circuitos en un caño (B1/B2) se reduce con la Tabla 771.16.IV ítem 1.

NORMA DE REFERENCIA
    AEA 90364-7-771 §16 (771.16.I a VII), §13; IEC 60228.  [VERIFICAR]
"""
from epc_feeder_sizing import aea_conductors as CO
from epc_calc_common import aea_tables as T

__version__ = "0.1.0"

AISLACIONES = ("pvc", "xlpe")
MATERIALES = ("cu", "al")
METODOS = ("B1", "B2", "C", "E", "F", "G", "D1", "D2")
METODOS_COLUMNA_EXPLICITA = ("D2",)   # D18: el método directamente enterrado exige COLUMNA_D2 (tabla de capacidad) y, con agrupamiento, SEPARACION_CABLES
# Los valores viven en `aea_tables.json` y los nombres se arman desde allí al usarlos (como en aea_conductors):
#   SECCION_MIN_AL_MM2  sección mínima del aluminio [mm²]      ALFA  {"cu", "al"} coeficiente de temperatura [1/°C]
#   R20_AL_OHM_KM       R20 [Ω/km], aluminio clase 2 (IEC 60228): {S: R}
#   TEMP_CONDUCTOR_C    temperatura máxima del conductor por aislación [°C] (Tabla 771.16.III)
_BUILD = {
    "SECCION_MIN_AL_MM2": lambda d: float(d["constantes"]["771.13_seccion_minima_al_mm2"]["valor"]),
    "ALFA": lambda d: {"cu": float(d["constantes"]["conductor_alfa_cu"]["valor"]), "al": float(d["constantes"]["conductor_alfa_al"]["valor"])},
    "R20_AL_OHM_KM": lambda d: {T.numeric_key(s): v for s, v in d["constantes"]["conductor_r20_al_ohm_km"]["valor"].items()},
    "TEMP_CONDUCTOR_C": lambda d: {a: float(v) for a, v in d["tablas_capacidad"]["771.16.III"]["referencia"]["temp_conductor_c"].items()},
}


def _g(nombre):
    return T.derived(f"{__name__}.{nombre}", _BUILD[nombre])


def __getattr__(nombre):
    if nombre in _BUILD:
        return _g(nombre)
    raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")



#: Descripción legible de cada método (se usa en el Excel; también se aceptan los códigos)
METODOS_DESCRIPCION = {
    "B1": "Conductores en caño o cablecanal (embutido o a la vista)",
    "B2": "Cable multipolar en caño (embutido o a la vista)",
    "C": "Bandeja no perforada o de fondo sólido",
    "E": "Bandeja perforada o escalera - cable multipolar",
    "F": "Bandeja perforada o escalera - unipolares en contacto",
    "G": "Aire libre - unipolares separados un diámetro",
    "D1": "Caño o ducto enterrado",
    "D2": "Directamente enterrado",
}
_SINONIMOS = {"cobre": "cu", "aluminio": "al"}


def _norm(v):
    """Minúsculas, sin guiones largos ni espacios repetidos."""
    return " ".join(str(v).replace("\u2013", "-").replace("\u2014", "-").lower().split())


def _metodo(v):
    """Código de método desde el código (B1, D2...) o desde su descripción."""
    if v in (None, ""):
        return "B1"
    t = _norm(v)
    for cod, desc in METODOS_DESCRIPCION.items():
        if t == cod.lower() or t == _norm(desc):
            return cod
    raise ValueError(f"METODO {v!r} inválido: use uno de {list(METODOS_DESCRIPCION.values())}")


def _txt(v, defecto):
    s = _norm(v) if v not in (None, "") else defecto
    return _SINONIMOS.get(s, s)


def _num(v, defecto):
    try:
        return float(v) if v not in (None, "") else defecto
    except (TypeError, ValueError):
        raise ValueError(f"valor numérico inválido: {v!r}")


def _opt_text(v):
    """Texto opcional de una celda: None si está vacía."""
    return None if v in (None, "") else str(v).strip()


def parametros(c):
    """Lee las columnas de instalación de una fila de CIRCUITOS y aplica los valores por defecto."""
    p = {
        "aislacion": _txt(c.get("AISLACION"), "pvc"),
        "material": _txt(c.get("MATERIAL"), "cu"),
        "metodo": _metodo(c.get("METODO")),
        "clase": int(_num(c.get("CLASE"), 2)),
        "ternas": int(_num(c.get("N_TERNAS"), 1)),
        "agrup": int(_num(c.get("AGRUP_CIRCUITOS"), 1)),
        "t_amb": _num(c.get("TEMP_AMBIENTE_C"), 40.0),
        "t_suelo": _num(c.get("TEMP_SUELO_C"), 25.0),
        "rho": _num(c.get("RESIST_TERMICA_KMW"), 1.0),
        "iz_a": _num(c.get("IZ_A"), None),
        "columna_d2": _opt_text(c.get("COLUMNA_D2")),
        "separacion": _opt_text(c.get("SEPARACION_CABLES")),
    }
    if p["aislacion"] not in AISLACIONES:
        raise ValueError(f"AISLACION {p['aislacion']!r} inválida: {AISLACIONES}")
    if p["material"] not in MATERIALES:
        raise ValueError(f"MATERIAL {p['material']!r} inválido: {MATERIALES}")
    if p["clase"] not in (2, 5) or p["ternas"] < 1 or p["agrup"] < 1:
        raise ValueError("CLASE debe ser 2 o 5; N_TERNAS y AGRUP_CIRCUITOS ≥ 1")
    return p


def seccion_valida(p, s):
    """El aluminio exige S ≥ 16 mm² y R20 tabulada."""
    if p["material"] == "al":
        return s >= _g("SECCION_MIN_AL_MM2") and s in _g("R20_AL_OHM_KM")
    return s in CO.R20_CU_OHM_KM


def temp_conductor(p, temp_c_defecto=70.0):
    """Temperatura de servicio: la dada, o 90 °C si es XLPE y no se fijó otra."""
    if p["aislacion"] == "xlpe" and temp_c_defecto == 70.0:
        return _g("TEMP_CONDUCTOR_C")["xlpe"]
    return temp_c_defecto


def resistencia_ohm_km(s, material, temp_c):
    """R(θ) del conductor [Ω/km]."""
    if material == "cu":
        return CO.R20_CU_OHM_KM[s] * (1.0 + _g("ALFA")["cu"] * (temp_c - 20.0))
    r20_al = _g("R20_AL_OHM_KM")
    if s not in r20_al:
        raise ValueError(f"sección {s} sin resistencia tabulada para Al")
    return r20_al[s] * (1.0 + _g("ALFA")["al"] * (temp_c - 20.0))


def _fuente(p, cargados):
    """(tabla, grupo, columna) de 771.16 para el método de instalación. D18: en D2 la columna la da la entrada (COLUMNA_D2), no hay una por defecto."""
    tabla, grupo, col = _fuente_de_mapa(p["metodo"], p["aislacion"], cargados)
    if p["metodo"] in METODOS_COLUMNA_EXPLICITA:
        col = _columna_explicita(p, tabla, cargados)
    return tabla, grupo, col


def _columna_explicita(p, tabla, cargados):
    """Columna de la tabla de capacidad que indicó la entrada (COLUMNA_D2) para ese número de conductores cargados; sin ella o si no corresponde se rechaza."""
    opciones = T.columnas_de_cargados(tabla, p["aislacion"], cargados)
    dada = (p.get("columna_d2") or "").lower()
    if dada not in [k for k, _ in opciones]:
        detalle = "; ".join(f"{k} = {d}" for k, d in opciones)
        raise T.MissingNormDataError(
            f"método {p['metodo']} (directamente enterrado) con {cargados} conductores cargados: falta o no corresponde COLUMNA_D2 ({p.get('columna_d2')!r}); "
            f"indique la columna de la Tabla {tabla} según la instalación: {detalle}. No hay columna por defecto")
    return dada


def _fuente_de_mapa(metodo, aislacion, cargados):
    """La regla vive en la constante `771.16_metodos_tabla_fuente` (método -> tabla, grupo y columna según el número de conductores cargados; un método nuevo es una entrada nueva)."""
    mapa = T.value("771.16_metodos_tabla_fuente")
    spec = mapa.get(metodo, mapa["por_defecto"])
    solo = spec.get("solo_aislacion")
    if solo is not None and aislacion != solo:
        raise ValueError(f"{metodo} con XLPE no tiene tabla en {spec['tabla']}: use B2 o C")
    col = spec["columna_n2"] if cargados == 2 and "columna_n2" in spec else spec["columna"].format(n=cargados)
    return spec["tabla"], spec["grupo"], col


def iz_base(p, s, cargados):
    """I_z0 por terna [A]: IZ_A si se informó, si no la tabla 771.16 correspondiente."""
    if p["iz_a"] is not None:
        return p["iz_a"]
    tabla, grupo, col = _fuente(p, cargados)
    return T.iz_tabla(tabla, p["aislacion"], p["material"], s, col, grupo)


def _agrupamiento(p, n, trifasico):
    """Factor de agrupamiento para n > 1 circuitos según la constante `771.16_metodos_agrupamiento` (método -> tabla); todo método no listado usa la de enterrados D1."""
    m = p["metodo"]
    mapa = T.value("771.16_metodos_agrupamiento")
    spec = mapa.get(m, mapa["por_defecto"])
    if "enterrado" in spec:
        idx = T.separacion_idx(spec["enterrado"], p.get("separacion")) if m in METODOS_COLUMNA_EXPLICITA else spec["separacion_idx"]   # D18: sin columna por defecto en D2
        return T.factor_agrupamiento_enterrado(spec["enterrado"], n, idx)
    if "canos_hasta" in spec and n <= spec["canos_hasta"]:
        return T.factor_agrupamiento_canos(n, trifasico)
    return T.factor_agrupamiento_aire(spec["aire_item"], n)


def factores(p, trifasico=True):
    """Dict con f_clase, f_temp, f_agrup y f_suelo."""
    m, n = p["metodo"], p["agrup"]
    enterrado = m in ("D1", "D2")
    f_temp = 1.0 if enterrado else T.factor_temperatura_aire(p["aislacion"], p["t_amb"])
    f_suelo = (T.factor_temperatura_suelo(p["aislacion"], p["t_suelo"]) * T.factor_resistividad(m, p["rho"])
               if enterrado else 1.0)
    f_agrup = 1.0 if n <= 1 or m == "G" else _agrupamiento(p, n, trifasico)
    return {"f_clase": float(T.value("771.16_factor_clase5")) if p["clase"] == 5 else 1.0, "f_temp": f_temp, "f_agrup": f_agrup, "f_suelo": f_suelo}


def iz(p, s, fases):
    """I_z total [A] del circuito con sección s. ValueError si la combinación no está tabulada."""
    cargados = 3 if fases == 3 else 2
    f = factores(p, fases == 3)
    return T.iz_corregida(iz_base(p, s, cargados), p["ternas"], p["clase"] == 5,
                          f["f_temp"], f["f_agrup"], f["f_suelo"])
