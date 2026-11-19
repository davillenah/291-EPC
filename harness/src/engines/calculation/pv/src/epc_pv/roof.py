"""Roof layout: where the modules go on each roof plane, and the arrays that follow from it.

A roof is a list of planes. Each plane is a rectangle in its own coordinates (metres): `x` along the eave, `y` up the slope, origin at the lower-left corner, with its tilt and azimuth (from north,
clockwise; in the southern hemisphere the sunny side is 0). The modules lie on the plane (same tilt and azimuth), so no row spacing is needed. Obstacles (chimneys, tanks, skylights) are rectangles
on the plane; a margin (`setback_m`) is kept free along every edge. Modules are placed on a grid in portrait or landscape, the one that holds more; cells touching an obstacle are dropped.

  plan(roof)       placement of every plane + the arrays for `epc_pv.run` (one array per plane: orientations are never mixed on one MPPT)
  `target_modules`  when given, only that many modules are placed (row by row from the eave); the result says if the roof is too small

Every datum is given (module size, gap, planes): nothing is defaulted here. Flat roofs with tilted frames and sloped shading between obstacles and modules are not covered (see the README).
"""
from typing import Any, Dict, List, Optional, Tuple

from epc_pv.layout import ORIENTATIONS, _need, _number
from epc_pv.messages import bi, item
from epc_pv.model import PvError

SCHEMA_VERSION = "1.0"
PLANE_KEYS = ("id", "width_m", "slope_m", "tilt_deg", "azimuth_deg", "setback_m")
OBSTACLE_KEYS = ("x", "y", "width_m", "depth_m")


def check(roof: Any) -> None:
    """Refuse an incomplete or wrong roof input, in English and Spanish."""
    _need(roof, ("planes", "module_dimensions_mm", "module_gap_m", "array"), "roof")
    if not isinstance(roof["planes"], list) or not roof["planes"]:
        raise PvError("err_type", name="roof.planes", kind=bi("a non-empty list", "una lista no vacía"))
    dims = roof["module_dimensions_mm"]
    if not (isinstance(dims, list) and len(dims) == 2 and all(isinstance(d, (int, float)) and not isinstance(d, bool) and d > 0 for d in dims)):
        raise PvError("err_type", name="roof.module_dimensions_mm", kind=bi("[long side, short side] in mm", "[lado largo, lado corto] en mm"))
    _number(roof, "module_gap_m", "roof", positive=False)
    _need(roof["array"], ("module", "inverter"), "roof.array")
    for k, plane in enumerate(roof["planes"]):
        where = f"roof.planes[{k}]"
        _need(plane, PLANE_KEYS, where)
        for key in ("width_m", "slope_m"):
            _number(plane, key, where)
        _number(plane, "setback_m", where, positive=False)
        for key, hi in (("tilt_deg", 90), ("azimuth_deg", 360)):
            if isinstance(plane[key], bool) or not isinstance(plane[key], (int, float)) or not 0 <= plane[key] <= hi:
                raise PvError("err_range", name=f"{where}.{key}", rule=f"0 to {hi}", value=plane[key])
        for j, ob in enumerate(plane.get("obstacles", [])):
            _need(ob, OBSTACLE_KEYS, f"{where}.obstacles[{j}]")
            for key in OBSTACLE_KEYS:
                _number(ob, key, f"{where}.obstacles[{j}]", positive=key in ("width_m", "depth_m"))


def _hits(cell: Tuple[float, float, float, float], obstacles: List[Dict[str, Any]]) -> bool:
    x, y, w, d = cell
    return any(x < o["x"] + o["width_m"] and o["x"] < x + w and y < o["y"] + o["depth_m"] and o["y"] < y + d for o in obstacles)


def _grid(plane: Dict[str, Any], along: float, across: float, gap: float) -> List[Dict[str, float]]:
    """Free cells of the plane for a module `along` the eave and `across` up the slope, row by row from the eave."""
    s = float(plane["setback_m"])
    usable_w, usable_l = float(plane["width_m"]) - 2 * s, float(plane["slope_m"]) - 2 * s
    cols, rows = int((usable_w + gap) // (along + gap)), int((usable_l + gap) // (across + gap))
    obstacles = plane.get("obstacles", [])
    cells = []
    for r in range(max(rows, 0)):
        for c in range(max(cols, 0)):
            cell = (s + c * (along + gap), s + r * (across + gap), along, across)
            if not _hits(cell, obstacles):
                cells.append({"x": round(cell[0], 3), "y": round(cell[1], 3), "row": r + 1})
    return cells


def _best(plane: Dict[str, Any], long_m: float, short_m: float, gap: float) -> Tuple[str, List[Dict[str, float]], Dict[str, float]]:
    """(orientation, cells, module size on the plane) of the orientation that holds more modules (portrait on a tie)."""
    options = {"portrait": (short_m, long_m), "landscape": (long_m, short_m)}
    best = max(ORIENTATIONS, key=lambda o: (len(_grid(plane, *options[o], gap)), o == "portrait"))
    along, across = options[best]
    return best, _grid(plane, along, across, gap), {"width_m": along, "depth_m": across}


def _plane(plane: Dict[str, Any], roof: Dict[str, Any], wanted: Optional[int]) -> Dict[str, Any]:
    long_m, short_m = (d / 1000.0 for d in roof["module_dimensions_mm"])
    orientation, cells, size = _best(plane, long_m, short_m, float(roof["module_gap_m"]))
    capacity = len(cells)
    placed = cells if wanted is None else cells[:max(wanted, 0)]
    return {"id": plane["id"], "width_m": float(plane["width_m"]), "slope_m": float(plane["slope_m"]), "tilt_deg": float(plane["tilt_deg"]), "azimuth_deg": float(plane["azimuth_deg"]),
            "setback_m": float(plane["setback_m"]), "obstacles": [dict(o) for o in plane.get("obstacles", [])], "orientation": orientation, "module": size,
            "capacity": capacity, "modules": len(placed), "cells": [dict(c) for c in placed]}


def _arrays(planes: List[Dict[str, Any]], template: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One array per plane that holds modules: the template (module, inverter, ratio or inverter count) with the plane's tilt, azimuth and module count."""
    return [dict(template, id=p["id"], name=p["id"], tilt_deg=p["tilt_deg"], azimuth_deg=p["azimuth_deg"], n_modules=p["modules"]) for p in planes if p["modules"] > 0]


def plan(roof: Dict[str, Any]) -> Dict[str, Any]:
    """The roof layout: placement per plane, the arrays for `epc_pv.run` and warnings (a target the roof cannot hold)."""
    check(roof)
    target = roof.get("target_modules")
    if target is not None and (isinstance(target, bool) or not isinstance(target, int) or target < 1):
        raise PvError("err_range", name="roof.target_modules", rule=">=1 (integer)", value=target)
    planes, left = [], target
    for plane in roof["planes"]:
        done = _plane(plane, roof, left)
        left = None if left is None else left - done["modules"]
        planes.append(done)
    total, capacity = sum(p["modules"] for p in planes), sum(p["capacity"] for p in planes)
    short = (target - total) if target is not None else 0
    return {"schema_version": SCHEMA_VERSION, "planes": planes, "arrays": _arrays(planes, roof["array"]),
            "counts": {"planes": len(planes), "modules": total, "capacity": capacity, "short": short}, "fits": short == 0,
            "warnings": [item("roof_short", n=short, capacity=capacity)] if short else []}
