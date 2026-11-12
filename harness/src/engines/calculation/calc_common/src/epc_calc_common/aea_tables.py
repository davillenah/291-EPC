"""aea_tables — Carga y consulta de los datos normativos del motor (`aea_tables.json`).

ESTADO: BORRADOR — pendiente de validación por el usuario.

OBJETIVO
    Dar acceso programático a las tablas de capacidad de corriente (AEA 90364-7-771,
    tablas 771.16.I a XI) y a sus factores de corrección, extraídas de los PDF de `assets/`.

FÓRMULAS
    I_z = N · I_z0 · f_clase · f_temp · f_agrup · f_suelo      (N = ternas en paralelo)
    f_clase = 0,95 para conductores clase 5 (flexibles), 1,00 para clase 2

UNIDADES
    I [A], S [mm²], T [°C], ρ [K·m/W].

LIMITACIONES
    - Interpolación lineal entre puntos de las tablas de temperatura y resistividad; fuera
      de rango se informa ValueError (no se extrapola).
    - Tabla 771.16.VI: las columnas 2x/2x/3x/3x se conservan en el orden impreso; la
      selección por defecto es la primera 3x (`c4_3x`), a confirmar.
    - No incluye la Tabla 771.16.XII ni las tablas B52 apaisadas.

NORMA DE REFERENCIA
    AEA 90364-7-771 Ed. 2006, §16 (tablas 771.16.I a XI).  [VERIFICAR]
"""
import unicodedata

from epc_calc_common import norm_data

__version__ = "0.1.0"
# `RUTA_JSON` (module attribute, read lazily below): path of `aea_tables.json` in the normative folder (MIG-37a). A test may assign another path.
_CACHE = {}
_DERIVED = {}


def __getattr__(nombre):
    if nombre == "RUTA_JSON":
        return str(norm_data.path("aea_tables.json"))
    raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")


def limpiar_cache_tablas():
    """Descarta los datos en memoria: se vuelven a leer del archivo (después de corregir un valor normativo)."""
    _CACHE.clear()
    _DERIVED.clear()
    norm_data.clear_cache()


def cargar(ruta=None):
    """Devuelve el contenido de `aea_tables.json` (con caché por ruta)."""
    ruta = ruta or globals().get("RUTA_JSON") or __getattr__("RUTA_JSON")
    if ruta not in _CACHE:
        _CACHE[ruta] = norm_data.read_json(ruta)
    return _CACHE[ruta]


def _clave_seccion(s):
    """1.5 -> '1.5'; 25.0 -> '25'."""
    return str(int(s)) if float(s) == int(s) else str(float(s))


def secciones(tabla, aislacion, material):
    """Secciones [mm²] disponibles para (tabla, aislación, material), de menor a mayor."""
    bloque = _bloque(tabla, aislacion, _tabla(tabla).get("grupo"), None)
    return sorted(float(k) for k in bloque["filas"][material])


def _tabla(tabla):
    try:
        return cargar()["tablas_capacidad"][tabla]
    except KeyError:
        raise ValueError(f"tabla {tabla} inexistente: {sorted(cargar()['tablas_capacidad'])}")


def _bloque(tabla, aislacion, grupo=None, material=None):
    for b in _tabla(tabla)["bloques"]:
        if b["aislacion"] == aislacion and (grupo is None or b.get("grupo_metodos") == grupo):
            if material is None or material in b["filas"]:
                return b
    raise ValueError(f"sin bloque {aislacion}/{grupo} en {tabla}")


def iz_tabla(tabla, aislacion, material, seccion_mm2, columna, grupo=None):
    """Intensidad admisible base [A] de una tabla 771.16, para `columna` (clave impresa).

    Ej.: iz_tabla('771.16.III','xlpe','cu',185,'C_3x') — bandeja no perforada, 3 cargados.
    """
    b = _bloque(tabla, aislacion, grupo, material)
    claves = [c["clave"] for c in b["columnas"]]
    if columna not in claves:
        raise ValueError(f"columna {columna} inexistente; use una de {claves}")
    fila = b["filas"][material].get(_clave_seccion(seccion_mm2))
    if fila is None:
        raise ValueError(f"sección {seccion_mm2} mm² fuera de {tabla}/{aislacion}/{material}")
    v = fila[claves.index(columna)]
    if v is None:
        raise ValueError(f"sin valor para {seccion_mm2} mm² en columna {columna}")
    return float(v)


