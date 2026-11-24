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


def path3d(run: Sequence[P3], radius: float, vertical_radius: float) -> List[P3]:
    """The axis of a run as 3D points: plan corners rounded by `radius`, height changes rounded by `vertical_radius`."""
    plan = tray_draw.fillet_path([p[:2] for p in run], radius)
    walked, profile = 0.0, []
    for i, p in enumerate(run):
        if i:
            walked += math.dist(run[i - 1][:2], p[:2])
        profile.append((walked, p[2]))
    profile = tray_draw.fillet_path(profile, vertical_radius) if vertical_radius > 0 else profile
    total_plan = sum(math.dist(a, b) for a, b in zip(plan, plan[1:])) or 1.0
    scale = walked / total_plan
    out: List[P3] = []
    along = 0.0
    for i, p in enumerate(plan):
        if i:
            along += math.dist(plan[i - 1], p)
        out.append((p[0], p[1], _z_at(profile, along * scale)))
    cuts = [s for s, _ in profile]                                   # make sure every bend of the profile is a vertex of the path
    s_plan = [0.0]
    for a, b in zip(plan, plan[1:]):
        s_plan.append(s_plan[-1] + math.dist(a, b) * scale)
    for s in cuts:
        for i in range(len(plan) - 1):
            if s_plan[i] + 1e-6 < s < s_plan[i + 1] - 1e-6:
                t = (s - s_plan[i]) / (s_plan[i + 1] - s_plan[i])
                at = (plan[i][0] + (plan[i + 1][0] - plan[i][0]) * t, plan[i][1] + (plan[i + 1][1] - plan[i][1]) * t, _z_at(profile, s))
                out.append(at)
    out.sort(key=lambda q: _s_of(q, plan, s_plan))
    return _dedupe3(out)


def _s_of(q: P3, plan: Sequence[Tuple[float, float]], s_plan: Sequence[float]) -> float:
    best, at = 1e18, 0.0
    for i in range(len(plan) - 1):
        a, b = plan[i], plan[i + 1]
        length = math.dist(a, b)
        if length < 1e-12:
            continue
        t = max(0.0, min(1.0, ((q[0] - a[0]) * (b[0] - a[0]) + (q[1] - a[1]) * (b[1] - a[1])) / length ** 2))
        d = math.hypot(q[0] - (a[0] + (b[0] - a[0]) * t), q[1] - (a[1] + (b[1] - a[1]) * t))
        if d < best - 1e-9:
            best, at = d, s_plan[i] + (s_plan[i + 1] - s_plan[i]) * t
    return at


def _frame(a: P3, b: P3) -> Tuple[P3, P3, P3]:
    """Unit vectors along the stretch, to its left (horizontal) and 'up' (across both)."""
    d = math.dist(a, b)
    u = ((b[0] - a[0]) / d, (b[1] - a[1]) / d, (b[2] - a[2]) / d)
    h = math.hypot(u[0], u[1])
    n = (-u[1] / h, u[0] / h, 0.0) if h > 1e-9 else (0.0, 1.0, 0.0)
    v = (u[1] * n[2] - u[2] * n[1], u[2] * n[0] - u[0] * n[2], u[0] * n[1] - u[1] * n[0])
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
            _box(vertices, faces, tuple(mid[k] + n[k] * off for k in range(3)), (u, n, v), (length, p["rail"], depth))
        while due < walked + length - 1e-9:
            t = due - walked
            at = tuple(a[k] + u[k] * t for k in range(3))
            _box(vertices, faces, tuple(at[k] - v[k] * (depth / 2 - p["rung_thick"] / 2) for k in range(3)), (u, n, v), (p["rung"], width, p["rung_thick"]))
            due += p["rung_pitch"]
        walked += length
    return {"vertices": vertices, "faces": faces}
