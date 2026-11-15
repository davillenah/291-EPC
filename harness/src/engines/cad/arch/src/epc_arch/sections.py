"""Elevations and sections of a floor, derived from its plan and the heights the person gives (ADR-0032, decisions 3 and 4): a plan does not say how high a wall, a sill or a door head is,
and none is guessed. A view is a list of rectangles, lines and texts in metres (`u` to the right, `z` up, 0 at the finished floor of the level), drawn on a sheet at a scale like the plan.

    heights = {"wall_height_m": 2.8, "door_head_m": 2.05, "window_sill_m": 0.9, "window_head_m": 2.1, "slab_m": 0.2, "elevation_m": 0.0}

`elevation(arch, "S", heights)` is the building seen from the south (also N, E, W): the walls in sight, the doors and windows of the walls that face that side, the ground and the slab above.
`section(arch, "x", 12.0, "E", heights)` cuts the floor with the vertical plane x = 12 m (or "y") and looks east (E/W for an x plane, N/S for a y plane): the walls and slabs the plane cuts
are solid, with the door or window the plane passes through left open; the walls beyond are seen with their doors and windows; each room cut is named.
Coordinates are those of the plan in metres (`box_m`: x to the right, y down from the top left). `stack` puts the views of several floors one above the other by their `elevation_m`.

Limits: walls along the two directions of the plan only (others are left out, with a warning); one height per floor; the roof is the slab; stairs and furniture are not drawn."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from epc_arch.model import ArchError, Architecture, Opening, Wall

HEIGHTS = ("wall_height_m", "door_head_m", "window_sill_m", "window_head_m", "slab_m", "elevation_m")
SIDES = ("N", "S", "E", "W")
GROUND_PAST = 1.0                          # metres the ground line runs past the building on each side
Span = Tuple[float, float]


@dataclass(frozen=True)
class Rect:
    role: str                              # cut (what the plane cuts: solid), seen (beyond the plane), door, window, glass
    u0: float
    z0: float
    u1: float
    z1: float


@dataclass(frozen=True)
class Segment:
    role: str                              # ground, level
    u0: float
    z0: float
    u1: float
    z1: float


@dataclass(frozen=True)
class Label:
    value: str
    u: float
    z: float
    role: str = "room"                     # room, level


@dataclass
class View:
    kind: str                              # elevation or section
    title: str
    items: List[object] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def box(self) -> Tuple[float, float, float, float]:
        """(u0, z0, u1, z1) of everything drawn."""
        us = [v for i in self.items for v in ((i.u0, i.u1) if not isinstance(i, Label) else (i.u,))]
        zs = [v for i in self.items for v in ((i.z0, i.z1) if not isinstance(i, Label) else (i.z,))]
        return (min(us), min(zs), max(us), max(zs)) if us else (0.0, 0.0, 0.0, 0.0)

    def of(self, role: str) -> List[object]:
        return [i for i in self.items if i.role == role]

    def as_dict(self) -> Dict[str, Any]:
        def one(i):
            if isinstance(i, Label):
                return {"type": "text", "role": i.role, "value": i.value, "u": round(i.u, 3), "z": round(i.z, 3)}
            return {"type": "rect" if isinstance(i, Rect) else "line", "role": i.role, "u0": round(i.u0, 3), "z0": round(i.z0, 3), "u1": round(i.u1, 3), "z1": round(i.z1, 3)}
        return {"schema_version": "1.0", "kind": self.kind, "title": self.title, "box": [round(v, 3) for v in self.box()], "items": [one(i) for i in self.items], "warnings": list(self.warnings)}


# ---------------------------------------------------------------- inputs
def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def heights_errors(h: Any) -> List[str]:
    """What is wrong with the heights of a floor (empty when a view can be drawn from them)."""
    if not isinstance(h, dict):
        return ["heights: an object with " + ", ".join(HEIGHTS)]
    out = [f"heights: unknown key(s) {', '.join(sorted(set(h) - set(HEIGHTS)))}"] if set(h) - set(HEIGHTS) else []
    out += [f"heights/{k}: required, in metres (no default)" for k in HEIGHTS if not _num(h.get(k))]
    if out:
        return out
    if h["wall_height_m"] <= 0 or h["slab_m"] <= 0:
        out.append("heights: wall_height_m and slab_m must be above 0")
    if not 0 < h["door_head_m"] <= h["wall_height_m"]:
        out.append("heights/door_head_m: above 0 and no higher than the wall")
    if not 0 <= h["window_sill_m"] < h["window_head_m"] <= h["wall_height_m"]:
        out.append("heights: 0 <= window_sill_m < window_head_m <= wall_height_m")
    return out


def _checked(arch: Architecture, heights: Any) -> float:
    """Metres per plan unit; an ArchError when the heights are not valid or the plan does not know its units."""
    bad = heights_errors(heights)
    if bad:
        raise ArchError("the view cannot be drawn: " + "; ".join(bad))
    if not arch.units_per_metre:
        raise ArchError("the view cannot be drawn: the plan does not say its units or scale")
    if not arch.walls:
        raise ArchError("the view cannot be drawn: the plan has no walls")
    return 1.0 / arch.units_per_metre


# ---------------------------------------------------------------- the plan in metres
@dataclass(frozen=True)
class _W:
    """A wall in metres: `along` is the axis it runs along ("x" or "y"), `pos` its place on the other axis, `a`..`b` its interval, `t` its thickness."""
    id: str
    along: str
    pos: float
    a: float
    b: float
    t: float


def _walls(arch: Architecture, k: float, warnings: List[str]) -> List[_W]:
    out, skew = [], 0
    for w in arch.walls:
        dx, dy = abs(w.b[0] - w.a[0]) * k, abs(w.b[1] - w.a[1]) * k
        if min(dx, dy) > 0.02 * max(dx, dy):
            skew += 1
            continue
        if dx >= dy:
            out.append(_W(w.id, "x", (w.a[1] + w.b[1]) / 2 * k, min(w.a[0], w.b[0]) * k, max(w.a[0], w.b[0]) * k, w.thickness * k))
        else:
            out.append(_W(w.id, "y", (w.a[0] + w.b[0]) / 2 * k, min(w.a[1], w.b[1]) * k, max(w.a[1], w.b[1]) * k, w.thickness * k))
    if skew:
        warnings.append(f"{skew} wall(s) are not along the directions of the plan: they are not drawn in this view")
    return out


def _meets(w: _W, end: float, other: _W) -> bool:
    """Does `other` (a wall across `w`) stand at that end of `w`: the corner or the T where the axis of one stops at the axis of the other?"""
    return other.along != w.along and abs(other.pos - end) <= other.t and other.a - other.t <= w.pos <= other.b + other.t


def _to_the_corner(w: _W, walls: List[_W]) -> _W:
    """A wall is stored from axis to axis; where another wall stands at its end it really reaches the far face of that wall (half its thickness more)."""
    a = w.a - max((o.t / 2 for o in walls if _meets(w, w.a, o)), default=0.0)
    b = w.b + max((o.t / 2 for o in walls if _meets(w, w.b, o)), default=0.0)
    return _W(w.id, w.along, w.pos, a, b, w.t)


def _holds(w: "_W", along: str, t: float, p: float, width: float) -> bool:
    """Does an opening at `t` along and `p` across lie on this wall (or in the gap at one of its ends)?"""
    return w.along == along and abs(w.pos - p) <= w.t and w.a - width <= t <= w.b + width


def _wall_of(o: Opening, walls: List[_W], k: float) -> Optional[_W]:
    """The wall an opening is in: the one it names, else the nearest one along its direction that it lies on."""
    along = "x" if min(o.angle % 180.0, 180.0 - o.angle % 180.0) < 45.0 else "y"
    named = [w for w in walls if w.id == o.wall and w.along == along]
    if named:
        return named[0]
    t, p = (o.at[0] * k, o.at[1] * k) if along == "x" else (o.at[1] * k, o.at[0] * k)
    near = [w for w in walls if _holds(w, along, t, p, o.width * k)]
    return min(near, key=lambda w: abs(w.pos - p)) if near else None


def _opening_spans(arch: Architecture, walls: List[_W], k: float) -> Dict[str, List[Tuple[str, float, float]]]:
    """{wall id: [(kind, start, end)]} of the doors, windows and openings of each wall, along the wall, in metres."""
    out: Dict[str, List[Tuple[str, float, float]]] = {}
    for o in arch.openings:
        w = _wall_of(o, walls, k)
        if w is None:
            continue
        t = (o.at[0] if w.along == "x" else o.at[1]) * k
        out.setdefault(w.id, []).append((o.kind, t - o.width * k / 2, t + o.width * k / 2))
    return out


def _bridged(walls: List[_W], gaps: Dict[str, List[Tuple[str, float, float]]]) -> Tuple[List[_W], Dict[str, List[Tuple[str, float, float]]]]:
    """A plan that was read stores a wall as the stretches between its doors and windows; an authored one stores it whole. Here the stretches of one line that an opening joins
    become one wall again (with the openings of all of them), so that both read the same."""
    out_walls: List[_W] = []
    out_gaps: Dict[str, List[Tuple[str, float, float]]] = {}
    for group in _lines(walls):
        holes = [g for w in group for g in gaps.get(w.id, [])]
        for run in _runs(sorted(group, key=lambda w: w.a), holes):
            first, end = run[0], max(w.b for w in run)
            out_walls.append(_W(first.id, first.along, first.pos, first.a, end, first.t))
            out_gaps[first.id] = [g for g in holes if first.a - 1e-6 <= (g[1] + g[2]) / 2 <= end + 1e-6]
    return out_walls, out_gaps


def _lines(walls: List[_W]) -> List[List[_W]]:
    """The walls by the line they stand on (same direction, same place across it)."""
    lines: Dict[Tuple[str, int], List[_W]] = {}
    for w in walls:
        key = next((k for k in lines if k[0] == w.along and abs(lines[k][0].pos - w.pos) <= w.t / 2), (w.along, len(lines)))
        lines.setdefault(key, []).append(w)
    return list(lines.values())


def _runs(group: List[_W], holes: List[Tuple[str, float, float]]) -> List[List[_W]]:
    """The stretches of one line, in order, split where no opening fills the space between one and the next."""
    runs: List[List[_W]] = [[group[0]]]
    for w in group[1:]:
        end = max(x.b for x in runs[-1])
        joined = w.a <= end + 1e-6 or any(g[1] <= end + 0.05 and g[2] >= w.a - 0.05 for g in holes)
        if joined:
            runs[-1].append(w)
        else:
            runs.append([w])
    return runs


def _minus(spans: List[Span], cover: List[Span]) -> List[Span]:
    """`spans` without what `cover` hides."""
    out = list(spans)
    for c0, c1 in cover:
        nxt: List[Span] = []
        for a, b in out:
            if c1 <= a or c0 >= b:
                nxt.append((a, b))
                continue
            if a < c0:
                nxt.append((a, c0))
            if c1 < b:
                nxt.append((c1, b))
        out = nxt
    return [(a, b) for a, b in out if b - a > 1e-6]


def _plan_in_metres(arch: Architecture, k: float, warnings: List[str]):
    """The walls (whole, from corner to corner) and the openings of each, in metres."""
    walls = _walls(arch, k, warnings)
    walls, gaps = _bridged(walls, _opening_spans(arch, walls, k))
    return [_to_the_corner(w, walls) for w in walls], gaps


def _opening_rects(kind: str, u0: float, u1: float, h: Dict[str, float]) -> List[Rect]:
    """A door, a window or a plain opening seen from the front."""
    if kind == "window":
        mid = (u0 + u1) / 2
        return [Rect("window", u0, h["window_sill_m"], u1, h["window_head_m"]), Rect("glass", u0, h["window_sill_m"], mid, h["window_head_m"])]
    return [Rect("door", u0, 0.0, u1, h["door_head_m"])]


# ---------------------------------------------------------------- elevation
def _axes_of(side: str) -> Tuple[str, float, float]:
    """For a view from `side`: the axis the facades run along, the sign that turns that axis into `u` (left to right for the viewer) and the sign of the direction of sight on the other axis."""
    return {"S": ("x", 1.0, -1.0), "N": ("x", -1.0, 1.0), "W": ("y", 1.0, 1.0), "E": ("y", -1.0, -1.0)}[side]


def _span_u(a: float, b: float, sign: float) -> Span:
    return (a * sign, b * sign) if sign > 0 else (b * sign, a * sign)


def _visible(walls: List[_W], along: str, sight: float, start: Optional[float]) -> List[Tuple[_W, List[Span]]]:
    """The walls that face the viewer (they run along `along`), nearest first, each with the parts of it that no nearer wall hides. `start` is where the viewer's plane is (None: outside)."""
    facing = [w for w in walls if w.along == along and (start is None or (w.pos - start) * sight > w.t / 2 + 1e-6)]
    facing.sort(key=lambda w: w.pos * sight)
    covered: List[Span] = []
    out = []
    for w in facing:
        free = _minus([(w.a, w.b)], covered)
        if free:
            out.append((w, free))
        covered.append((w.a, w.b))
    return out


