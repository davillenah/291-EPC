"""Parses the two table-like inputs of a luminaire: the CU table and the photometry.

Kept apart from document.py so cu.py can read the generic table without
importing the document parser.
"""
import math
from functools import lru_cache
from typing import Any, Sequence

from epc_lighting.config import data
from epc_lighting.model import CuTable, LightingError, Photometry
from epc_lighting.model import LightingError


def _fail(path: str, code: str, **params) -> None:
    raise LightingError(code, path=path, **params)


def _bounds(value: float, path: str, minimum: float | None, maximum: float | None, positive: bool) -> None:
    if positive and value <= 0:
        _fail(path, "err_not_positive", value=value)
    if minimum is not None and value < minimum:
        _fail(path, "err_below_minimum", minimum=minimum, value=value)
    if maximum is not None and value > maximum:
        _fail(path, "err_above_maximum", maximum=maximum, value=value)


def number(value: Any, path: str, minimum: float | None = None, maximum: float | None = None, positive: bool = False) -> float:
    """A finite number within limits, or an error that says what to correct."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(path, "err_not_number", value=value)
    if not math.isfinite(value):
        _fail(path, "err_not_finite_number")
    _bounds(value, path, minimum, maximum, positive)
    return float(value)


def _increasing(values: Sequence[float], path: str) -> None:
    if any(b <= a for a, b in zip(values, values[1:])):
        _fail(path, "err_not_increasing")


def _list(raw: Any, path: str, minimum_len: int = 1) -> list:
    if not isinstance(raw, list) or len(raw) < minimum_len:
        _fail(path, "err_list_too_short", minimum_len=minimum_len)
    return raw


def parse_cu_table(raw: Any, path: str) -> CuTable:
    if not isinstance(raw, dict):
        _fail(path, "err_cu_table_shape")
    axis = raw.get("axis", "k")
    if axis not in ("k", "rcr"):
        _fail(f'{path}.axis', "err_axis_invalid", axis=axis)
    axis_values = tuple(number(v, f"{path}.axis_values[{i}]", minimum=0) for i, v in enumerate(_list(raw.get("axis_values"), f"{path}.axis_values")))
    _increasing(axis_values, f"{path}.axis_values")
    columns = _columns(raw.get("reflectances"), f"{path}.reflectances")
    scale = _scale(raw.get("unit", "fraction"), f"{path}.unit")
    rows = _list(raw.get("values"), f"{path}.values")
    if len(rows) != len(axis_values):
        _fail(f'{path}.values', "err_rows_per_axis", expected=len(axis_values), got=len(rows))
    values = tuple(_row(r, len(columns), scale, f"{path}.values[{i}]") for i, r in enumerate(rows))
    return CuTable(axis, axis_values, columns, values)


def _scale(unit: Any, path: str) -> float:
    if unit not in ("fraction", "percent"):
        _fail(path, "err_unit_invalid", unit=unit)
    return 0.01 if unit == "percent" else 1.0


def _columns(raw: Any, path: str):
    columns = []
    for i, col in enumerate(_list(raw, path)):
        triple = _list(col, f"{path}[{i}]", 3)
        if len(triple) != 3:
            _fail(f'{path}[{i}]', "err_reflectances_shape")
        columns.append(tuple(number(v, f"{path}[{i}][{j}]", minimum=0, maximum=1) for j, v in enumerate(triple)))
    return tuple(columns)


def _row(raw: Any, width: int, scale: float, path: str):
    row = _list(raw, path)
    if len(row) != width:
        _fail(path, "err_values_per_reflectance", width=width, got=len(row))
    return tuple(number(v, f"{path}[{j}]", minimum=0) * scale for j, v in enumerate(row))


def parse_photometry(raw: Any, path: str) -> Photometry:
    if not isinstance(raw, dict):
        _fail(path, "err_photometry_shape")
    gamma = tuple(number(v, f"{path}.gamma_deg[{i}]", minimum=0, maximum=180) for i, v in enumerate(_list(raw.get("gamma_deg"), f"{path}.gamma_deg")))
    _increasing(gamma, f"{path}.gamma_deg")
    intensity = raw.get("intensity_cd_per_klm")
    if "c_deg" not in raw:
        return Photometry(gamma, (0.0,), (_intensity_row(intensity, len(gamma), f"{path}.intensity_cd_per_klm"),))
    c_deg = tuple(number(v, f"{path}.c_deg[{i}]", minimum=0, maximum=359.999) for i, v in enumerate(_list(raw["c_deg"], f"{path}.c_deg")))
    _increasing(c_deg, f"{path}.c_deg")
    rows = _list(intensity, f"{path}.intensity_cd_per_klm")
    if len(rows) != len(c_deg):
        _fail(f'{path}.intensity_cd_per_klm', "err_rows_per_c_plane", expected=len(c_deg), got=len(rows))
    return Photometry(gamma, c_deg, tuple(_intensity_row(r, len(gamma), f"{path}.intensity_cd_per_klm[{i}]") for i, r in enumerate(rows)))


def _intensity_row(raw: Any, width: int, path: str):
    row = _list(raw, path)
    if len(row) != width:
        _fail(path, "err_values_per_gamma", width=width, got=len(row))
    return tuple(number(v, f"{path}[{j}]", minimum=0) for j, v in enumerate(row))


@lru_cache(maxsize=None)
def generic_table() -> CuTable:
    """The illustrative CU table shipped in data/cu_generic.json."""
    return parse_cu_table(data("cu_generic")["cu_table"], "data/cu_generic.json cu_table")

