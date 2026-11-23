"""CAL-017 · aea_reactive — Compensación de energía reactiva: potencia del banco de capacitores y su corriente.

ESTADO: BORRADOR — pendiente de validación por el usuario.

OBJETIVO
    1. Factor de potencia de un conjunto de cargas (P y Q de cada una) y reactiva que falta para llegar al factor de potencia objetivo.
    2. Banco de capacitores en escalones comerciales: tamaño del escalón, cantidad y potencia instalada.
    3. Corriente del banco y la que deben soportar su protección y su cable.

FÓRMULAS
    Q_i = P_i · tan φ_i          fp = P / √(P² + Q²)
    Q_c = P · (tan φ_1 − tan φ_2)   (φ_1 actual, φ_2 objetivo; si fp ≥ objetivo no hace falta)
    Escalón: el mayor comercial con Q_c / escalón ≥ N_min (para regular con N_min escalones al menos); sin ninguno, el menor.  n = ⌈Q_c / escalón⌉
    I_c = Q_banco / (√3 · U)       corriente de diseño del cable y la protección: k · I_c  (k = 1,3 de sobrecorriente × 1,1 de tolerancia de capacidad = 1,43)

HIPÓTESIS
    - Compensación central en barras, carga trifásica equilibrada, tensión nominal constante, sin armónicos (con cargas no lineales importantes el banco lleva reactancias de desintonía).
    - Los escalones comerciales, el factor 1,43 y el factor de potencia objetivo son datos de `aea_tables.json` (constantes `compensacion_reactiva`).

UNIDADES
    P [kW], Q [kvar], U [V], I [A], fp adimensional.

LIMITACIONES
    - No verifica resonancia con la inductancia de la red ni la sobretensión por la compensación en vacío.
    - No dimensiona el contactor ni el regulador del banco.

NORMA DE REFERENCIA (por designación)
    - IEC 60831 / IEC 60364-5-55 (condensadores: corriente permanente de hasta 1,3 · I_n por armónicos y 1,1 de tolerancia).  [VERIFICAR]
"""
import math
from typing import Iterable, Optional

from epc_aea90364 import aea_tables as T
from epc_aea90364._validate import num as _num
from epc_aea90364.errors import Aea90364Error

__version__ = "0.1.0"

_RAIZ3 = math.sqrt(3.0)


def _consts() -> dict:
    return T.constante("compensacion_reactiva")


def fp_objetivo_defecto() -> float:
    return float(_consts()["fp_objetivo_defecto"])


def balance(cargas: Iterable[tuple]) -> dict:
    """P [kW], Q [kvar], S [kVA] y fp del conjunto; `cargas`: pares (P en kW, fp de la carga)."""
    p = q = 0.0
    for p_kw, fp in cargas:
        _num(p_kw, "p_kw", 0.0)
        _num(fp, "fp", 0.0, True)
        if fp > 1.0:
            raise Aea90364Error("err_fp_range")
        p += p_kw
        q += p_kw * math.tan(math.acos(fp))
    s = math.hypot(p, q)
    return {"p_kw": p, "q_kvar": q, "s_kva": s, "fp": (p / s) if s else 1.0}


def reactiva_a_compensar(p_kw: float, fp_actual: float, fp_objetivo: Optional[float] = None) -> float:
    """Q_c [kvar] para pasar de `fp_actual` al objetivo (0 si ya lo cumple)."""
    fp2 = fp_objetivo_defecto() if fp_objetivo is None else fp_objetivo
    _num(p_kw, "p_kw", 0.0)
    for v, n in ((fp_actual, "fp_actual"), (fp2, "fp_objetivo")):
        _num(v, n, 0.0, True)
        if v > 1.0:
            raise Aea90364Error("err_fraction_range", n=n)
    if fp_actual >= fp2:
        return 0.0
    return p_kw * (math.tan(math.acos(fp_actual)) - math.tan(math.acos(fp2)))


def banco(q_kvar: float, u_v: float) -> dict:
    """El banco para compensar `q_kvar`: {escalon_kvar, escalones, instalado_kvar, corriente_a, corriente_diseno_a}; vacío si no hace falta."""
    _num(q_kvar, "q_kvar", 0.0)
    _num(u_v, "u_v", 0.0, True)
    if q_kvar <= 0:
        return {"escalon_kvar": 0.0, "escalones": 0, "instalado_kvar": 0.0, "corriente_a": 0.0, "corriente_diseno_a": 0.0}
    c = _consts()
    pasos = sorted(float(x) for x in c["pasos_kvar"])
    paso = max([s for s in pasos if s <= q_kvar / float(c["pasos_minimos"])], default=pasos[0])
    n = math.ceil(q_kvar / paso - 1e-9)
    instalado = n * paso
    i_c = instalado * 1000.0 / (_RAIZ3 * u_v)
    return {"escalon_kvar": paso, "escalones": n, "instalado_kvar": instalado, "corriente_a": round(i_c, 2), "corriente_diseno_a": round(float(c["factor_corriente_condensador"]) * i_c, 2)}