def _front(view: View, walls: List[_W], gaps, along: str, sign: float, sight: float, start: Optional[float], h: Dict[str, float], clip: Optional[Span] = None) -> None:
    """What is seen in front of the viewer: each visible stretch of wall as a rectangle and the openings that lie in it."""
    for w, free in _visible(walls, along, sight, start):
        for a, b in (free if clip is None else [(max(a, clip[0]), min(b, clip[1])) for a, b in free if min(b, clip[1]) - max(a, clip[0]) > 1e-6]):
            u0, u1 = _span_u(a, b, sign)
            view.items.append(Rect("seen", u0, 0.0, u1, h["wall_height_m"]))
            for kind, g0, g1 in gaps.get(w.id, []):
                if a - 1e-6 <= (g0 + g1) / 2 <= b + 1e-6:
                    view.items += _opening_rects(kind, *_span_u(g0, g1, sign), h)


def _finish(view: View, h: Dict[str, float], name: str) -> View:
    """The ground or floor line, the slab above and the mark of the level, over the extent of what was drawn."""
    rects = [i for i in view.items if isinstance(i, Rect)]
    if not rects:
        return view
    u0, u1 = min(r.u0 for r in rects), max(r.u1 for r in rects)
    H = h["wall_height_m"]
    view.items.append(Rect("cut" if view.kind == "section" else "seen", u0, H, u1, H + h["slab_m"]))
    if view.kind == "section":
        view.items.append(Rect("cut", u0, -h["slab_m"], u1, 0.0))
    view.items.append(Segment("ground", u0 - GROUND_PAST, 0.0, u1 + GROUND_PAST, 0.0))
    view.items.append(Label(f"{name} {h['elevation_m']:+.2f}".strip(), u0 - GROUND_PAST, 0.0, "level"))
    return view


