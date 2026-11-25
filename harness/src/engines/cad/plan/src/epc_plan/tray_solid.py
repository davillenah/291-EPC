"""A ladder tray as a 3D mesh: two side rails and the rungs, swept along the 3D path of the run. Pure geometry: sizes arrive as arguments (metres, or any one unit), the caller writes the DXF.

`path3d` turns a run (points x, y, z) into the path of the axis: the corners in plan are rounded by `radius` (`tray_draw.fillet_path`) and the changes of height by `vertical_radius`, so a tray that
climbs, crosses over another and comes back down is one smooth path. `ladder_mesh` then builds, for each stretch of the path, the two rails (a box `rail` thick and `depth` high) and a rung every
`rung_pitch` (a box `rung` wide and `rung_thick` thick), and returns {"vertices": [[x, y, z]], "faces": [[i, j, k, l]]}, the shape the 3D scene already uses.
"""
import math
from typing import Dict, List, Optional, Sequence, Tuple

from . import tray_draw
from .core import PlanError

P3 = Tuple[float, float, float]


def _dedupe3(pts: Sequence[P3]) -> List[P3]:
    return [p for i, p in enumerate(pts) if i == 0 or math.dist(p, pts[i - 1]) > 1e-9]


def _z_at(profile: Sequence[Tuple[float, float]], s: float) -> float:
    for (s0, z0), (s1, z1) in zip(profile, profile[1:]):
        if s <= s1 + 1e-9:
            return z0 if s1 - s0 < 1e-12 else z0 + (z1 - z0) * min(max((s - s0) / (s1 - s0), 0.0), 1.0)
    return profile[-1][1]


def _profile(run: Sequence[P3], vertical_radius: float, links: int = 8) -> List[Tuple[float, float]]:
    """(distance walked in plan, height) of the run, with the changes of height rounded by `vertical_radius`."""
    walked, profile = 0.0, []
    for i, p in enumerate(run):
        if i:
            walked += math.dist(run[i - 1][:2], p[:2])
        profile.append((walked, p[2]))
    return tray_draw.fillet_path(profile, vertical_radius, links) if vertical_radius > 0 else profile


def _point_at(plan: Sequence[Tuple[float, float]], marks: Sequence[float], s: float) -> Tuple[float, float]:
    """The point of the plan path at distance `s` (`marks` holds the distance of every vertex)."""
    for i in range(len(plan) - 1):
        if s <= marks[i + 1] + 1e-9:
            t = 0.0 if marks[i + 1] - marks[i] < 1e-12 else (s - marks[i]) / (marks[i + 1] - marks[i])
            return (plan[i][0] + (plan[i + 1][0] - plan[i][0]) * t, plan[i][1] + (plan[i + 1][1] - plan[i][1]) * t)
    return plan[-1]


def path3d(run: Sequence[P3], radius: float, vertical_radius: float, links: int = 8) -> List[P3]:
    """The axis of a run as 3D points: plan corners rounded by `radius`, height changes rounded by `vertical_radius` in `links` straight stretches (the articulated bend of a catalogue has 5)."""
    plan = tray_draw.fillet_path([p[:2] for p in run], radius)
    profile = _profile(run, vertical_radius, links)
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
    v = (u[1] * n[2] - u[2] * n[1], u[2] * n[0] - u[0] * n[2], u[0] * n[1] - u[1] * n[0])
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


def _rail(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], side: int, width: float, depth: float, p: Dict[str, float],
          width_b: Optional[float] = None) -> None:
    """A rail as a sheet swept along a..b: one quad per segment of its section, the web with its side slots; with `width_b` the rail leans from `width` at a to `width_b` at b (a taper)."""
    u, n, v = axes
    section = rail_section(depth, p["foot"], p["curl"])
    base = len(vertices)
    slotted = "slot" in p and width_b is None
    for end, wide in ((a, width), (b, width if width_b is None else width_b)):
        for inward, height in section:
            lateral = side * wide / 2 - side * inward
            vertices.append([end[k] + n[k] * lateral + v[k] * (height - depth / 2) for k in range(3)])
    count = len(section)
    for i in range(count - 1):
        if i == 1 and slotted:
            continue
        faces.append([base + i, base + i + 1, base + count + i + 1, base + count + i])
    if slotted:
        _web(vertices, faces, a, math.dist(a, b), axes, side * width / 2, depth, p)


def _side_rails(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], width: float, depth: float, p: Dict[str, float]) -> None:
    """Both rails of a stretch: the cold-formed C when `p` has its sizes, a plain strip otherwise."""
    u, n, v = axes
    mid = tuple((a[k] + b[k]) / 2 for k in range(3))
    for side in (-1, 1):
        if "foot" in p:
            _rail(vertices, faces, a, b, axes, side, width, depth, p)
            continue
        off = side * (width / 2 + p["rail"] / 2)
        _box(vertices, faces, tuple(mid[k] + n[k] * off for k in range(3)), axes, (math.dist(a, b), p["rail"], depth))


