"""CAL-019 · aea_motor — Fuerza motriz: corriente de arranque de un motor y caída de tensión en el arranque.

ESTADO: BORRADOR — pendiente de validación por el usuario.

OBJETIVO
    1. Corriente de arranque de un motor según su arrancador (directo, estrella-triángulo, arrancador suave, variador).
    2. Caída de tensión del cable del motor durante el arranque (cos φ de arranque 0,3 de la tabla de GDC) y su verificación contra el límite.

FÓRMULAS
    I_arr = k_arr · I_n                    k_arr según el arrancador (mismos múltiplos que el estudio de grupo electrógeno)
    ΔU_arr = GDC_arr · I_arr · L / S       GDC_arr [V·mm²/(A·m)] de `aea_voltage_drop` (hasta 70 mm²)
    cumple si ΔU_arr% ≤ límite             límite en arranque: constante `fuerza_motriz`

    Protección propia: ajuste del relé térmico = I_n · factor de servicio, dentro del rango comercial que lo deja en la parte alta
    (el más chico que lo contiene); disparo magnético mínimo = k · I_arr (k de las constantes) para que no dispare con el arranque.

HIPÓTESIS
    - El límite de caída en el arranque es un valor típico de `aea_tables.json` (constantes `fuerza_motriz`), a confirmar.
    - La caída se calcula solo en el cable del motor; no suma la de los alimentadores aguas arriba.

UNIDADES
    I [A], L [m], S [mm²], U [V], ΔU [%].

LIMITACIONES
    - Arriba de 70 mm² la tabla de GDC no tiene valor de arranque: la caída se informa como no calculada (None).
    - No verifica la reactancia subtransitoria del transformador ni el par del motor.

NORMA DE REFERENCIA (por designación)
    AEA 90364-7-771 (caída de tensión), AEA 90364-5-55 (motores).  [VERIFICAR]
"""
from typing import Optional

from epc_aea90364 import aea_backup as B
from epc_aea90364 import aea_tables as T
from epc_aea90364 import aea_voltage_drop as VD
from epc_aea90364._validate import num as _num

__version__ = "0.1.0"


def limite_arranque_pct() -> float:
    """Caída de tensión máxima en el arranque (%)."""
    return float(T.constante("fuerza_motriz")["caida_arranque_max_pct"])


def corriente_arranque(i_n_a: float, topologia: str) -> float:
    """I_arr [A] de un motor de corriente nominal `i_n_a` con el arrancador `topologia`."""
    _num(i_n_a, "i_n_a", 0.0)
    return round(i_n_a * B.multiplo_arranque(topologia), 1)


def caida_arranque(i_n_a: float, topologia: str, largo_m: float, seccion_mm2: float, material: str = "cu", fases: int = 3, un_v: Optional[float] = None) -> dict:
    """Arranque del motor: {k_arr, i_arranque_a, caida_pct (None si la tabla no llega), limite_pct, cumple (None si no se calculó)}."""
    _num(largo_m, "largo_m", 0.0)
    _num(seccion_mm2, "seccion_mm2", 0.0, True)
    i_arr = corriente_arranque(i_n_a, topologia)
    lim = limite_arranque_pct()
    out = {"k_arr": B.multiplo_arranque(topologia), "i_arranque_a": i_arr, "caida_pct": None, "limite_pct": lim, "cumple": None}
    if seccion_mm2 > VD.GDC_ARRANQUE_MAX_MM2:
        return out
    pct = VD.caida_gdc(i_arr, largo_m, seccion_mm2, material, fases, un_v, arranque=True)["delta_u_pct"]
    out.update(caida_pct=round(pct, 2), cumple=pct <= lim + 1e-9)
    return out


def proteccion_motor(i_n_a: float, topologia: str) -> dict:
    """Protección propia del motor: {ajuste_termico_a, rango_a (None si ningún rango comercial lo contiene), clase_disparo, magnetico_min_a}."""
    _num(i_n_a, "i_n_a", 0.0, True)
    c = T.constante("fuerza_motriz")
    ajuste = round(i_n_a * float(c["factor_servicio"]), 2)
    rango = next((tuple(r) for r in c["rangos_rele_termico_a"] if r[0] <= ajuste <= r[1]), None)
    i_arr = corriente_arranque(i_n_a, topologia)
    return {"ajuste_termico_a": ajuste, "rango_a": rango, "clase_disparo": int(c["clase_disparo"]), "magnetico_min_a": round(float(c["magnetico_x_arranque"]) * i_arr, 1)}