def _level_name(arch: Architecture) -> str:
    return arch.level.name if arch.level else ""


def elevation(arch: Architecture, side: str, heights: Dict[str, float]) -> View:
    """The floor seen from outside, from the north, south, east or west."""
    if side not in SIDES:
        raise ArchError("the side of an elevation is one of N, S, E, W")
    k = _checked(arch, heights)
    view = View("elevation", f"ELEVATION {side}")
    walls, gaps = _plan_in_metres(arch, k, view.warnings)
    along, sign, sight = _axes_of(side)
    _front(view, walls, gaps, along, sign, sight, None, heights)
    return _finish(view, heights, _level_name(arch))


# ---------------------------------------------------------------- section
LOOKS = {"x": {"E": (1.0, 1.0), "W": (-1.0, -1.0)}, "y": {"N": (1.0, -1.0), "S": (-1.0, 1.0)}}     # plane axis -> look -> (sign of u on the other axis, sign of the sight on the plane axis)


def _cut_pieces(kind: Optional[str], h: Dict[str, float]) -> List[Span]:
    """The heights where a wall is solid at the place the plane cuts it: all of it, above a door, or under and above a window."""
    H = h["wall_height_m"]
    if kind is None:
        return [(0.0, H)]
    if kind == "window":
        return [(0.0, h["window_sill_m"]), (h["window_head_m"], H)]
    return [(h["door_head_m"], H)]