def _lid(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], width: float, depth: float, p: Dict[str, float]) -> None:
    """The cover of a stretch: a flat sheet `p["cover"]` over the top of the rails."""
    n, v = axes[1], axes[2]
    corners = [tuple(e[k] + n[k] * sy * (width / 2 + p["rail"]) + v[k] * (depth / 2 + p["cover"]) for k in range(3)) for e, sy in ((a, -1), (b, -1), (b, 1), (a, 1))]
    _quad(vertices, faces, corners)


def _joints(vertices: List[List[float]], faces: List[List[int]], path: Sequence[P3], width: float, depth: float, p: Dict[str, float]) -> None:
    """The bolts of the joints: every `joint` of length of the path, four bolt heads on the outer faces of the two rails (two on each), the same for every kind of tray."""
    if "joint" not in p:
        return
    due, walked = p["joint"], 0.0
    for a, b in zip(path, path[1:]):
        length = math.dist(a, b)
        if length < 1e-9:
            continue
        axes = _frame(a, b)
        u, n, v = axes
        while due < walked + length - 1e-6:
            at = tuple(a[k] + u[k] * (due - walked) for k in range(3))
            for side in (-1, 1):
                for height in (-depth / 4, depth / 4):
                    centre = tuple(at[k] + n[k] * side * (width / 2 + p["bolt"] / 2) + v[k] * height for k in range(3))
                    _box(vertices, faces, centre, axes, (p["bolt"], p["bolt"], p["bolt"]))
            due += p["joint"]
        walked += length


def ladder_mesh(path: Sequence[P3], width: float, depth: float, p: Dict[str, float]) -> Dict[str, list]:
    """The mesh of a ladder tray along `path`: `width` clear width, `depth` rail height; `p` has `rail` (thickness of the rail), `rung` (width of a rung), `rung_thick` and `rung_pitch`;
    `foot`, `curl`, `slot_pitch`, `slot` and `slot_height` give the rails their section and side slots; `cover` adds a lid."""
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    due = p["rung_pitch"] / 2
    walked = 0.0
    for a, b in zip(path, path[1:]):
        length = math.dist(a, b)
        if length < 1e-9:
            continue
        axes = _frame(a, b)
        u, n, v = axes
        _side_rails(vertices, faces, a, b, axes, width, depth, p)
        if p.get("cover"):
            _lid(vertices, faces, a, b, axes, width, depth, p)
        while due < walked + length - 1e-9:
            at = tuple(a[k] + u[k] * (due - walked) for k in range(3))
            _box(vertices, faces, tuple(at[k] - v[k] * (depth / 2 - p["rung_thick"] / 2) for k in range(3)), axes, (p["rung"], width, p["rung_thick"]))
            due += p["rung_pitch"]
        walked += length
    _joints(vertices, faces, path, width, depth, p)
    return {"vertices": vertices, "faces": faces}


def _floor(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], width: float, depth: float, p: Dict[str, float], slotted: bool) -> None:
    """The floor of a solid-bottom tray between its rails; with `slotted`, the perforated one: a band of slots across it every `slot_pitch`."""
    u, n, v = axes
    length = math.dist(a, b)
    edge = p["floor_margin"]
    cells = []
    at = 0.0
    while at < length - 1e-9:
        solid_end = min(at + (p["slot_pitch"] - p["slot"] if slotted else length), length)
        cells.append((at, solid_end, -width / 2, width / 2))
        if slotted and solid_end < length - 1e-9:
            stop = min(solid_end + p["slot"], length)
            cells.extend([(solid_end, stop, -width / 2, -width / 2 + edge), (solid_end, stop, width / 2 - edge, width / 2)])
            at = stop
        else:
            at = length
    for s0, s1, y0, y1 in cells:
        _quad(vertices, faces, [tuple(a[k] + u[k] * x + n[k] * y - v[k] * depth / 2 for k in range(3)) for x, y in ((s0, y0), (s1, y0), (s1, y1), (s0, y1))])


def _wire(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], width: float, depth: float, p: Dict[str, float]) -> None:
    """A wire-mesh tray: a longitudinal wire along each top edge and every `wire_pitch` across the floor, and a transverse wire every `wire_pitch`."""
    u, n, v = axes
    length = math.dist(a, b)
    w = p["wire"]
    mid = tuple((a[k] + b[k]) / 2 for k in range(3))
    for y, z in [(-width / 2, depth / 2), (width / 2, depth / 2)] + [(-width / 2 + i * p["wire_pitch"], -depth / 2) for i in range(1, int(width / p["wire_pitch"]))]:
        _box(vertices, faces, tuple(mid[k] + n[k] * y + v[k] * z for k in range(3)), axes, (length, w, w))
    x = p["wire_pitch"] / 2
    while x < length:
        at = tuple(a[k] + u[k] * x for k in range(3))
        _box(vertices, faces, tuple(at[k] - v[k] * depth / 2 for k in range(3)), axes, (w, width, w))
        for side in (-1, 1):
            _box(vertices, faces, tuple(at[k] + n[k] * side * width / 2 for k in range(3)), axes, (w, w, depth))
        x += p["wire_pitch"]


