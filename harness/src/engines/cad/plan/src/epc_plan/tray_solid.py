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


def _miters(path: Sequence[P3]) -> List[P3]:
    """The lateral vector at each vertex of the path, scaled so that the rails of two neighbouring stretches meet at a mitre (n1 + n2) / (1 + n1.n2) and leave no wedge at a bend."""
    sides = [_frame(a, b)[1] for a, b in zip(path, path[1:]) if math.dist(a, b) > 1e-9]
    if len(sides) != len(path) - 1:
        return [sides[0] if sides else (0.0, 1.0, 0.0)] * len(path)                # a path with a repeated point: no mitre
    out = [sides[0]]
    for n1, n2 in zip(sides, sides[1:]):
        k = 1 + sum(x * y for x, y in zip(n1, n2))
        out.append(tuple((x + y) / k for x, y in zip(n1, n2)) if k > 1e-6 else n1)
    return out + [sides[-1]]


def _box(vertices: List[List[float]], faces: List[List[int]], centre: P3, axes: Tuple[P3, P3, P3], size: Tuple[float, float, float]) -> None:
    """A box with the given centre, the three unit axes and the full size along each."""
    base = len(vertices)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                vertices.append([centre[k] + axes[0][k] * sx * size[0] / 2 + axes[1][k] * sy * size[1] / 2 + axes[2][k] * sz * size[2] / 2 for k in range(3)])
    for quad in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        faces.append([base + i for i in quad])


def rail_section(depth: float, foot: float, curl: float, lip: float = 0.0, jog: float = 0.0) -> List[Tuple[float, float]]:
    """The centre line of a cold-formed rail, as (inward, height above the bottom) pairs: the bottom foot turned in (with its return `lip` up when given), the straight web, and over the top `curl` of the height
    the S fold (`jog` deep) and the rolled hook, as in the catalogue sections. With no `lip` and no `jog` it is the plain C: foot, web and a small roll."""
    if not jog:
        return [(foot, 0.0), (0.0, 0.0), (0.0, depth - curl), (curl / 3, depth - curl / 3), (curl, depth), (curl * 1.4, depth - curl / 3)]
    z = depth - curl
    hook = [(0.0, z), (jog, z + 0.27 * curl), (0.25 * jog, z + 0.5 * curl), (0.5 * jog, z + 0.78 * curl),
            (2.0 * jog, depth), (3.2 * jog, depth - 0.1 * curl), (3.6 * jog, depth - 0.3 * curl), (2.9 * jog, depth - 0.38 * curl)]
    return ([(foot, lip)] if lip else []) + [(foot, 0.0), (0.0, 0.0)] + hook


def _miter_offsets(section: Sequence[Tuple[float, float]], half: float) -> List[Tuple[float, float]]:
    """For every point of an open polyline, the vector that moves it `half` to its left (mitred between the two segments, capped so a sharp fold cannot spike)."""
    count = len(section)
    normals = []
    for (x0, y0), (x1, y1) in zip(section, section[1:]):
        length = math.hypot(x1 - x0, y1 - y0) or 1.0
        normals.append((-(y1 - y0) / length, (x1 - x0) / length))
    offsets = []
    for i in range(count):
        a = normals[max(i - 1, 0)]
        b = normals[min(i, count - 2)]
        mx, my = a[0] + b[0], a[1] + b[1]
        scale = 1.0 + a[0] * b[0] + a[1] * b[1]
        k = half / max(scale, 0.4)
        offsets.append((mx * k, my * k))
    return offsets


def rail_outline(section: Sequence[Tuple[float, float]], thick: float) -> List[Tuple[float, float]]:
    """The closed outline of a rail of thickness `thick` whose centre line is `section`: the left side forward, then the right side back."""
    off = _miter_offsets(section, thick / 2)
    left = [(x + dx, y + dy) for (x, y), (dx, dy) in zip(section, off)]
    right = [(x - dx, y - dy) for (x, y), (dx, dy) in zip(section, off)]
    return left + right[::-1]