def _cut_across(view: View, walls: List[_W], gaps, across: str, at: float, sign: float, h: Dict[str, float]) -> None:
    """The walls the plane crosses (they run along the axis the plane is on): their thickness, solid except where the plane passes through one of their openings."""
    for w in walls:
        if w.along != across or not w.a - 1e-6 <= at <= w.b + 1e-6:
            continue
        kind = next((g[0] for g in gaps.get(w.id, []) if g[1] <= at <= g[2]), None)
        u0, u1 = _span_u(w.pos - w.t / 2, w.pos + w.t / 2, sign)
        view.items += [Rect("cut", u0, z0, u1, z1) for z0, z1 in _cut_pieces(kind, h) if z1 - z0 > 1e-6]
        if kind == "window":
            view.items.append(Rect("glass", (u0 + u1) / 2, h["window_sill_m"], (u0 + u1) / 2, h["window_head_m"]))


def _in_plane(walls: List[_W], plane: str, at: float) -> List[_W]:
    """The walls that lie in the plane itself (they are cut along their length and not seen again beyond)."""
    return [w for w in walls if w.along != plane and abs(w.pos - at) <= w.t / 2 + 1e-6]


def _cut_along(view: View, inside: List[_W], gaps, sign: float, h: Dict[str, float]) -> None:
    """The walls that lie in the plane: cut along their length, with their doors and windows open."""
    for w in inside:
        holes = gaps.get(w.id, [])
        for a, b in _minus([(w.a, w.b)], [(g0, g1) for _, g0, g1 in holes]):
            view.items.append(Rect("cut", *_rect_u(a, b, sign, 0.0, h["wall_height_m"])))
        for kind, g0, g1 in holes:
            view.items += [Rect("cut", *_rect_u(g0, g1, sign, z0, z1)) for z0, z1 in _cut_pieces(kind, h) if z1 - z0 > 1e-6]


