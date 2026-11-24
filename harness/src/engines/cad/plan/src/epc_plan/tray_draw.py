"""How a cable tray looks from above (plan view), as lines: pure geometry, the caller draws them.

A tray is a path (its axis) with a width. Four kinds: `escalera` (ladder: two side rails with their return lip and rungs), `perforada` (perforated floor
between the rails, with its slots), `ciega` (solid floor) and `alambre` (wire mesh). Every kind shows a joint every nominal length of a section and bends with a
radius. All sizes arrive as arguments in drawing units; nothing is read from files or the environment.
"""
import math
from typing import Dict, List, Sequence, Tuple

from epc_plan.core import PlanError

Point = Tuple[float, float]
Line = Tuple[Point, Point]
KINDS = ("escalera", "perforada", "ciega", "alambre")


def _dedupe(pts: Sequence[Point]) -> List[Point]:
    return [p for i, p in enumerate(pts) if i == 0 or math.dist(p, pts[i - 1]) > 1e-9]


def fillet_path(pts: Sequence[Point], radius: float, steps: int = 8) -> List[Point]:
    """The path with every corner rounded by an arc of `radius` (drawn as `steps` chords); a corner whose stretches are too short for the arc stays square."""
    pts = _dedupe(pts)
    if len(pts) < 3 or radius <= 0:
        return list(pts)
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        out += _corner(pts[i - 1], pts[i], pts[i + 1], radius, steps)
    return out + [pts[-1]]


def _corner(a: Point, b: Point, c: Point, radius: float, steps: int) -> List[Point]:
    d1, d2 = math.dist(a, b), math.dist(b, c)
    u1, u2 = ((b[0] - a[0]) / d1, (b[1] - a[1]) / d1), ((c[0] - b[0]) / d2, (c[1] - b[1]) / d2)
    turn = math.atan2(u1[0] * u2[1] - u1[1] * u2[0], u1[0] * u2[0] + u1[1] * u2[1])
    reach = radius * math.tan(abs(turn) / 2)
    if abs(turn) < 1e-6 or reach > min(d1, d2) / 2 + 1e-9:      # straight on, or no room for the arc: the corner stays
        return [b]
    start = (b[0] - u1[0] * reach, b[1] - u1[1] * reach)
    side = 1.0 if turn > 0 else -1.0                              # the centre of the arc is on the inside of the turn
    centre = (start[0] - u1[1] * radius * side, start[1] + u1[0] * radius * side)
    first = math.atan2(start[1] - centre[1], start[0] - centre[0])
    return [(centre[0] + radius * math.cos(first + turn * k / steps), centre[1] + radius * math.sin(first + turn * k / steps)) for k in range(steps + 1)]


def offset_path(pts: Sequence[Point], d: float) -> List[Point]:
    """The path moved sideways by `d` (left of the walking direction when positive); the corners are mitred, so the two edges of a bend meet."""
    pts = _dedupe(pts)
    if len(pts) < 2:
        return list(pts)
    normals = []
    for a, b in zip(pts, pts[1:]):
        length = math.dist(a, b)
        normals.append((-(b[1] - a[1]) / length, (b[0] - a[0]) / length))
    out = [(pts[0][0] + normals[0][0] * d, pts[0][1] + normals[0][1] * d)]
    for i in range(1, len(pts) - 1):
        (n1x, n1y), (n2x, n2y) = normals[i - 1], normals[i]
        k = max(1 + n1x * n2x + n1y * n2y, 1e-6)                   # 1 + cos of the turn: the corner moves d / (that / 2) along the bisector
        out.append((pts[i][0] + (n1x + n2x) * d / k, pts[i][1] + (n1y + n2y) * d / k))
    out.append((pts[-1][0] + normals[-1][0] * d, pts[-1][1] + normals[-1][1] * d))
    return out


def stations(pts: Sequence[Point], step: float, first: float = 0.0) -> List[Tuple[Point, Point]]:
    """(point, unit direction) every `step` along the path by length, starting `first` from its start, never at the very start or end."""
    pts = _dedupe(pts)
    out: List[Tuple[Point, Point]] = []
    walked, due = 0.0, first if first > 0 else step
    for a, b in zip(pts, pts[1:]):
        length = math.dist(a, b)
        u = ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
        while due < walked + length - 1e-9:
            t = due - walked
            out.append(((a[0] + u[0] * t, a[1] + u[1] * t), u))
            due += step
        walked += length
    return out


