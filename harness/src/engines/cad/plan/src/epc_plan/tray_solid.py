"""A ladder tray as a 3D mesh: two side rails and the rungs, swept along the 3D path of the run. Pure geometry: sizes arrive as arguments (metres, or any one unit), the caller writes the DXF.

`path3d` turns a run (points x, y, z) into the path of the axis: the corners in plan are rounded by `radius` (`tray_draw.fillet_path`) and the changes of height by `vertical_radius`, so a tray that
climbs, crosses over another and comes back down is one smooth path. `ladder_mesh` then builds, for each stretch of the path, the two rails (a box `rail` thick and `depth` high) and a rung every
`rung_pitch` (a box `rung` wide and `rung_thick` thick), and returns {"vertices": [[x, y, z]], "faces": [[i, j, k, l]]}, the shape the 3D scene already uses.
"""
import math
from typing import Dict, List, Sequence, Tuple

from . import tray_draw

P3 = Tuple[float, float, float]


def _dedupe3(pts: Sequence[P3]) -> List[P3]:
    return [p for i, p in enumerate(pts) if i == 0 or math.dist(p, pts[i - 1]) > 1e-9]


def _z_at(profile: Sequence[Tuple[float, float]], s: float) -> float:
    for (s0, z0), (s1, z1) in zip(profile, profile[1:]):
        if s <= s1 + 1e-9:
            return z0 if s1 - s0 < 1e-12 else z0 + (z1 - z0) * min(max((s - s0) / (s1 - s0), 0.0), 1.0)
    return profile[-1][1]


def _profile(run: Sequence[P3], vertical_radius: float) -> List[Tuple[float, float]]:
    """(distance walked in plan, height) of the run, with the changes of height rounded by `vertical_radius`."""
    walked, profile = 0.0, []
    for i, p in enumerate(run):
        if i:
            walked += math.dist(run[i - 1][:2], p[:2])
        profile.append((walked, p[2]))
    return tray_draw.fillet_path(profile, vertical_radius) if vertical_radius > 0 else profile


def _point_at(plan: Sequence[Tuple[float, float]], marks: Sequence[float], s: float) -> Tuple[float, float]:
    """The point of the plan path at distance `s` (`marks` holds the distance of every vertex)."""
    for i in range(len(plan) - 1):
        if s <= marks[i + 1] + 1e-9:
            t = 0.0 if marks[i + 1] - marks[i] < 1e-12 else (s - marks[i]) / (marks[i + 1] - marks[i])
            return (plan[i][0] + (plan[i + 1][0] - plan[i][0]) * t, plan[i][1] + (plan[i + 1][1] - plan[i][1]) * t)
    return plan[-1]


def path3d(run: Sequence[P3], radius: float, vertical_radius: float) -> List[P3]:
    """The axis of a run as 3D points: plan corners rounded by `radius`, height changes rounded by `vertical_radius`."""
    plan = tray_draw.fillet_path([p[:2] for p in run], radius)
    profile = _profile(run, vertical_radius)
    walked = profile[-1][0]
    marks = [0.0]
    for a, b in zip(plan, plan[1:]):
        marks.append(marks[-1] + math.dist(a, b))
    scale = walked / (marks[-1] or 1.0)
    marks = [m * scale for m in marks]
    stops = sorted(set(marks) | {s for s, _ in profile})              # every vertex of the plan and every bend of the profile
    return _dedupe3([(*_point_at(plan, marks, s), _z_at(profile, s)) for s in stops])


def _frame(a: P3, b: P3) -> Tuple[P3, P3, P3]:
    """Unit vectors along the stretch, to its left (horizontal) and 'up' (across both)."""
    d = math.dist(a, b)
    u = ((b[0] - a[0]) / d, (b[1] - a[1]) / d, (b[2] - a[2]) / d)
    h = math.hypot(u[0], u[1])
    n = (-u[1] / h, u[0] / h, 0.0) if h > 1e-9 else (0.0, 1.0, 0.0)
    v = (n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0])
    return u, n, v


def _box(vertices: List[List[float]], faces: List[List[int]], centre: P3, axes: Tuple[P3, P3, P3], size: Tuple[float, float, float]) -> None:
    """A box with the given centre, the three unit axes and the full size along each."""
    base = len(vertices)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                vertices.append([centre[k] + axes[0][k] * sx * size[0] / 2 + axes[1][k] * sy * size[1] / 2 + axes[2][k] * sz * size[2] / 2 for k in range(3)])
    for quad in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        faces.append([base + i for i in quad])


