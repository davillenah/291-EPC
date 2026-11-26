"""Metrics of a recognized plan against the truth with coordinates (see `planta_prueba.verdad`): openings matched by place (precision, recall, F1), the overlap of the walls (IoU), the error of the
thickness of each wall, and the area of each room. The plan is put in the frame of the truth by the scale fitted to its walls (the error of the scale it says is reported apart) and the corner of its walls."""
import math
from typing import Dict, List, Tuple

import numpy as np

CELL = 5.0                      # cm per cell of the wall masks


def _frame(arch, truth: dict):
    """Found plan units to truth cm. A plan that says its units is placed by them; one that does not has only an estimate, and its scale is the one fitted to the walls (the extent of their axes against the truth's):
    the error of the estimate is reported on its own (`scale_error_pct`) so that it does not hide how well the plan was read. The corner of the walls' axes is the origin of both."""
    xs = [c for w in arch.walls for c in (w.a[0], w.b[0])]
    ys = [c for w in arch.walls for c in (w.a[1], w.b[1])]
    txs = [c for m in truth["muros"] for c in (m["a"][0], m["b"][0])]
    tys = [c for m in truth["muros"] for c in (m["a"][1], m["b"][1])]
    stated = 100.0 / arch.units_per_metre
    fitted = ((max(txs) - min(txs)) / max(max(xs) - min(xs), 1e-9) + (max(tys) - min(tys)) / max(max(ys) - min(ys), 1e-9)) / 2
    k = fitted if any("units were not known" in w for w in arch.warnings) else stated
    return (lambda p: (min(txs) + (p[0] - min(xs)) * k, min(tys) + (p[1] - min(ys)) * k)), k, round((stated / k - 1) * 100, 1)


def _f1(tp: int, found: int, truth: int) -> Dict[str, float]:
    p = tp / found if found else (1.0 if not truth else 0.0)
    r = tp / truth if truth else 1.0
    return {"precision": round(p, 2), "recall": round(r, 2), "f1": round(2 * p * r / (p + r), 2) if p + r else 0.0}


def match_openings(found: List[Tuple[float, float]], truth: List[Tuple[float, float, float]]) -> int:
    """True positives: each truth opening takes the nearest found one within half its width (at least 30 cm)."""
    free, tp = list(found), 0
    for x, y, w in truth:
        best = min(free, key=lambda p: math.hypot(p[0] - x, p[1] - y), default=None)
        if best is not None and math.hypot(best[0] - x, best[1] - y) <= max(30.0, 0.5 * w):
            free.remove(best)
            tp += 1
    return tp


def _mask(rects: List[List[Tuple[float, float]]], shape: Tuple[int, int], origin: Tuple[float, float]) -> np.ndarray:
    m = np.zeros(shape, bool)
    for q in rects:
        xs, ys = [p[0] for p in q], [p[1] for p in q]
        x0, x1 = int((min(xs) - origin[0]) / CELL), int(math.ceil((max(xs) - origin[0]) / CELL))
        y0, y1 = int((min(ys) - origin[1]) / CELL), int(math.ceil((max(ys) - origin[1]) / CELL))
        m[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)] = True
    return m


def _wall_boxes(axes: List[Tuple[Tuple[float, float], Tuple[float, float], float]]):
    """The box each wall covers, as an axis-aligned rectangle (the walls of these plans are horizontal or vertical)."""
    out = []
    for a, b, t in axes:
        h = t / 2
        out.append([(min(a[0], b[0]) - (h if a[1] == b[1] else 0) - (0 if a[1] == b[1] else h), min(a[1], b[1]) - (h if a[0] == b[0] else 0) - (0 if a[0] == b[0] else h)),
                    (max(a[0], b[0]) + (h if a[1] == b[1] else 0) + (0 if a[1] == b[1] else h), max(a[1], b[1]) + (h if a[0] == b[0] else 0) + (0 if a[0] == b[0] else h))])
    return out


