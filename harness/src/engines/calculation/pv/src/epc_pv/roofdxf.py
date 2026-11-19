"""Roof planes read from a DXF plan of the roof (ASCII DXF, standard library only).

The plan is drawn in plan view (seen from above, x east, y north) with these layers (names of the PV layer catalog, `config/dxf/layers.json`):

  PV-CUBIERTA        one closed rectangle per roof plane (a horizontal projection; axis-aligned)
  PV-CUBIERTA-OBST   one closed rectangle per obstacle (chimney, tank, skylight) inside a plane
  PV-CUBIERTA-DATOS  an optional text inside a plane: `tilt=20 az=0` (degrees; azimuth from north, clockwise; a text may carry one or both)

What is read: the planes with their width along the eave and slope length, and the obstacles in the plane's own coordinates (`epc_pv.roof`). The tilt and the azimuth are read only when the drawing carries them;
otherwise they are left out and the harness chooses them (stage 3). Units come from `$INSUNITS` of the file (metres, millimetres, centimetres, inches or feet); a file without units is refused (nothing is guessed).
A plane with a known azimuth must face a main direction (0, 90, 180 or 270): the eave is the edge on the facing side. With an unknown azimuth the eave is the south edge and the plane is only a placement
area. The horizontal projection is turned into the slope length by `1 / cos(tilt)`. Not read: sloped planes that are not rectangles, hips and valleys, curved or rotated outlines (the reading says so and stops).
"""
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from epc_pv.messages import bi, item
from epc_pv.model import PvError

SCHEMA_VERSION = "1.0"
LAYER_PLANE, LAYER_OBSTACLE, LAYER_DATA = "PV-CUBIERTA", "PV-CUBIERTA-OBST", "PV-CUBIERTA-DATOS"
UNITS_M = {1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0}
MAIN_AZIMUTHS = (0, 90, 180, 270)
TOL = 1e-6


def _pairs(text: str) -> List[Tuple[int, str]]:
    lines = text.replace("\r", "").split("\n")
    out = []
    for i in range(0, len(lines) - 1, 2):
        try:
            out.append((int(lines[i].strip()), lines[i + 1].strip()))
        except ValueError as exc:
            raise PvError("err_dxf", detail=bi("the file is not an ASCII DXF", "el archivo no es un DXF ASCII")) from exc
    return out


def _units(pairs: List[Tuple[int, str]]) -> int:
    for i, (code, value) in enumerate(pairs[:-1]):
        if code == 9 and value == "$INSUNITS":
            return int(float(pairs[i + 1][1]))
    return 0


def _entities(pairs: List[Tuple[int, str]]) -> List[Dict[str, Any]]:
    """The entities of the ENTITIES section as dicts: type, layer, closed flag, vertices (LWPOLYLINE and POLYLINE) and text with its insertion point."""
    start = next((i for i, (c, v) in enumerate(pairs) if c == 2 and v == "ENTITIES"), None)
    if start is None:
        raise PvError("err_dxf", detail=bi("no ENTITIES section", "no hay sección ENTITIES"))
    out: List[Dict[str, Any]] = []
    cur: Dict[str, Any] = _entity("")
    for code, value in pairs[start + 1:]:
        if code != 0:
            _field(cur, code, value)
        elif value == "ENDSEC":
            break
        elif value == "VERTEX" and cur["type"] == "POLYLINE":
            cur["_vertex"] = {}
            cur["vertices"].append(cur["_vertex"])
        elif value == "SEQEND":
            cur["_vertex"] = None
        else:
            cur = _entity(value)
            out.append(cur)
    return out


def _entity(kind: str) -> Dict[str, Any]:
    return {"type": kind, "layer": "", "closed": False, "vertices": [], "text": "", "x": None, "y": None, "ax": None, "ay": None, "_vertex": None}