def _interp(xs, ys, x):
    if x < xs[0] or x > xs[-1]:
        raise ValueError(f"valor {x} fuera del rango de la tabla [{xs[0]}, {xs[-1]}]")
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            if ys[i] is None or ys[i + 1] is None:
                raise ValueError(f"sin dato de factor para {x}")
            if xs[i + 1] == xs[i]:
                return float(ys[i])
            return float(ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i]))
    raise ValueError(f"valor {x} fuera de tabla")


def factor_temperatura_aire(aislacion, temp_c):
    """Tabla 771.16.II.a: factor por temperatura ambiente distinta de 40 °C."""
    f = cargar()["factores_correccion"]["771.16.II.a"]
    return _interp(f["temperaturas_c"][aislacion], f["factores"][aislacion], temp_c)


def factor_temperatura_suelo(aislacion, temp_c):
    """Tabla 771.16.VII.a: factor por temperatura del suelo distinta de 25 °C."""
    f = cargar()["factores_correccion"]["771.16.VII.a"]
    xs = f["temperaturas_c"]
    ys = f["factores"][aislacion]
    pares = [(x, y) for x, y in zip(xs, ys) if y is not None]
    return _interp([p[0] for p in pares], [p[1] for p in pares], temp_c)


def factor_resistividad(metodo, rho_kmw):
    """Tabla 771.16.VII.b: método 'D1' (caños enterrados) o 'D2' (directamente enterrado)."""
    f = cargar()["factores_correccion"]["771.16.VII.b"]
    clave = {"D1": "cables_en_caños_o_conductos_enterrados_D1",
             "D2": "cables_directamente_enterrados_D2"}[metodo]
    return _interp(f["resistividad_termica_kmw"], f["factores"][clave], rho_kmw)


def factor_agrupamiento_canos(circuitos, trifasicos=True):
    """Tabla 771.16.II.b: 2 o 3 circuitos en un mismo caño (monofásicos u trifásicos). D18: otro número se rechaza."""
    if circuitos <= 1:
        return 1.0
    for fila in cargar()["factores_correccion"]["771.16.II.b"]["filas"]:
        if fila["circuitos"] == f"{circuitos} " + ("trifásicos" if trifasicos else "monofásicos"):
            return float(fila["factor"])
    raise MissingNormDataError(f"agrupamiento de {circuitos} circuitos en un mismo caño fuera de la Tabla 771.16.II.b (solo 2 o 3 circuitos): "
                               "indique en AGRUP_CIRCUITOS un número cubierto por la tabla o reagrupe los circuitos")


def factor_agrupamiento_aire(item, n_circuitos):
    """Tabla 771.16.IV: item '1'..'5'. D18: solo se aceptan los números de circuitos que la tabla trae (sin interpolar ni repetir el último factor)."""
    if n_circuitos <= 1:
        return 1.0
    for fila in cargar()["factores_correccion"]["771.16.IV"]["filas"]:
        if fila["item"] == str(item):
            ns, fs = fila["numero_de_circuitos"], fila["factores"]
            if n_circuitos not in ns:
                raise MissingNormDataError(
                    f"agrupamiento de {n_circuitos} circuitos fuera de la Tabla 771.16.IV (ítem {item}): la tabla trae solo {ns[1:]} circuitos; "
                    "no se interpola ni se repite el último factor. Indique en AGRUP_CIRCUITOS uno de esos números (reagrupe los circuitos o separe las canalizaciones)")
            return float(fs[ns.index(n_circuitos)])
    raise ValueError(f"item {item} inexistente en Tabla 771.16.IV")