def _opening_boxes(arch, to_cm, k: float):
    """What each opening takes of its wall (its width by the wall's thickness): the wall is not there, but it is the wall's line, which the truth walls cover whole."""
    out = []
    for o in arch.openings:
        c = to_cm(o.at)
        horizontal = o.angle < 45 or o.angle > 135
        hw, ht = o.width * k / 2, (arch.wall_thickness or 0) * k / 2
        dx, dy = (hw, ht) if horizontal else (ht, hw)
        out.append([(c[0] - dx, c[1] - dy), (c[0] + dx, c[1] + dy)])
    return out


def wall_iou(found_boxes, truth_boxes) -> float:
    pts = [p for q in found_boxes + truth_boxes for p in q]
    origin = (min(p[0] for p in pts), min(p[1] for p in pts))
    shape = (int((max(p[1] for p in pts) - origin[1]) / CELL) + 2, int((max(p[0] for p in pts) - origin[0]) / CELL) + 2)
    a, b = _mask(found_boxes, shape, origin), _mask(truth_boxes, shape, origin)
    return round(float((a & b).sum() / max((a | b).sum(), 1)), 3)


def thickness_error(found, truth_walls) -> float:
    """Mean absolute error in cm of the thickness of each found wall against the truth wall it lies on (parallel, midpoint within 25 cm of its axis)."""
    errs = []
    for (a, b, t) in found:
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        horizontal = abs(a[1] - b[1]) < abs(a[0] - b[0])
        for m in truth_walls:
            ta, tb = m["a"], m["b"]
            if (abs(ta[1] - tb[1]) < abs(ta[0] - tb[0])) != horizontal:
                continue
            d = abs(mid[1] - ta[1]) if horizontal else abs(mid[0] - ta[0])
            lo, hi = (min(ta[0], tb[0]), max(ta[0], tb[0])) if horizontal else (min(ta[1], tb[1]), max(ta[1], tb[1]))
            along = mid[0] if horizontal else mid[1]
            if d <= 25 and lo - 25 <= along <= hi + 25:
                errs.append(abs(t - m["espesor_cm"]))
                break
    return round(sum(errs) / len(errs), 1) if errs else float("nan")


def measure(arch, truth: dict) -> Dict[str, object]:
    if not arch.units_per_metre or not arch.walls:
        return {"error": "no scale or no walls"}
    to_cm, k, scale_error = _frame(arch, truth)
    out: Dict[str, object] = {"scale_error_pct": scale_error}
    for kind, key in (("door", "puertas"), ("window", "ventanas"), ("opening", "huecos")):
        found = [to_cm(o.at) for o in arch.openings if o.kind == kind]
        tr = [(a["at"][0], a["at"][1], a["ancho_cm"]) for a in truth[key]]
        out[kind] = _f1(match_openings(found, tr), len(found), len(tr))
    fw = [(to_cm(w.a), to_cm(w.b), w.thickness * k) for w in arch.walls]
    tw = [(tuple(m["a"]), tuple(m["b"]), float(m["espesor_cm"])) for m in truth["muros"]]
    out["wall_iou"] = wall_iou(_wall_boxes(fw) + _opening_boxes(arch, to_cm, k), _wall_boxes(tw))
    out["wall_thickness_err_cm"] = thickness_error(fw, truth["muros"])
    areas = []
    for r in arch.rooms:
        x, y = to_cm(r.at)
        for t in truth["ambientes"]:
            x0, y0, x1, y1 = t["rect"]
            if x0 <= x <= x1 and y0 <= y <= y1 and r.area_m2:
                areas.append(abs(r.area_m2 - t["m2_net"]) / t["m2_net"] * 100)
                break
    out["room_count_delta"] = len(arch.rooms) - len(truth["ambientes"])
    out["room_area_err_pct"] = round(sum(areas) / len(areas), 1) if areas else None
    return out
