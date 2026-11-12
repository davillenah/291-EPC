"""CAL-018 · aea_backup — Respaldo de energía: grupo electrógeno, UPS y transferencia automática.

ESTADO: BORRADOR — pendiente de validación por el usuario.

OBJETIVO
    1. Potencia del grupo electrógeno para las cargas esenciales, con el arranque del motor más exigente.
    2. Potencia de la UPS y energía de su batería para una autonomía dada.
    3. Corriente del interruptor de transferencia (red / grupo).

FÓRMULAS
    Marcha:     S_marcha = Σ S_i                                  grupo ≥ S_marcha / c_max            (c_max: carga continua máxima del grupo)
    Arranque:   S_arr = S_marcha − S_m + k_arr · S_m             grupo ≥ S_arr / m_arr               (m_arr: múltiplo de potencia que el grupo da en el transitorio)
                S_m del motor cuyo arranque da el mayor S_arr; k_arr según el arrancador (directo 6, estrella-triángulo 2, suave 3, variador 1,2)
    Grupo:      el menor valor comercial ≥ el mayor de los dos
    UPS:        S_ups = S_cargas · (1 + reserva)   →  el menor valor comercial ≥ S_ups
                E_bat = P · t / (η_inv · DoD)       P [kW] de las cargas, t [h] la autonomía, η_inv el rendimiento del inversor, DoD la profundidad de descarga
    Transferencia: I_n ≥ m_t · I_cargas   (serie comercial de interruptores)

HIPÓTESIS
    - Los múltiplos de arranque, la carga máxima del grupo, el múltiplo transitorio, la reserva y los rendimientos son valores típicos de `aea_tables.json` (constantes `respaldo_grupo_ups`), a confirmar con
      el fabricante del grupo y de la UPS.
    - La UPS también se alimenta del grupo: las cargas de UPS suman a las del grupo.

UNIDADES
    S [kVA], P [kW], t [h], E [kWh], I [A].

LIMITACIONES
    - La caída de tensión en el arranque se cubre con el múltiplo transitorio, no se calcula con la reactancia subtransitoria del alternador.
    - No dimensiona el combustible, el tablero de transferencia ni el sincronismo.

NORMA DE REFERENCIA (por designación)
    - ISO 8528 (grupos electrógenos), IEC 62040 (UPS), AEA 90364-5-56 (servicios de seguridad).  [VERIFICAR]
"""
import math
from typing import Iterable, List, Optional, Tuple

from epc_aea90364 import aea_tables as T
from epc_aea90364._validate import num as _num

__version__ = "0.1.0"

_RAIZ3 = math.sqrt(3.0)


def _c() -> dict:
    return T.constante("respaldo_grupo_ups")


def _primero(serie: List[float], valor: float) -> float:
    return next((x for x in serie if x >= valor - 1e-9), float(serie[-1]))


def multiplo_arranque(topologia: str) -> float:
    """k_arr del arrancador (1 para lo que no es motor)."""
    return float(_c()["arranque_multiplo_in"].get(str(topologia or "").lower(), 1.0))


def grupo(cargas: Iterable[Tuple[str, float, str]], u_v: float) -> dict:
    """El grupo de las cargas `(tag, S en kVA, topología)`: {s_marcha_kva, s_arranque_kva, motor, grupo_kva, corriente_a}; todo en 0 si no hay cargas."""
    _num(u_v, "u_v", 0.0, True)
    items = [(t, float(s), top) for t, s, top in cargas]
    for _, s, _ in items:
        _num(s, "s_kva", 0.0)
    marcha = sum(s for _, s, _ in items)
    if marcha <= 0:
        return {"s_marcha_kva": 0.0, "s_arranque_kva": 0.0, "motor": "", "grupo_kva": 0.0, "corriente_a": 0.0}
    c = _c()
    pico, motor = marcha, ""
    for tag, s, top in items:
        k = multiplo_arranque(top)
        if k > 1.0 and marcha - s + k * s > pico + 1e-9:
            pico, motor = marcha - s + k * s, tag
    necesaria = max(marcha / float(c["grupo_carga_maxima"]), pico / float(c["grupo_multiplo_arranque"]))
    g = _primero(sorted(float(x) for x in c["grupo_potencias_kva"]), necesaria)
    return {"s_marcha_kva": round(marcha, 2), "s_arranque_kva": round(pico, 2), "motor": motor, "grupo_kva": g, "corriente_a": round(g * 1000.0 / (_RAIZ3 * u_v), 1)}


def ups(s_kva: float, p_kw: float, autonomia_min: float) -> dict:
    """La UPS de unas cargas de `s_kva` / `p_kw` con `autonomia_min`: {ups_kva, bateria_kwh}; todo en 0 si no hay cargas."""
    for v, n in ((s_kva, "s_kva"), (p_kw, "p_kw"), (autonomia_min, "autonomia_min")):
        _num(v, n, 0.0)
    if s_kva <= 0:
        return {"ups_kva": 0.0, "bateria_kwh": 0.0}
    c = _c()
    nominal = _primero(sorted(float(x) for x in c["ups_potencias_kva"]), s_kva * (1.0 + float(c["ups_reserva"])))
    energia = p_kw * (autonomia_min / 60.0) / (float(c["ups_rendimiento_inversor"]) * float(c["ups_profundidad_descarga"]))
    return {"ups_kva": nominal, "bateria_kwh": round(energia, 2)}


def transferencia(i_a: float, serie_in_a: Optional[List[float]] = None) -> float:
    """El interruptor de transferencia para unas cargas de `i_a` (el menor de la serie con el margen de la tabla)."""
    _num(i_a, "i_a", 0.0)
    if i_a <= 0:
        return 0.0
    if serie_in_a is None:
        from epc_aea90364 import aea_pipeline as P
        serie_in_a = list(P.SERIE_IN_A)
    return float(_primero(sorted(serie_in_a), i_a * float(_c()["transferencia_margen"])))