def factor_agrupamiento_enterrado(tabla, n_circuitos, separacion_idx):
    """Tablas 771.16.VII.c / d1 / d2: `tabla` en {'c','d1','d2'}; `separacion_idx` 0.. según columnas. D18: sin tope en 6; un número no tabulado se rechaza."""
    f = cargar()["factores_correccion"]["771.16.VII." + tabla]
    clave = [k for k in f if k.startswith("numero_de")][0]
    filas = f[clave]
    if n_circuitos <= 1:
        return 1.0
    if str(n_circuitos) not in filas:
        raise MissingNormDataError(
            f"agrupamiento enterrado de {n_circuitos} circuitos fuera de la Tabla 771.16.VII.{tabla}: la tabla trae solo {', '.join(filas)} circuitos; "
            "no hay tope silencioso ni se repite el último factor. Indique en AGRUP_CIRCUITOS uno de esos números (reagrupe los circuitos o separe las canalizaciones)")
    return float(filas[str(n_circuitos)][separacion_idx])


def iz_corregida(iz_base_a, ternas=1, clase5=False, f_temp=1.0, f_agrup=1.0, f_suelo=1.0):
    """I_z = N · I_z0 · f_clase · f_temp · f_agrup · f_suelo   [A]."""
    return ternas * iz_base_a * (float(value("771.16_factor_clase5")) if clase5 else 1.0) * f_temp * f_agrup * f_suelo


def constante(nombre):
    """Devuelve una constante del motor (clave de `constantes`, p. ej. '771.19.II_k_adiabatico')."""
    c = cargar()["constantes"]
    if nombre not in c:
        raise ValueError(f"constante {nombre} inexistente: {sorted(c)}")
    return c[nombre]


def value(nombre):
    """Valor (`valor`) de una constante con metadatos (`titulo`, `fuente`, `valor`); es el dato en memoria, no una copia."""
    return constante(nombre)["valor"]


def numeric_key(clave):
    """Clave JSON de sección a número: '1.5' -> 1.5, '4' -> 4 (int)."""
    f = float(clave)
    return int(f) if f == int(f) else f


def derived(nombre, build):
    """Objeto que un módulo arma desde los datos (`build(datos)`, el contenido de `aea_tables.json`), con caché que se descarta junto con los datos (`limpiar_cache_tablas`)."""
    if nombre not in _DERIVED:
        _DERIVED[nombre] = build(cargar())
    return _DERIVED[nombre]


class MissingNormDataError(ValueError):
    """D18: the calculation is rejected because a datum is outside the normative tables or was not given (the message names it and says how to supply it)."""


def separacion_idx(tabla, texto):
    """Índice de la columna de separación de la Tabla 771.16.VII.<tabla> según el texto de la entrada (p. ej. 'en contacto', '0,25 m'); D18: sin texto o desconocido se rechaza."""
    opciones = cargar()["factores_correccion"]["771.16.VII." + tabla]["separacion"]
    claves = [_clave_texto(o) for o in opciones]
    if texto in (None, "") or _clave_texto(texto) not in claves:
        raise MissingNormDataError(f"falta la separación entre cables (SEPARACION_CABLES) de la Tabla 771.16.VII.{tabla}: indique una de {opciones}; no hay columna por defecto")
    return claves.index(_clave_texto(texto))


def _clave_texto(texto):
    """Texto comparable: sin tildes, en minúsculas, sin espacios y con punto decimal."""
    plano = unicodedata.normalize("NFD", str(texto)).encode("ascii", "ignore").decode()
    return plano.lower().replace(",", ".").replace(" ", "")


def columnas_de_cargados(tabla, aislacion, cargados):
    """[(clave, descripción)] de las columnas de una tabla de capacidad para ese número de conductores cargados."""
    return [(c["clave"], c["descripcion"]) for c in _bloque(tabla, aislacion)["columnas"] if c.get("cargados") == cargados]
