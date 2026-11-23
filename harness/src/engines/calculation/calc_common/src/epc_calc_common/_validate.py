"""Validadores numéricos compartidos por los módulos de cálculo (antes copiados en cada uno).

El cuerpo y los mensajes de error son los mismos que tenían las copias; cada módulo los importa con su nombre local de siempre (`_num`, `_pos`, `_nonneg`, `_frac`).
"""
import math
from epc_calc_common.errors import CalcCommonError


def num(v, nombre, minimo=0.0, estricto=False):
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
        raise CalcCommonError("err_not_finite_number", nombre=nombre, v=v)
    if (estricto and v <= minimo) or (not estricto and v < minimo):
        raise CalcCommonError("err_out_of_range", nombre=nombre, relacion='>' if estricto else '≥', minimo=minimo, v=v)


def pos(valor, nombre):
    if not isinstance(valor, (int, float)) or isinstance(valor, bool) or not math.isfinite(valor):
        raise CalcCommonError("err_not_finite_number_value", nombre=nombre, valor=valor)
    if valor <= 0:
        raise CalcCommonError("err_not_positive", nombre=nombre, valor=valor)


def nonneg(valor, nombre):
    if not isinstance(valor, (int, float)) or isinstance(valor, bool) or not math.isfinite(valor):
        raise CalcCommonError("err_not_finite_number_value", nombre=nombre, valor=valor)
    if valor < 0:
        raise CalcCommonError("err_negative", nombre=nombre, valor=valor)


def frac(valor, nombre):
    pos(valor, nombre)
    if valor > 1:
        raise CalcCommonError("err_not_fraction", nombre=nombre, valor=valor)