def _sheet(vertices: List[List[float]], faces: List[List[int]], corners: Sequence[P3], direction: P3, thick: float) -> None:
    """A plate: the four `corners` and the same corners moved `thick` along the unit vector `direction`, closed by its six faces."""
    base = len(vertices)
    vertices.extend([list(c) for c in corners])
    vertices.extend([[c[k] + direction[k] * thick for k in range(3)] for c in corners])
    faces.append([base, base + 1, base + 2, base + 3])
    faces.append([base + 7, base + 6, base + 5, base + 4])
    for i in range(4):
        j = (i + 1) % 4
        faces.append([base + i, base + j, base + 4 + j, base + 4 + i])


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
        centre = tuple(a[k] + u[k] * (s0 + s1) / 2 + n[k] * lateral + v[k] * ((h0 + h1) / 2 - depth / 2) for k in range(3))
        _box(vertices, faces, centre, axes, (s1 - s0, p["rail"], h1 - h0))


def _rail_points(ends: Sequence[Tuple[P3, float]], leans: Sequence[P3], v: P3, side: int, section: Sequence[Tuple[float, float]], depth: float) -> List[List[float]]:
    """The points of the section of a rail at its two ends; `leans` are the (mitred) lateral vectors there."""
    return [[end[k] + lean[k] * (side * wide / 2 - side * inward) + v[k] * (height - depth / 2) for k in range(3)] for (end, wide), lean in zip(ends, leans) for inward, height in section]


def _rail(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], side: int, width: float, depth: float, p: Dict[str, float],
          width_b: Optional[float] = None, ns: Optional[Tuple[P3, P3]] = None) -> None:
    """A rail as a sheet swept along a..b: one quad per segment of its section, the web with its side slots; with `width_b` the rail leans from `width` at a to `width_b` at b (a taper)."""
    u, n, v = axes
    section = rail_section(depth, p["foot"], p["curl"], p.get("lip", 0.0), p.get("jog", 0.0))
    outline = rail_outline(section, p["rail"])
    base = len(vertices)
    slotted = "slot" in p and width_b is None
    vertices.extend(_rail_points(((a, width), (b, width if width_b is None else width_b)), ns or (n, n), v, side, outline, depth))
    count = len(outline)
    web = section.index((0.0, 0.0))
    skipped = {web, count - 2 - web} if slotted else set()
    for i in range(count):
        if i not in skipped:
            j = (i + 1) % count
            faces.append([base + i, base + j, base + count + j, base + count + i])
    if slotted:
        _web(vertices, faces, a, math.dist(a, b), axes, side * width / 2, depth, p)


def _side_rails(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], width: float, depth: float, p: Dict[str, float],
                ns: Optional[Tuple[P3, P3]] = None) -> None:
    """Both rails of a stretch: the cold-formed C when `p` has its sizes, a plain strip otherwise."""
    u, n, v = axes
    mid = tuple((a[k] + b[k]) / 2 for k in range(3))
    for side in (-1, 1):
        if "foot" in p:
            _rail(vertices, faces, a, b, axes, side, width, depth, p, ns=ns)
            continue
        off = side * (width / 2 + p["rail"] / 2)
        _box(vertices, faces, tuple(mid[k] + n[k] * off for k in range(3)), axes, (math.dist(a, b), p["rail"], depth))


def cover_thickness(p: Dict[str, float], width: float) -> float:
    """The thickness of a cover: `p["cover"]`, or `p["cover_wide"]` from the width `p["cover_wide_from"]` up (the thicker sheet of the wide covers)."""
    if "cover_wide" in p and width >= p.get("cover_wide_from", math.inf) - 1e-9:
        return p["cover_wide"]
    return p["cover"]