def _field(ent: Dict[str, Any], code: int, value: str) -> None:
    vertex = ent["_vertex"]
    if code == 8:
        ent["layer"] = value
    elif code == 70 and ent["type"] in ("LWPOLYLINE", "POLYLINE"):
        ent["closed"] = bool(int(float(value)) & 1)
    elif code in (1, 3) and ent["type"] in ("TEXT", "MTEXT"):
        ent["text"] += value
    elif code in (11, 21) and ent["type"] == "TEXT":
        ent["a" + ("x" if code == 11 else "y")] = float(value)      # the alignment point replaces the insertion point of a centred text
    elif code in (10, 20):
        axis = "x" if code == 10 else "y"
        if ent["type"] == "LWPOLYLINE":
            if axis == "x":
                ent["vertices"].append({"x": float(value)})
            else:
                ent["vertices"][-1]["y"] = float(value)
        elif ent["type"] == "POLYLINE" and vertex is not None:
            vertex[axis] = float(value)
        elif ent["type"] in ("TEXT", "MTEXT"):
            ent[axis] = float(value)


def _box(ent: Dict[str, Any], scale: float, what: str) -> Dict[str, float]:
    """The axis-aligned rectangle of a closed polyline (x0, y0, x1, y1 in metres); anything else is refused."""
    pts = [(v["x"] * scale, v["y"] * scale) for v in ent["vertices"] if "x" in v and "y" in v]
    if len(pts) == 5 and abs(pts[0][0] - pts[-1][0]) < TOL and abs(pts[0][1] - pts[-1][1]) < TOL:
        pts = pts[:-1]
    xs, ys = sorted({round(p[0], 6) for p in pts}), sorted({round(p[1], 6) for p in pts})
    if not ent["closed"] or len(pts) != 4 or len(xs) != 2 or len(ys) != 2:
        raise PvError("err_dxf", detail=bi(f"{what} on layer {ent['layer']} is not a closed axis-aligned rectangle", f"{what} en la capa {ent['layer']} no es un rectángulo cerrado alineado con los ejes"))
    return {"x0": xs[0], "y0": ys[0], "x1": xs[1], "y1": ys[1]}


def _inside(box: Dict[str, float], x: float, y: float) -> bool:
    return box["x0"] - TOL <= x <= box["x1"] + TOL and box["y0"] - TOL <= y <= box["y1"] + TOL


