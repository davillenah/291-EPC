"""Trays at different heights: where two trays cross, which one goes over, the lines of the lower one broken under the upper one, the side view of a run that climbs
and descends, and the symbol of a vertical riser. Pure geometry: every size arrives as an argument in drawing units and the caller draws the lines.

A run is a list of 3D points (x, y, z). The crossing of two runs is found in plan; the height of each at the crossing is read along its own stretch. The higher one is
drawn whole; the lower one is broken under it (with `clearance` on each side), as plans show a crossing. A crossing with less than `min_gap` between them is reported
as a conflict instead of being drawn as solved.
"""
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import tray_draw

Point = Tuple[float, float]
Point3 = Tuple[float, float, float]
Line = Tuple[Point, Point]


def _intersection(a0: Point, a1: Point, b0: Point, b1: Point) -> Optional[Tuple[float, float]]:
    """(t, u) along each segment where they cross, or None when they are parallel or do not meet."""
    dx, dy = a1[0] - a0[0], a1[1] - a0[1]
    ex, ey = b1[0] - b0[0], b1[1] - b0[1]
    det = dx * ey - dy * ex
    if abs(det) < 1e-12:
        return None
    t = ((b0[0] - a0[0]) * ey - (b0[1] - a0[1]) * ex) / det
    u = ((b0[0] - a0[0]) * dy - (b0[1] - a0[1]) * dx) / det
    return (t, u) if 0 <= t <= 1 and 0 <= u <= 1 else None


def crossings(a: Sequence[Point3], b: Sequence[Point3], min_gap: float) -> List[Dict[str, Any]]:
    """Every place where the plan of run `a` crosses the plan of run `b`: `at` (x, y), `za` and `zb` (heights there), `upper` ("a" or "b"), `gap` (the difference of heights) and
    `ok` (False when the gap is under `min_gap`, a conflict the engineer has to solve). `seg_a` and `seg_b` are the stretch index of each run."""
    found = []
    for i in range(len(a) - 1):
        for j in range(len(b) - 1):
            hit = _intersection(a[i][:2], a[i + 1][:2], b[j][:2], b[j + 1][:2])
            if hit is None:
                continue
            t, u = hit
            za = a[i][2] + (a[i + 1][2] - a[i][2]) * t
            zb = b[j][2] + (b[j + 1][2] - b[j][2]) * u
            at = (a[i][0] + (a[i + 1][0] - a[i][0]) * t, a[i][1] + (a[i + 1][1] - a[i][1]) * t)
            found.append({"at": at, "za": za, "zb": zb, "upper": "a" if za >= zb else "b", "gap": abs(za - zb), "ok": abs(za - zb) >= min_gap, "seg_a": i, "seg_b": j})
    return found


def _footprint(pts: Sequence[Point], width: float, clearance: float) -> List[List[Point]]:
    """One rectangle per stretch of the tray: its width plus `clearance` on each side, and `clearance` past each end."""
    rects = []
    for p, q in zip(pts, pts[1:]):
        length = math.dist(p, q)
        if length < 1e-9:
            continue
        u = ((q[0] - p[0]) / length, (q[1] - p[1]) / length)
        n = (-u[1], u[0])
        h = width / 2 + clearance
        s = p[0] - u[0] * clearance, p[1] - u[1] * clearance
        e = q[0] + u[0] * clearance, q[1] + u[1] * clearance
        rects.append([(s[0] + n[0] * h, s[1] + n[1] * h), (e[0] + n[0] * h, e[1] + n[1] * h), (e[0] - n[0] * h, e[1] - n[1] * h), (s[0] - n[0] * h, s[1] - n[1] * h)])
    return rects


def _inside(line: Line, rect: Sequence[Point]) -> Optional[Tuple[float, float]]:
    """The part of a segment (as a range of t from 0 to 1) that lies inside a convex rectangle (Cyrus-Beck), or None when none of it does."""
    (x0, y0), (x1, y1) = line
    centre = (sum(c[0] for c in rect) / 4, sum(c[1] for c in rect) / 4)
    t0, t1 = 0.0, 1.0
    for i in range(4):
        p, q = rect[i], rect[(i + 1) % 4]
        nx, ny = q[1] - p[1], -(q[0] - p[0])
        if nx * (centre[0] - p[0]) + ny * (centre[1] - p[1]) > 0:   # the normal points outward
            nx, ny = -nx, -ny
        num = nx * (p[0] - x0) + ny * (p[1] - y0)
        den = nx * (x1 - x0) + ny * (y1 - y0)
        if abs(den) < 1e-12:
            if num < 0:
                return None                                         # parallel and outside this side
            continue
        t = num / den
        t0, t1 = (t0, min(t1, t)) if den > 0 else (max(t0, t), t1)
    return (t0, t1) if t0 < t1 else None


def _outside(line: Line, rect: Sequence[Point]) -> List[Line]:
    """The parts of a segment that lie outside a convex rectangle: the whole line, or up to two pieces."""
    span = _inside(line, rect)
    if span is None:
        return [line]
    (x0, y0), (x1, y1) = line
    at = lambda k: (x0 + (x1 - x0) * k, y0 + (y1 - y0) * k)
    pieces = []
    if span[0] > 1e-9:
        pieces.append((at(0.0), at(span[0])))
    if span[1] < 1 - 1e-9:
        pieces.append((at(span[1]), at(1.0)))
    return pieces


def break_under(lines: Sequence[Line], upper_pts: Sequence[Point], upper_width: float, clearance: float) -> List[Line]:
    """The lines of the lower tray with the part under the upper tray taken out (the upper tray and `clearance` on each side), as a plan shows a crossing."""
    rects = _footprint(upper_pts, upper_width, clearance)
    out = list(lines)
    for rect in rects:
        out = [piece for ln in out for piece in _outside(ln, rect)]
    return out


def profile(run: Sequence[Point3], depth: float, radius: float) -> Dict[str, Any]:
    """The side view of a run: x is the distance walked in plan, y the height. Returns the axis, the top and bottom edges of the tray (`depth` is its side height) with the
    vertical bends rounded by `radius`, as {"axis": [...], "lines": [(a, b)]}."""
    walked = 0.0
    pts: List[Point] = []
    for i, p in enumerate(run):
        if i:
            walked += math.dist(run[i - 1][:2], p[:2])
        pts.append((walked, p[2]))
    axis = tray_draw.fillet_path(pts, radius)
    top, bottom = tray_draw.offset_path(axis, depth / 2), tray_draw.offset_path(axis, -depth / 2)
    return {"axis": axis, "lines": list(zip(top, top[1:])) + list(zip(bottom, bottom[1:]))}


def riser(at: Point, width: float, length: float) -> Dict[str, Any]:
    """The plan symbol of a vertical tray: the rectangle of its section crossed by its two diagonals. Returns {"lines": [(a, b)]}."""
    hx, hy = length / 2, width / 2
    c = [(at[0] - hx, at[1] - hy), (at[0] + hx, at[1] - hy), (at[0] + hx, at[1] + hy), (at[0] - hx, at[1] + hy)]
    return {"lines": [(c[i], c[(i + 1) % 4]) for i in range(4)] + [(c[0], c[2]), (c[1], c[3])]}