def _lid(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], width: float, depth: float, p: Dict[str, float],
         ns: Optional[Tuple[P3, P3]] = None) -> None:
    """The cover of a stretch: a flat sheet `p["cover"]` over the top of the rails (with `ns`, the mitred lateral vectors at its two ends)."""
    n, v = axes[1], axes[2]
    leans = ns or (n, n)
    t = cover_thickness(p, width)
    corners = [tuple(e[k] + lean[k] * sy * (width / 2 + p["rail"]) + v[k] * (depth / 2 + t) for k in range(3)) for e, sy, lean in ((a, -1, leans[0]), (b, -1, leans[1]), (b, 1, leans[1]), (a, 1, leans[0]))]
    _sheet(vertices, faces, corners, tuple(-x for x in v), t)


def cover_mesh(path: Sequence[P3], width: float, depth: float, p: Dict[str, float]) -> Dict[str, list]:
    """The cover alone (a flat sheet over the rails, as `_lid` draws it) along `path`: for the covers of straights and fittings; `p` needs `rail` and `cover`."""
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    turns = _miters(path)
    for i, (a, b) in enumerate(zip(path, path[1:])):
        if math.dist(a, b) > 1e-9:
            _lid(vertices, faces, a, b, _frame(a, b), width, depth, p, (turns[i], turns[i + 1]))
    return {"vertices": vertices, "faces": faces}


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
    turns = _miters(path)
    for i, (a, b) in enumerate(zip(path, path[1:])):
        length = math.dist(a, b)
        if length < 1e-9:
            continue
        axes = _frame(a, b)
        u, n, v = axes
        _side_rails(vertices, faces, a, b, axes, width, depth, p, (turns[i], turns[i + 1]))
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
        _sheet(vertices, faces, [tuple(a[k] + u[k] * x + n[k] * y - v[k] * depth / 2 for k in range(3)) for x, y in ((s0, y0), (s1, y0), (s1, y1), (s0, y1))], tuple(-x for x in v), p["rail"])


def _tray_floor(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], width: float, depth: float, p: Dict[str, float], kind: str) -> None:
    """The floor of a perforated or solid-bottom tray: sheet with round holes when the sizes of the holes are given, bands of slots otherwise."""
    if kind == "perforada" and "hole" in p:
        _perforated(vertices, faces, a, b, axes, width, depth, p)
    else:
        _floor(vertices, faces, a, b, axes, width, depth, p, kind == "perforada")


def _hole_cell(vertices: List[List[float]], faces: List[List[int]], at: P3, axes: Tuple[P3, P3, P3], size: Tuple[float, float], diameter: float, thick: float = 0.0) -> None:
    """One square cell of the perforated floor: the sheet around a round hole (a hexagon of the given diameter), `thick` deep with the wall of the hole. `at` is the centre of the cell, `size` its length and width."""
    u, n, v = axes[0], axes[1], axes[2]
    half_u, half_n, r = size[0] / 2, size[1] / 2, diameter / 2
    outer = [(-half_u, -half_n), (0.0, -half_n), (half_u, -half_n), (half_u, half_n), (0.0, half_n), (-half_u, half_n)]
    inner = [(r * math.cos(math.pi / 3 * k + math.pi / 6), r * math.sin(math.pi / 3 * k + math.pi / 6)) for k in range(6)]
    inner = [min(inner, key=lambda q, o=o: (q[0] - o[0] / 2) ** 2 + (q[1] - o[1] / 2) ** 2) for o in outer]
    drop = tuple(-x * thick for x in v)
    point = lambda x, y, low: tuple(at[j] + u[j] * x + n[j] * y + (drop[j] if low else 0.0) for j in range(3))    # noqa: E731
    for k in range(6):
        k2 = (k + 1) % 6
        _quad(vertices, faces, [point(*outer[k], False), point(*outer[k2], False), point(*inner[k2], False), point(*inner[k], False)])
        if thick:
            _quad(vertices, faces, [point(*inner[k], True), point(*inner[k2], True), point(*outer[k2], True), point(*outer[k], True)])
            _quad(vertices, faces, [point(*inner[k], False), point(*inner[k2], False), point(*inner[k2], True), point(*inner[k], True)])