def _rect_u(a: float, b: float, sign: float, z0: float, z1: float) -> Tuple[float, float, float, float]:
    u0, u1 = _span_u(a, b, sign)
    return u0, z0, u1, z1


def _room_labels(view: View, arch: Architecture, k: float, plane: str, at: float, sign: float, h: Dict[str, float]) -> None:
    for r in arch.rooms:
        for x0, y0, x1, y1 in r.rects:
            lo, hi, a, b = (x0 * k, x1 * k, y0 * k, y1 * k) if plane == "x" else (y0 * k, y1 * k, x0 * k, x1 * k)
            if lo < at < hi and (r.name or r.code):
                u0, u1 = _span_u(a, b, sign)
                view.items.append(Label(r.name or r.code, (u0 + u1) / 2, h["wall_height_m"] / 2))
                break


def _check_plane(plane: str, at_m: Any, look: str) -> None:
    if plane not in LOOKS or look not in LOOKS[plane]:
        raise ArchError("a section is cut by an x plane seen to the E or W, or by a y plane seen to the N or S")
    if not _num(at_m):
        raise ArchError("the place of the section plane is a number of metres")


def _cuts(walls: List["_W"], plane: str, at: float) -> bool:
    """Does the plane meet a wall: one it crosses, or one that lies in it?"""
    crossed = any(w.along == plane and w.a - 1e-6 <= at <= w.b + 1e-6 for w in walls)
    return crossed or any(w.along != plane and abs(w.pos - at) <= w.t / 2 for w in walls)


def section(arch: Architecture, plane: str, at_m: float, look: str, heights: Dict[str, float]) -> View:
    """The floor cut by the vertical plane `plane` = `at_m` ("x" or "y", metres of the plan) and seen towards `look` (E or W for an x plane, N or S for a y plane)."""
    _check_plane(plane, at_m, look)
    k = _checked(arch, heights)
    view = View("section", f"SECTION {plane.upper()} = {at_m:g} m ({look})")
    walls, gaps = _plan_in_metres(arch, k, view.warnings)
    if not _cuts(walls, plane, at_m):
        raise ArchError(f"the plane {plane} = {at_m:g} m does not cut the building")
    sign, sight = LOOKS[plane][look]
    in_plane = _in_plane(walls, plane, at_m)
    _front(view, [w for w in walls if w not in in_plane], gaps, "y" if plane == "x" else "x", sign, sight, at_m, heights)
    _cut_along(view, in_plane, gaps, sign, heights)                             # what is cut is drawn after (over) what is seen
    _cut_across(view, walls, gaps, plane, at_m, sign, heights)                  # a wall that runs along the plane's axis crosses the plane
    _room_labels(view, arch, k, plane, at_m, sign, heights)
    return _finish(view, heights, _level_name(arch))


