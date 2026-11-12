"""CAL-020 · aea_lightning — Protección contra descargas atmosféricas: frecuencia de impactos, riesgo y nivel de protección de una estructura.

ESTADO: BORRADOR — pendiente de validación por el usuario. Las reglas de la norma NO fueron revisadas: los valores son típicos
(constantes `descargas_atmosfericas`) y deben pasar por la revisión del dueño (E5-04) antes de alimentar un documento.

OBJETIVO
    1. Superficie de captación y frecuencia anual de impactos directos sobre una estructura aislada.
    2. Frecuencia tolerable de impactos y eficiencia que debe tener la protección.
    3. Nivel de protección (I a IV) y sus parámetros de diseño: radio de la esfera rodante, malla del captor, distancia entre bajadas.

FÓRMULAS (método simplificado de evaluación de riesgo)
    A_d = L·W + 2·(3H)·(L+W) + π·(3H)²          superficie de captación [m²]  (equivale a L·W + 6H(L+W) + 9πH²)
    N_d = N_g · A_d · C_d · 10⁻⁶                impactos directos por año    (N_g: descargas a tierra por km² y año; C_d: entorno)
    N_c = 5,5·10⁻³ / C                          frecuencia tolerable          (C = C2·C3·C4·C5: estructura, contenido, ocupación, consecuencias)
    E   = 1 − N_c / N_d                         eficiencia requerida (≤ 0: no hace falta protección)

HIPÓTESIS
    - Estructura aislada y de planta rectangular; entorno C_d entre 0,25 (rodeada de objetos más altos) y 2 (colina o aislada).
    - Los factores C2..C5, los umbrales de eficiencia y los parámetros por nivel son valores típicos de `aea_tables.json`: a revisar.

UNIDADES
    L, W, H [m]; A_d [m²]; N_g [1/(km²·año)]; N_d, N_c [1/año]; E [–]; radio y malla [m].

LIMITACIONES
    - No evalúa el riesgo por pérdida de vidas ni de servicios (componentes R1..R4), solo el criterio simplificado de frecuencias.
    - No dimensiona el sistema de puesta a tierra ni la separación de seguridad: ver el estudio de puesta a tierra.

NORMA DE REFERENCIA (por designación)
    IEC 62305-2 (riesgo), IEC 62305-3 (captores y bajadas), IRAM 2184.  [VERIFICAR]
"""
import math
from typing import Dict

from epc_aea90364 import aea_tables as T
from epc_aea90364._validate import num as _num

__version__ = "0.1.0"


def _c() -> dict:
    return T.constante("descargas_atmosfericas")


def superficie_captacion_m2(largo_m: float, ancho_m: float, altura_m: float) -> float:
    """A_d de una estructura aislada de `largo_m` × `ancho_m` y `altura_m`."""
    for v, n in ((largo_m, "largo_m"), (ancho_m, "ancho_m"), (altura_m, "altura_m")):
        _num(v, n, 0.0, True)
    r = T.value("descargas_radio_captacion_factor_altura") * altura_m
    return largo_m * ancho_m + 2.0 * r * (largo_m + ancho_m) + math.pi * r * r


def impactos_directos_anuales(ng: float, ad_m2: float, entorno: str = "aislada") -> float:
    """N_d con la densidad `ng` [1/(km²·año)] y el entorno (clave de `entorno_cd`)."""
    _num(ng, "ng", 0.0)
    _num(ad_m2, "ad_m2", 0.0)
    cd = _c()["entorno_cd"]
    if entorno not in cd:
        raise ValueError(f"entorno {entorno!r} inexistente: {sorted(cd)}")
    return ng * ad_m2 * float(cd[entorno]) * 1e-6


def frecuencia_tolerable(estructura: str, contenido: str, ocupacion: str, consecuencias: str) -> float:
    """N_c = 5,5·10⁻³ / (C2·C3·C4·C5), con cada factor elegido por clave de la tabla."""
    c = _c()
    prod = 1.0
    for tabla, clave in (("factor_c2_estructura", estructura), ("factor_c3_contenido", contenido), ("factor_c4_ocupacion", ocupacion), ("factor_c5_consecuencias", consecuencias)):
        if clave not in c[tabla]:
            raise ValueError(f"{tabla}: {clave!r} inexistente: {sorted(c[tabla])}")
        prod *= float(c[tabla][clave])
    return float(c["frecuencia_base"]) / prod


def nivel_proteccion(eficiencia: float) -> str:
    """Nivel de protección que cubre la eficiencia requerida: 'none' si no hace falta, 'I+' si pide medidas adicionales, 'I' a 'IV'."""
    _num(eficiencia, "eficiencia", -1e9)
    for limite, nivel in _c()["niveles_eficiencia"]:
        if eficiencia > limite:
            return str(nivel)
    return "none"


def parametros_nivel(nivel: str) -> Dict[str, float]:
    """Radio de la esfera rodante, malla del captor y distancia entre bajadas [m] del nivel 'I'..'IV' ('I+' usa los del I)."""
    p = _c()["parametros_nivel"]
    clave = "I" if nivel == "I+" else nivel
    if clave not in p:
        raise ValueError(f"nivel {nivel!r} inexistente: {sorted(p)}")
    return dict(p[clave])


def evaluar(largo_m, ancho_m, altura_m, ng, entorno, estructura, contenido, ocupacion, consecuencias) -> dict:
    """La estructura completa: {ad_m2, nd, nc, eficiencia, nivel, parametros (None si no hace falta protección)}."""
    ad = superficie_captacion_m2(largo_m, ancho_m, altura_m)
    nd = impactos_directos_anuales(ng, ad, entorno)
    nc = frecuencia_tolerable(estructura, contenido, ocupacion, consecuencias)
    e = 1.0 - nc / nd if nd > 0 else 0.0
    nivel = nivel_proteccion(e) if e > 0 else "none"
    return {"ad_m2": round(ad, 1), "nd": nd, "nc": nc, "eficiencia": round(max(e, 0.0), 4), "nivel": nivel, "parametros": None if nivel == "none" else parametros_nivel(nivel)}