def _channel(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], width: float, depth: float) -> None:
    """A U channel: the floor and the two walls, as sheets, with no return lip."""
    n, v = axes[1], axes[2]
    for (y0, z0), (y1, z1) in (((-width / 2, depth / 2), (-width / 2, -depth / 2)), ((-width / 2, -depth / 2), (width / 2, -depth / 2)), ((width / 2, -depth / 2), (width / 2, depth / 2))):
        _quad(vertices, faces, [tuple(e[k] + n[k] * y + v[k] * z for k in range(3)) for e, y, z in ((a, y0, z0), (b, y0, z0), (b, y1, z1), (a, y1, z1))])


def tray_mesh(path: Sequence[P3], width: float, depth: float, p: Dict[str, float], kind: str = "escalera") -> Dict[str, list]:
    """The mesh of a tray of the given kind (`escalera`, `perforada`, `ciega`, `alambre`, `canal`) along `path`: the ladder, or the same rails with a floor (slotted for `perforada`), or a wire mesh."""
    if kind == "escalera":
        return ladder_mesh(path, width, depth, p)
    if kind not in ("perforada", "ciega", "alambre", "canal"):
        raise PlanError("err_tray_kind", kind=kind, kinds=", ".join(tray_draw.KINDS))
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    for a, b in zip(path, path[1:]):
        if math.dist(a, b) < 1e-9:
            continue
        axes = _frame(a, b)
        if kind == "alambre":
            _wire(vertices, faces, a, b, axes, width, depth, p)
            continue
        if kind == "canal":
            _channel(vertices, faces, a, b, axes, width, depth)
            continue
        _side_rails(vertices, faces, a, b, axes, width, depth, p)
        _floor(vertices, faces, a, b, axes, width, depth, p, kind == "perforada")
        if p.get("cover"):
            _lid(vertices, faces, a, b, axes, width, depth, p)
    if kind != "alambre":
        _joints(vertices, faces, path, width, depth, p)
    return {"vertices": vertices, "faces": faces}


def _taper_rungs(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], widths: Tuple[float, float], depth: float, p: Dict[str, float]) -> None:
    """The rungs of a reducer: one every `rung_pitch`, each as wide as the taper is there."""
    u, v = axes[0], axes[2]
    length = math.dist(a, b)
    x = p["rung_pitch"] / 2
    while x < length:
        at = tuple(a[k] + u[k] * x for k in range(3))
        wide = widths[0] + (widths[1] - widths[0]) * x / length
        _box(vertices, faces, tuple(at[k] - v[k] * (depth / 2 - p["rung_thick"] / 2) for k in range(3)), axes, (p["rung"], wide, p["rung_thick"]))
        x += p["rung_pitch"]


def reducer_mesh(a: P3, b: P3, widths: Tuple[float, float], depth: float, p: Dict[str, float], kind: str = "escalera") -> Dict[str, list]:
    """A central reducer from a (width `widths[0]`) to b (`widths[1]`): the rails lean in, with the rungs (ladder) or the floor (perforated and solid) as wide as the taper; a wire tray steps down."""
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    if kind == "alambre":
        return _stepped(a, b, tuple((a[k] + b[k]) / 2 for k in range(3)), widths, depth, p)
    axes = _frame(a, b)
    for side in (-1, 1):
        _rail(vertices, faces, a, b, axes, side, widths[0], depth, p, widths[1])
    if kind == "escalera":
        _taper_rungs(vertices, faces, a, b, axes, widths, depth, p)
    else:
        u, n, v = axes
        length = math.dist(a, b)
        _quad(vertices, faces, [tuple(a[k] + u[k] * x + n[k] * y - v[k] * depth / 2 for k in range(3)) for x, y in ((0, -widths[0] / 2), (length, -widths[1] / 2), (length, widths[1] / 2), (0, widths[0] / 2))])
    return {"vertices": vertices, "faces": faces}


def _stepped(a: P3, b: P3, mid: P3, widths: Tuple[float, float], depth: float, p: Dict[str, float]) -> Dict[str, list]:
    """A wire-mesh reducer: the wide half, then the narrow half."""
    big = tray_mesh([a, mid], widths[0], depth, p, "alambre")
    small = tray_mesh([mid, b], widths[1], depth, p, "alambre")
    shift = len(big["vertices"])
    return {"vertices": big["vertices"] + small["vertices"], "faces": big["faces"] + [[i + shift for i in f] for f in small["faces"]]}


def solid(ident: str, tag: str, run: Sequence[P3], layer: str, width: float, depth: float, p: Dict[str, float], radius: float, vertical_radius: float,
          level: str = "") -> Dict[str, object]:
    """One tray as a solid of the 3D scene (the same plain data `scene3d` shows and writes: id, tag, kind, discipline, level, layer and the mesh), in the units of its arguments."""
    return {"id": ident, "tag": tag, "kind": "tray", "discipline": "electricidad", "level": level, "layer": layer,
            "mesh": ladder_mesh(path3d(run, radius, vertical_radius), width, depth, p)}