def _text_data(texts: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for t in texts:
        for key, pattern in (("tilt_deg", r"(?:tilt|incl\w*|pend\w*)\s*[=:]?\s*(-?\d+(?:[.,]\d+)?)"), ("azimuth_deg", r"(?:az\w*)\s*[=:]?\s*(-?\d+(?:[.,]\d+)?)")):
            m = re.search(pattern, t, re.IGNORECASE)
            if m:
                out[key] = float(m.group(1).replace(",", "."))
    return out


def _frame(box: Dict[str, float], azimuth: Optional[float]):
    """(function plan point -> plane coordinates, width along the eave, plan depth up the slope): the plane turned so its eave (the edge on the facing side) is y=0 and x runs along it."""
    w, d = box["x1"] - box["x0"], box["y1"] - box["y0"]
    az = 180 if azimuth is None else int(round(azimuth)) % 360
    if az == 180:
        return (lambda X, Y: (X - box["x0"], Y - box["y0"])), w, d
    if az == 0:
        return (lambda X, Y: (box["x1"] - X, box["y1"] - Y)), w, d
    if az == 90:
        return (lambda X, Y: (Y - box["y0"], box["x1"] - X)), d, w
    return (lambda X, Y: (box["y1"] - Y, X - box["x0"])), d, w


def _plane(n: int, box: Dict[str, float], data: Dict[str, float], obstacles: List[Dict[str, float]], setback_m: float) -> Dict[str, Any]:
    tilt, azimuth = data.get("tilt_deg"), data.get("azimuth_deg")
    for name, value, hi in (("tilt_deg", tilt, 90), ("azimuth_deg", azimuth, 360)):
        if value is not None and not 0 <= value <= hi:
            raise PvError("err_range", name=f"dxf plane R{n}.{name}", rule=f"0 to {hi}", value=value)
    if azimuth is not None and int(round(azimuth)) % 360 not in MAIN_AZIMUTHS:
        raise PvError("err_dxf", detail=bi(f"plane R{n}: the azimuth {azimuth:g} is not 0, 90, 180 or 270 (the rectangle cannot say where its eave is)", f"faldón R{n}: el azimut {azimuth:g} no es 0, 90, 180 ni 270 (el rectángulo no dice dónde está su alero)"))
    to_local, width, depth = _frame(box, azimuth)
    stretch = 1.0 / math.cos(math.radians(tilt)) if tilt else 1.0
    out = {"id": f"R{n}", "width_m": round(width, 4), "slope_m": round(depth * stretch, 4), "setback_m": setback_m, "obstacles": []}
    out.update({k: v for k, v in data.items()})
    for ob in obstacles:
        (xa, ya), (xb, yb) = to_local(ob["x0"], ob["y0"]), to_local(ob["x1"], ob["y1"])
        out["obstacles"].append({"x": round(min(xa, xb), 4), "y": round(min(ya, yb) * stretch, 4), "width_m": round(abs(xb - xa), 4), "depth_m": round(abs(yb - ya) * stretch, 4)})
    return out


def read(content: str, setback_m: float) -> Dict[str, Any]:
    """{planes, warnings, source} of the DXF text `content`; `setback_m` (the margin kept free along every edge) is given by the caller."""
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    if content.startswith("AutoCAD Binary DXF"):
        raise PvError("err_dxf", detail=bi("binary DXF is not read: save the roof as ASCII DXF", "no se lee DXF binario: guardar la cubierta como DXF ASCII"))
    pairs = _pairs(content)
    code = _units(pairs)
    if code not in UNITS_M:
        raise PvError("err_dxf", detail=bi("the file does not declare its drawing units ($INSUNITS): set them to metres or millimetres", "el archivo no declara sus unidades de dibujo ($INSUNITS): fijarlas en metros o milímetros"))
    scale = UNITS_M[code]
    ents = _entities(pairs)
    on = lambda name: [e for e in ents if e["layer"].upper() == name and e["type"] in ("LWPOLYLINE", "POLYLINE")]      # noqa: E731
    boxes = [_box(e, scale, "a roof plane") for e in on(LAYER_PLANE)]
    if not boxes:
        raise PvError("err_dxf", detail=bi(f"no closed rectangle on layer {LAYER_PLANE}", f"no hay un rectángulo cerrado en la capa {LAYER_PLANE}"))
    order = sorted(range(len(boxes)), key=lambda i: (-boxes[i]["y1"], boxes[i]["x0"]))
    obstacles = [_box(e, scale, "an obstacle") for e in on(LAYER_OBSTACLE)]
    texts = [((e["ax"] if e["ax"] is not None else e["x"]) * scale, (e["ay"] if e["ay"] is not None else e["y"]) * scale, e["text"]) for e in ents if e["layer"].upper() == LAYER_DATA and e["type"] in ("TEXT", "MTEXT") and e["x"] is not None]
    planes, warnings = [], []
    for n, i in enumerate(order, start=1):
        box = boxes[i]
        here = [t for x, y, t in texts if _inside(box, x, y)]
        data = _text_data(here)
        inside = [o for o in obstacles if _inside(box, o["x0"], o["y0"]) and _inside(box, o["x1"], o["y1"])]
        planes.append(_plane(n, box, data, inside, setback_m))
        if "azimuth_deg" not in data:
            warnings.append(item("roof_dxf_azimuth", plane=f"R{n}"))
        if "tilt_deg" not in data:
            warnings.append(item("roof_dxf_tilt", plane=f"R{n}"))
    lost = len(obstacles) - sum(len(p["obstacles"]) for p in planes)
    warnings += [item("roof_dxf_obstacles", n=lost)] if lost else []
    return {"schema_version": SCHEMA_VERSION, "planes": planes, "warnings": warnings, "source": {"units_code": code, "to_metres": scale, "layers": [LAYER_PLANE, LAYER_OBSTACLE, LAYER_DATA]}}