def _perforated(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], width: float, depth: float, p: Dict[str, float]) -> None:
    """The floor of a perforated tray: a solid sheet with small round holes in a grid (`hole_pitch` apart, `hole` across), a solid margin along each rail and a solid strip at the end."""
    u, n, v = axes
    length, pitch = math.dist(a, b), p["hole_pitch"]
    cols, rows = int((width - 2 * p["floor_margin"]) / pitch + 1e-9), int(length / pitch + 1e-9)
    side = (width - cols * pitch) / 2                                    # the margin and what is left of the width after the columns
    floor = tuple(a[k] - v[k] * depth / 2 for k in range(3))
    sheet = lambda x0, x1, y0, y1: _sheet(vertices, faces, [tuple(floor[k] + u[k] * x + n[k] * y for k in range(3)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))], tuple(-x for x in v), p["rail"])    # noqa: E731
    sheet(0, length, -width / 2, -width / 2 + side)
    sheet(0, length, width / 2 - side, width / 2)
    if rows * pitch < length - 1e-9:
        sheet(rows * pitch, length, -width / 2 + side, width / 2 - side)
    for i in range(rows):
        for j in range(cols):
            centre = tuple(floor[k] + u[k] * (i + 0.5) * pitch + n[k] * (-width / 2 + side + (j + 0.5) * pitch) for k in range(3))
            _hole_cell(vertices, faces, centre, axes, (pitch, pitch), p["hole"], p["rail"])


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


def _channel(vertices: List[List[float]], faces: List[List[int]], a: P3, b: P3, axes: Tuple[P3, P3, P3], width: float, depth: float, thick: float = 0.002) -> None:
    """A U channel: the floor and the two walls, each a plate `thick` deep towards the outside, with no return lip."""
    n, v = axes[1], axes[2]
    walls = (((-width / 2, depth / 2), (-width / 2, -depth / 2), tuple(-x for x in n)), ((-width / 2, -depth / 2), (width / 2, -depth / 2), tuple(-x for x in v)),
             ((width / 2, -depth / 2), (width / 2, depth / 2), n))
    for (y0, z0), (y1, z1), out in walls:
        _sheet(vertices, faces, [tuple(e[k] + n[k] * y + v[k] * z for k in range(3)) for e, y, z in ((a, y0, z0), (b, y0, z0), (b, y1, z1), (a, y1, z1))], out, thick)


def tray_mesh(path: Sequence[P3], width: float, depth: float, p: Dict[str, float], kind: str = "escalera") -> Dict[str, list]:
    """The mesh of a tray of the given kind (`escalera`, `perforada`, `ciega`, `alambre`, `canal`) along `path`: the ladder, or the same rails with a floor (slotted for `perforada`), or a wire mesh."""
    if kind == "escalera":
        return ladder_mesh(path, width, depth, p)
    if kind not in ("perforada", "ciega", "alambre", "canal"):
        raise PlanError("err_tray_kind", kind=kind, kinds=", ".join(tray_draw.KINDS))
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    turns = _miters(path)
    for i, (a, b) in enumerate(zip(path, path[1:])):
        if math.dist(a, b) < 1e-9:
            continue
        axes = _frame(a, b)
        if kind == "alambre":
            _wire(vertices, faces, a, b, axes, width, depth, p)
            continue
        if kind == "canal":
            _channel(vertices, faces, a, b, axes, width, depth, p.get("rail", 0.002))
            continue
        _side_rails(vertices, faces, a, b, axes, width, depth, p, (turns[i], turns[i + 1]))
        _tray_floor(vertices, faces, a, b, axes, width, depth, p, kind)
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
        _sheet(vertices, faces, [tuple(a[k] + u[k] * x + n[k] * y - v[k] * depth / 2 for k in range(3)) for x, y in ((0, -widths[0] / 2), (length, -widths[1] / 2), (length, widths[1] / 2), (0, widths[0] / 2))], tuple(-x for x in v), p["rail"])
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
