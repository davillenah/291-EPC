"""Parámetros normativos de la protección de conductores y de las curvas de disparo: los valores viven en `aea_tables.json` (sección `constantes`, que revisa la página de normas con
aprobación por valor) y este módulo los entrega. Son funciones y no constantes del módulo: un valor corregido en la página de normas rige sin reiniciar nada.

Hoy hay una sola jurisdicción (AEA 90364 / IEC 60364-4-43 / IEC 60898-1 / IEC 60947-2); cuando exista una segunda, este módulo pasa a ser una política por norma.
"""
from typing import Dict

from epc_calc_common import aea_tables as T


def k_max_i2_iz() -> float:
    """IEC 60364-4-43: la corriente convencional de funcionamiento del dispositivo no supera este múltiplo de Iz (1,45)."""
    return float(T.constante("proteccion_k_max_i2_iz"))


def k2_convencional() -> Dict[str, float]:
    """Corriente convencional de funcionamiento I2 = k2 · In (disparo seguro), por tipo de dispositivo."""
    return dict(T.constante("proteccion_k2_convencional"))


def k1_no_disparo() -> Dict[str, float]:
    """Corriente convencional de no funcionamiento k1 · In (IEC 60898-1 para MCB, IEC 60947-2 para MCCB)."""
    return dict(T.constante("proteccion_k1_no_disparo"))