def _across(point: Point, u: Point, d1: float, d2: float) -> Line:
    """A line across the path at `point` from `d1` to `d2` on the left of the direction `u`."""
    return ((point[0] - u[1] * d1, point[1] + u[0] * d1), (point[0] - u[1] * d2, point[1] + u[0] * d2))


def _along(path: Sequence[Point], d: float) -> List[Line]:
    side = offset_path(path, d)
    return list(zip(side, side[1:]))


def _rails(path, half: float, lip: float) -> List[Line]:
    """The two side rails: each is its outer edge and the edge of its return lip."""
    return [ln for d in (half, -half) for ln in _along(path, d) + _along(path, d - lip * (1 if d > 0 else -1))]


def _ladder(path, half, p) -> List[Line]:
    lines = _rails(path, half, p["lip"])
    for point, u in stations(path, p["rung_pitch"]):
        for off in (-p["rung_width"] / 2, p["rung_width"] / 2):
            lines.append(_rung_edge(point, u, half - p["lip"], off))
    return lines


def _rung_edge(point, u, reach, off) -> Line:
    shifted = (point[0] + u[0] * off, point[1] + u[1] * off)
    return _across(shifted, u, -reach, reach)


def _floor(path, half, p, slots: bool) -> List[Line]:
    lines = _rails(path, half, p["lip"])
    if slots:
        for point, u in stations(path, p["slot_pitch"]):
            for d in (-half / 2, half / 2):
                lines.append(((point[0] - u[0] * p["slot_length"] / 2 - u[1] * d, point[1] - u[1] * p["slot_length"] / 2 + u[0] * d),
                              (point[0] + u[0] * p["slot_length"] / 2 - u[1] * d, point[1] + u[1] * p["slot_length"] / 2 + u[0] * d)))
    return lines


def _mesh(path, half, p) -> List[Line]:
    lines = [ln for d in (half, -half) for ln in _along(path, d)]
    lines += [ln for d in (-half / 2, 0.0, half / 2) for ln in _along(path, d)]
    lines += [_across(point, u, -half, half) for point, u in stations(path, p["wire_pitch"])]
    return lines


def tray_lines(pts: Sequence[Point], kind: str, width: float, p: Dict[str, float]) -> List[Line]:
    """The lines of one tray: `pts` is its axis, `width` its clear width and `p` the drawing sizes (`lip`, `rung_pitch`, `rung_width`, `slot_pitch`, `slot_length`,
    `wire_pitch`, `radius`, `joint_pitch`), all in drawing units. The joints of the sections are drawn as a line across every `joint_pitch`."""
    if kind not in KINDS:
        raise PlanError("err_tray_kind", kind=kind, kinds=", ".join(KINDS))
    path = fillet_path(pts, p["radius"] + width / 2)               # the radius of the catalogue is the inside one
    half = width / 2
    body = {"escalera": lambda: _ladder(path, half, p), "perforada": lambda: _floor(path, half, p, True), "ciega": lambda: _floor(path, half, p, False), "alambre": lambda: _mesh(path, half, p)}[kind]()
    return body + [_across(point, u, -half, half) for point, u in stations(path, p["joint_pitch"])]


def support_shapes(pts: Sequence[Point], width: float, p: Dict[str, float]) -> Dict[str, list]:
    """The trapeze hangers of a tray seen from above, one every `support_spacing` along its axis: a bar (`support_channel` deep, the tray width plus `support_overhang` on each
    side) with a threaded rod of diameter `support_rod` at each end. Returns {"lines": [(a, b)], "circles": [(centre, radius)]}; `radius` and the sizes are drawing units."""
    path = fillet_path(pts, p["radius"] + width / 2)
    half = width / 2 + p["support_overhang"]
    lines: List[Line] = []
    circles = []
    for point, u in stations(path, p["support_spacing"]):
        a, b = _across(point, u, -half, half)
        d = p["support_channel"] / 2
        corners = [(a[0] - u[0] * d, a[1] - u[1] * d), (b[0] - u[0] * d, b[1] - u[1] * d), (b[0] + u[0] * d, b[1] + u[1] * d), (a[0] + u[0] * d, a[1] + u[1] * d)]
        lines += [(corners[i], corners[(i + 1) % 4]) for i in range(4)]
        circles += [(a, p["support_rod"] / 2), (b, p["support_rod"] / 2)]
    return {"lines": lines, "circles": circles}