def rail_section(depth: float, foot: float, curl: float) -> List[Tuple[float, float]]:
    """The centre line of a cold-formed rail (a C with the bottom foot turned in and the top edge rolled), as (inward, height above the bottom) pairs."""
    return [(foot, 0.0), (0.0, 0.0), (0.0, depth - curl), (curl / 3, depth - curl / 3), (curl, depth), (curl * 1.4, depth - curl / 3)]


def _quad(vertices: List[List[float]], faces: List[List[int]], corners: Sequence[P3]) -> None:
    base = len(vertices)
    vertices.extend([list(c) for c in corners])
    faces.append([base, base + 1, base + 2, base + 3])


def _web(vertices: List[List[float]], faces: List[List[int]], a: P3, length: float, axes: Tuple[P3, P3, P3], lateral: float, depth: float, p: Dict[str, float]) -> None:
    """The web of a rail from `a` along its length, with the side slots left open: the slot pitch, length and height come from `p` (`slot_pitch`, `slot`, `slot_height`)."""
    u, n, v = axes
    top = depth - p["curl"]
    mid = (top - p["slot_height"]) / 2
    pieces = []
    at = 0.0
    while at < length - 1e-9:
        end = min(at + p["slot_pitch"] - p["slot"], length)
        pieces.append((at, end, 0.0, top))
        if end < length - 1e-9:
            stop = min(end + p["slot"], length)
            pieces.append((end, stop, 0.0, mid))
            pieces.append((end, stop, mid + p["slot_height"], top))
        at = end + p["slot"]
    for s0, s1, h0, h1 in pieces:
        _quad(vertices, faces, [tuple(a[k] + u[k] * x + n[k] * lateral + v[k] * (h - depth / 2) for k in range(3)) for x, h in ((s0, h0), (s1, h0), (s1, h1), (s0, h1))])


def _rail(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], side: int, width: float, depth: float, p: Dict[str, float]) -> None:
    """A rail as a sheet swept along a..b: one quad per segment of its section, the web with its side slots."""
    u, n, v = axes
    section = rail_section(depth, p["foot"], p["curl"])
    base = len(vertices)
    for end in (a, b):
        for inward, height in section:
            lateral = side * width / 2 - side * inward
            vertices.append([end[k] + n[k] * lateral + v[k] * (height - depth / 2) for k in range(3)])
    count = len(section)
    for i in range(count - 1):
        if i == 1 and "slot" in p:
            continue
        faces.append([base + i, base + i + 1, base + count + i + 1, base + count + i])
    if "slot" in p:
        _web(vertices, faces, a, math.dist(a, b), axes, side * width / 2, depth, p)


def ladder_mesh(path: Sequence[P3], width: float, depth: float, p: Dict[str, float]) -> Dict[str, list]:
    """The mesh of a ladder tray along `path`: `width` clear width, `depth` rail height; `p` has `rail` (thickness of the rail), `rung` (width of a rung), `rung_thick` and `rung_pitch`."""
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    due = p["rung_pitch"] / 2
    walked = 0.0
    for a, b in zip(path, path[1:]):
        length = math.dist(a, b)
        if length < 1e-9:
            continue
        u, n, v = _frame(a, b)
        mid = tuple((a[k] + b[k]) / 2 for k in range(3))
        for side in (-1, 1):
            off = side * (width / 2 + p["rail"] / 2)
            if "foot" in p:
                _rail(vertices, faces, a, b, (u, n, v), side, width, depth, p)
                continue
            _box(vertices, faces, tuple(mid[k] + n[k] * off for k in range(3)), (u, n, v), (length, p["rail"], depth))
        while due < walked + length - 1e-9:
            t = due - walked
            at = tuple(a[k] + u[k] * t for k in range(3))
            _box(vertices, faces, tuple(at[k] - v[k] * (depth / 2 - p["rung_thick"] / 2) for k in range(3)), (u, n, v), (p["rung"], width, p["rung_thick"]))
            due += p["rung_pitch"]
        walked += length
    return {"vertices": vertices, "faces": faces}


def solid(ident: str, tag: str, run: Sequence[P3], layer: str, width: float, depth: float, p: Dict[str, float], radius: float, vertical_radius: float,
          level: str = "") -> Dict[str, object]:
    """One tray as a solid of the 3D scene (the same plain data `scene3d` shows and writes: id, tag, kind, discipline, level, layer and the mesh), in the units of its arguments."""
    return {"id": ident, "tag": tag, "kind": "tray", "discipline": "electricidad", "level": level, "layer": layer,
            "mesh": ladder_mesh(path3d(run, radius, vertical_radius), width, depth, p)}
