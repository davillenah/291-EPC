"""aea_protection — Protección contra contactos indirectos y coordinación de dispositivos (AEA 90364-4-41, 4-43, 7-771.18).

ESTADO: BORRADOR — pendiente de validación por el usuario.

OBJETIVO
    Verificación de la desconexión automática por esquema (TN, TT, IT) y corriente
    convencional de funcionamiento (I2) de los dispositivos de protección.

FÓRMULAS
    I2 = k2 · In            (k2: 1,45 MCB IEC 60898; 1,30 MCCB IEC 60947-2; 1,60 fusible gG)
    In,max = min(Iz, 1,45·Iz/k2)       (coordinación con I2 ≤ 1,45·Iz)
    TN:  Zs ≤ c_min · U0 / Ia   (D13, c_min = 0,95)
    TT:  Ra ≤ Ra,max = min(0,5·24/Ia ; 40 Ω) (D11; con UL explícito: Ra,max = UL/Ia) ;  If = U0/(Ra + Rb)
    IT (segunda falla, masas interconectadas):  2 · Ia · Zs ≤ U   (sin neutro)
                                                2 · Ia · Zs' ≤ U0 (con neutro distribuido)

UNIDADES
    I [A], Z, R [Ω], U [V].

LIMITACIONES
    - k2 son valores usuales de normas de producto; el fabricante prevalece.
    - No calcula Zs desde la instalación (ver `short_circuit.py`, `aea_earthing.py`).

NORMA DE REFERENCIA
    AEA 90364-4-41 (§41.3), 90364-4-43, 90364-7-771.18 y IT 90909-1.  [VERIFICAR]
"""
from typing import Any, Dict, Optional

from epc_grounding import aea_earthing as E
from epc_calc_common import aea_rounding as RND
from epc_calc_common import policy; from epc_load_balance import system_voltage as SV
from epc_selectivity.errors import SelectivityError

__version__ = "0.1.0"


def i2_convencional(in_a: float, tipo: str = "mcb") -> float:
    """Corriente convencional de funcionamiento I2 = k2·In [A]."""
    k2 = policy.k2_convencional()
    if tipo not in k2:
        raise SelectivityError("err_type_unknown", tipo=tipo, tipos=sorted(k2))
    if in_a <= 0:
        raise SelectivityError("err_rated_current")
    return k2[tipo] * in_a


def in_max_por_iz(iz_a: float, tipo: str = "mcb") -> float:
    """In máxima que cumple In ≤ Iz e I2 ≤ 1,45·Iz [A]."""
    return min(iz_a, policy.k_max_i2_iz() * iz_a / policy.k2_convencional()[tipo])


def verifica_tn(zs_ohm: float, ia_a: float, u0_v: Optional[float] = None, un_v: Optional[float] = None) -> Dict[str, Any]:
    """TN: Zs ≤ Zs máxima = c_min·U0/Ia (decisión D13: el mismo límite que `aea_earthing.zs_maxima`, una sola función). Devuelve dict con el producto Zs·Ia, el
    límite en volts (c_min·U0), la Zs máxima y cumple. U0 es el del sistema del proyecto (D16, `system_voltage.system_u0(un_v)`; sin dato, el sistema por defecto del motor)."""
    zs_max = E.zs_maxima(_u0(u0_v, un_v), ia_a)
    return {"zs_ia_v": zs_ohm * ia_a, "limite_v": zs_max * ia_a, "zs_max_ohm": zs_max, "cumple": zs_ohm <= zs_max}


def ra_maxima_tt(ia_a: float, ul_v: Optional[float] = None) -> float:
    """TT: resistencia de puesta a tierra máxima [Ω]. Por defecto (decisión D11) la adoptada, min(0,5·24/Ia ; 40 Ω), de `aea_earthing.ra_maxima`;
    solo si se pide una tensión límite explícita `ul_v` (p. ej. la columna de 50 V) devuelve UL/Ia."""
    return _ra_limit(ia_a, ul_v)


def _ra_limit(ia_a: float, ul_v: Optional[float]) -> float:
    return E.ra_maxima(ia_a)["adoptada"] if ul_v is None else ul_v / ia_a


def verifica_tt(ra_ohm: float, ia_a: float, ul_v: Optional[float] = None) -> Dict[str, Any]:
    """TT: Ra ≤ Ra máxima. Por defecto (D11) la adoptada, min(0,5·24/Ia ; 40 Ω); con `ul_v` explícito, Ra·Ia ≤ UL. `limite_v` es el límite expresado en volts (Ra máx · Ia)."""
    return _tt_result(ra_ohm, ia_a, ra_maxima_tt(ia_a, ul_v), ul_v)


def _tt_result(ra_ohm: float, ia_a: float, ra_max: float, ul_v: Optional[float]) -> Dict[str, Any]:
    return {"ra_ia_v": ra_ohm * ia_a, "limite_v": ra_max * ia_a if ul_v is None else ul_v, "ra_max_ohm": ra_max,
            "cumple": RND.round_up_2(ra_ohm) <= ra_max if ul_v is None else ra_ohm * ia_a <= ul_v}


def corriente_falla_tt(u0_v: float, ra_ohm: float, rb_ohm: float) -> float:
    """TT: corriente de primera falla If = U0/(Ra + Rb) [A]."""
    return u0_v / (ra_ohm + rb_ohm)


def verifica_it_segunda_falla(zs_ohm: float, ia_a: float, u_v: Optional[float] = None, u0_v: Optional[float] = None, neutro_distribuido: bool = False) -> Dict[str, Any]:
    """IT, segunda falla: 2·Ia·Zs ≤ U (sin neutro) o ≤ U0 (con neutro distribuido). U y U0 son los del sistema del proyecto (D16)."""
    prod = 2.0 * ia_a * zs_ohm
    u_v = SV.default_un_v() if u_v is None else u_v
    limite = _u0(u0_v, u_v) if neutro_distribuido else u_v
    return {"dos_ia_zs_v": prod, "limite_v": limite, "cumple": prod <= limite}


def _u0(u0_v: Optional[float], un_v: Optional[float]) -> float:
    """U0 stated by the caller, or the one of the system `un_v` (D16); no module keeps its own value."""
    if u0_v is not None:
        return u0_v
    return SV.system_u0(SV.default_un_v() if un_v is None else un_v)