# ---------------------------------------------------------------- several floors
def _raised(item, dz: float):
    if isinstance(item, Label):
        return Label(item.value, item.u, item.z + dz, item.role)
    return type(item)(item.role, item.u0, item.z0 + dz, item.u1, item.z1 + dz)


def stack(views: List[Tuple[View, float]]) -> View:
    """The views of several floors (each with the level of its floor in metres) as one, every floor at its height. The floors must share one frame (the plans of one sheet do: `reference`)."""
    if not views:
        raise ArchError("no views to stack")
    first = views[0][0]
    out = View(first.kind, first.title)
    for view, level in sorted(views, key=lambda v: v[1]):
        if view.kind != first.kind:
            raise ArchError("only views of one kind are stacked")
        out.items += [_raised(i, level) for i in view.items]
        out.warnings += [w for w in view.warnings if w not in out.warnings]
    return out


# ---------------------------------------------------------------- the sheet
LAYERS = {"cut": "A-WALL-CUT", "seen": "A-ELEV", "door": "A-DOOR", "window": "A-WINDOW", "glass": "A-WINDOW-GLASS", "ground": "A-WALL-CUT", "level": "A-ANNO", "room": "A-ROOM-TAG"}


FILLS = {"cut": "#8C8C8C", "seen": "#FFFFFF", "door": "#FFFFFF", "window": "#FFFFFF"}


def _paper_item(i, at, D):
    """One item of a view as an item of the drawing, in paper millimetres."""
    if isinstance(i, Label):
        room = i.role == "room"
        return D.TextItem(i.value, at(i.u, i.z), "TXT_25" if room else "TXT_18", LAYERS[i.role], "middle" if room else "end")
    if isinstance(i, Segment) or abs(i.u1 - i.u0) < 1e-9 or abs(i.z1 - i.z0) < 1e-9:
        return D.Poly((at(i.u0, i.z0), at(i.u1, i.z1)), LAYERS[i.role])
    return D.Poly((at(i.u0, i.z0), at(i.u1, i.z0), at(i.u1, i.z1), at(i.u0, i.z1)), LAYERS[i.role], closed=True, fill=FILLS.get(i.role))


def view_drawing(view: View, arch: Architecture, style=None, sheet: Optional[str] = None, scale: Optional[int] = None, template=None, fields: Optional[dict] = None):
    """The view as a `Drawing` on a sheet (the layers and the typeface of the style, the IRAM title block when `template` is given), at a standard scale that fits."""
    from epc_arch import drawing as D
    style = style or D.load_style()
    name, size, free = D._sheet_of(style, sheet, template)
    d = D.Drawing(name, size, 0)
    u0, z0, u1, z1 = view.box()
    d.scale, changed = D._scale_for(((u1 - u0) * 1000.0, (z1 - z0) * 1000.0), (free[2] - free[0], free[3] - free[1]), scale, style)
    if changed:
        d.warnings.append(f"the view does not fit sheet {d.sheet} at the requested scale: drawn at 1:{d.scale}")
    k = 1000.0 / d.scale
    cx, cy = (free[0] + free[2]) / 2, (free[1] + free[3]) / 2
    at = lambda u, z: (cx + (u - (u0 + u1) / 2) * k, cy - (z - (z0 + z1) / 2) * k)        # noqa: E731
    d.items += [_paper_item(i, at, D) for i in view.items]
    d.title = view.title
    d.document = arch.source
    d.warnings += view.warnings
    D._frame_the_sheet(d, arch, style, free, template, fields)
    return d


def view_dxf(view: View, arch: Architecture, sheet: str = "A1", scale: Optional[int] = None, fields: Optional[Dict[str, str]] = None) -> str:
    """The view on an IRAM sheet, as DXF text (real metres, like the plan)."""
    from epc_arch.drawing import load_style
    from epc_arch.export.export_dxf import to_dxf
    from epc_arch.sheets import iram_template
    style = load_style()
    return to_dxf(view_drawing(view, arch, style, sheet, scale, iram_template(sheet), dict({"denominacion": view.title}, **(fields or {}))), style)
