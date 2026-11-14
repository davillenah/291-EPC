"""Doors, windows and plain openings. A wall that stops and starts again leaves a gap; what lies in the gap says what it is: the swing of a leaf is a door, thin lines across it are a window,
nothing is just an opening. A door whose arc is drawn without a gap in the wall, and the blocks the drawing names as doors or windows, are found too."""
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from epc_arch.geometry import angle_gap, arc_point, arc_span, axis_of, dist_point_line, dist_point_segment, seg_angle, seg_length, segment_distance
from epc_arch.model import Arc, Block, Line, Opening, Primitives, Wall
from epc_arch.recognizers import Context
from epc_arch.recognizers.swings import doors_at_wall_ends
from epc_arch.recognizers.windows_v2 import windows_in_walls

Pt = Tuple[float, float]


@dataclass(frozen=True)
class Gap:
    at: Pt
    width: float
    theta: float
    offset: float
    t0: float
    t1: float
    wall: str
    at_end: bool = False                  # between the end of a wall and a wall across it: only a door or a window there is taken, not an empty gap


def _wall_axis(w: Wall):
    theta = seg_angle(w.a, w.b)
    ax = axis_of(theta)
    t0, t1 = sorted((ax.t(w.a), ax.t(w.b)))
    return theta, ax, ax.o(w.a), t0, t1


def _collinear_groups(walls: List[Wall], T: float, tol: float) -> List[List[Wall]]:
    groups: List[List[Wall]] = []
    for w in walls:
        theta, _, off, _, _ = _wall_axis(w)
        for g in groups:
            t2, _, o2, _, _ = _wall_axis(g[0])
            if angle_gap(theta, t2) <= tol and abs(off - o2) <= 0.5 * T:
                g.append(w)
                break
        else:
            groups.append([w])
    return groups


def opening_range(T: float, ctx: Context) -> Tuple[float, float]:
    if ctx.scale.known:
        return ctx.scale.opening_width
    lo, hi = ctx.params["relative"]["opening_width_in_walls"]
    return lo * T, hi * T


def door_range(T: float, ctx: Context) -> Tuple[float, float]:
    if ctx.scale.known:
        return ctx.scale.door_radius
    lo, hi = ctx.params["relative"]["door_radius_in_walls"]
    return lo * T, hi * T


def _meets_a_cross_wall(p: Pt, theta: float, walls: List[Wall], ctx: Context) -> bool:
    """Does a wall end at this point on the face of a wall that crosses its line (a T), instead of ending free?"""
    reach = ctx.params["walls"]["touch_factor"]
    return any(angle_gap(seg_angle(q.a, q.b), theta) >= 60.0 and dist_point_segment(p, q.a, q.b) <= q.thickness * (0.5 + 0.3 * reach) for q in walls)


def _is_a_passage(a: Pt, b: Pt, theta: float, walls: List[Wall], T: float, ctx: Context) -> bool:
    """A line of wall that stops and starts again with each end on a cross wall is not an opening in a wall but the space between two parallel walls (a corridor that cuts the line): a door's
    jambs are free ends."""
    return _meets_a_cross_wall(a, theta, walls, ctx) and _meets_a_cross_wall(b, theta, walls, ctx)


def _is_an_opening(a: Pt, b: Pt, widths: Tuple[float, float], theta: float, walls: List[Wall], T: float, ctx: Context) -> bool:
    """Is the stretch a-b, where a line of wall stops and starts again, the width of an opening and not a passage between walls?"""
    return widths[0] <= math.hypot(b[0] - a[0], b[1] - a[1]) <= widths[1] and not _is_a_passage(a, b, theta, walls, T, ctx)


def _gap_between(span, nxt, axis, walls, T, ctx, lines):
    """The gap between a stretch of wall `span` and the next one `nxt` on the same axis: an opening, a window at the end of a corridor (only with `lines`) or None."""
    (theta, ax, off), (_, e0, wid), (s1, _, _) = axis, span, nxt
    lo, hi = opening_range(T, ctx)
    a, b = ax.at(e0, off), ax.at(s1, off)
    if _is_an_opening(a, b, (lo, hi), theta, walls, T, ctx):
        return Gap(ax.at((e0 + s1) / 2, off), s1 - e0, theta, off, e0, s1, wid)
    if not (lines and lo <= s1 - e0 <= hi and _is_a_passage(a, b, theta, walls, T, ctx)):
        return None
    cand = Gap(ax.at((e0 + s1) / 2, off), s1 - e0, theta, off, e0, s1, wid, at_end=True)
    return cand if _window_evidence(cand, lines, T, ctx) >= ctx.params["windows"]["min_lines"] and on_the_outside(cand, walls, T) else None


def find_gaps(walls: List[Wall], T: float, ctx: Context, lines: Sequence[Line] = ()) -> List[Gap]:
    """Where a line of wall stops and starts again a door's width further on. With the `lines` of the drawing, the end of a corridor that is closed by a window is found too: the stretch
    between two parallel walls looks like a passage, but the panes drawn across it and the outside beyond make it a window (`at_end`: a window there, never an empty opening)."""
    out: List[Gap] = []
    for g in _collinear_groups(walls, T, ctx.params["walls"]["angle_tolerance_deg"]):
        theta, ax, off, _, _ = _wall_axis(g[0])
        spans = sorted(((_wall_axis(w)[3], _wall_axis(w)[4], w.id) for w in g))
        found = (_gap_between(span, nxt, (theta, ax, off), walls, T, ctx, lines) for span, nxt in zip(spans, spans[1:]))
        out.extend(filter(None, found))
    return out + end_gaps(walls, T, ctx)


def end_gaps(walls: List[Wall], T: float, ctx: Context) -> List[Gap]:
    """Where a wall stops a door's width short of a wall that crosses its line: the door or window is between the end of the one and the face of the other (at a corner or a T, which is where
    most doors of a plan are)."""
    lo, hi = opening_range(T, ctx)
    tol = ctx.params["walls"]["angle_tolerance_deg"]
    out: List[Gap] = []
    for w in walls:
        theta, ax, off, t0, t1 = _wall_axis(w)
        for t_end, sign in ((t1, 1.0), (t0, -1.0)):
            nearest: Optional[float] = None
            goes_on = False
            for q in walls:
                if q is w:
                    continue
                qtheta, qax, qoff, q0, q1 = _wall_axis(q)
                gap_angle = angle_gap(qtheta, theta)
                if gap_angle <= tol:
                    ahead = q0 - t_end if sign > 0 else t_end - q1
                    if abs(qoff - off) <= 0.5 * T and -0.5 * T <= ahead < hi:                  # the line of wall goes on: that gap is found as an ordinary one
                        goes_on = True
                        break
                    continue
                if gap_angle < 60.0:
                    continue
                den = ax.ux * qax.nx + ax.uy * qax.ny                                       # how fast the position across the other wall changes along this one
                if abs(den) < 1e-9:
                    continue
                t_hit = t_end + (qoff - qax.o(ax.at(t_end, off))) / den                    # where this wall's axis meets the other wall's axis
                if not q0 - 0.5 * T <= qax.t(ax.at(t_hit, off)) <= q1 + 0.5 * T:
                    continue
                face = (t_hit - t_end) * sign - q.thickness / 2                             # from this wall's end to the near face of the other
                if face > -0.25 * T and (nearest is None or face < nearest):
                    nearest = face
            if goes_on or nearest is None or not lo <= nearest <= hi:
                continue
            width = nearest
            a, b = (t_end, t_end + width) if sign > 0 else (t_end - width, t_end)
            out.append(Gap(ax.at((a + b) / 2, off), width, theta, off, a, b, w.id, True))
    return out


class LineIndex:
    """The end points of the strokes by place, to ask which strokes end near a point without reading them all."""

    def __init__(self, lines: List[Line], cell: float):
        self.cell = max(cell, 1e-6)
        self._grid: Dict[Tuple[int, int], List[Line]] = {}
        for l in lines:
            for p in (l.a, l.b):
                self._grid.setdefault((int(p[0] // self.cell), int(p[1] // self.cell)), []).append(l)

    def near(self, p: Pt, reach: float) -> List[Line]:
        span = int(reach // self.cell) + 1
        cx, cy = int(p[0] // self.cell), int(p[1] // self.cell)
        return [l for dx in range(-span, span + 1) for dy in range(-span, span + 1) for l in self._grid.get((cx + dx, cy + dy), [])]


def _ends(a: Arc) -> Tuple[Pt, Pt]:
    return arc_point(a.c, a.r, a.start), arc_point(a.c, a.r, a.end)


def _leaf(a: Arc, index: LineIndex, cfg: dict) -> Optional[Pt]:
    """The end of the arc where the leaf is drawn: a stroke from the hinge to that end, as long as the radius."""
    tol = cfg["leaf_match"] * a.r
    for end in _ends(a):
        for l in index.near(a.c, tol):
            for p, q in ((l.a, l.b), (l.b, l.a)):
                if math.hypot(p[0] - a.c[0], p[1] - a.c[1]) <= tol and abs(seg_length(p, q) - a.r) <= 2 * tol and math.hypot(q[0] - end[0], q[1] - end[1]) <= 2 * tol:
                    return end
    return None


def _nearest_wall(p: Pt, walls: List[Wall], reach: float) -> Optional[Wall]:
    best = min(walls, key=lambda w: dist_point_segment(p, w.a, w.b), default=None)
    return best if best is not None and dist_point_segment(p, best.a, best.b) <= reach else None


def _covered(a: Pt, b: Pt, walls: List[Wall], T: float, samples: int = 8) -> float:
    """The share of the stretch a-b that lies on a wall."""
    hits = 0
    for i in range(samples):
        f = (i + 0.5) / samples
        p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        hits += any(dist_point_segment(p, w.a, w.b) <= 0.5 * w.thickness + 0.1 * T for w in walls)
    return hits / samples


def _wall_of(a: Arc, walls: List[Wall], T: float) -> Optional[Wall]:
    """The wall a swing belongs to: the nearest to its hinge. At a corner the hinge touches two walls; the door is in the one whose line the shut leaf lies along with no wall under it (along the
    other the leaf would lie on solid wall)."""
    near = [w for w in walls if dist_point_segment(a.c, w.a, w.b) <= 1.2 * T]
    if len(near) < 2:
        return _nearest_wall(a.c, walls, 1.2 * T)
    ends = _ends(a)

    def under(w: Wall) -> float:
        end = min(ends, key=lambda e: dist_point_line(e, w.a, w.b))
        return _covered(a.c, end, walls, T)

    return min(near, key=lambda w: (under(w), dist_point_segment(a.c, w.a, w.b)))


def _wall_and_closed_end(a: Arc, leaf: Optional[Pt], walls: List[Wall], T: float) -> Tuple[Optional[Wall], Pt]:
    """The wall a swing belongs to and the end of the arc where the leaf lies when shut. The open leaf is drawn to one end, so the shut one is the other, along the wall, across its gap; the wall
    is the one that runs that way through the hinge. Without a drawn leaf, the wall is the nearest to the hinge (see `_wall_of`) and the end is the one along it."""
    e0, e1 = _ends(a)
    if leaf is not None:
        shut = e1 if leaf == e0 else e0
        theta = seg_angle(a.c, shut)
        along = [w for w in walls if angle_gap(seg_angle(w.a, w.b), theta) <= 20.0 and dist_point_line(a.c, w.a, w.b) <= T]
        if along:
            return min(along, key=lambda w: dist_point_segment(shut, w.a, w.b)), shut
    wall = _wall_of(a, walls, T)
    return wall, min((e0, e1), key=lambda e: dist_point_line(e, wall.a, wall.b) if wall else 0.0)


def _door_from_arc(a: Arc, walls: List[Wall], index: LineIndex, T: float, ctx: Context) -> Opening:
    cfg, conf = ctx.params["doors"], ctx.params["confidence"]
    e0, e1 = _ends(a)
    leaf = _leaf(a, index, cfg)
    wall, on_wall = _wall_and_closed_end(a, leaf, walls, T)
    at = ((a.c[0] + on_wall[0]) / 2, (a.c[1] + on_wall[1]) / 2)
    angle = seg_angle(wall.a, wall.b) if wall else seg_angle(a.c, on_wall)
    reason = "arc and leaf" if leaf else "arc"
    in_room = e1 if on_wall == e0 else e0                                                           # the free end of the open leaf: where the swing reaches into the room
    return Opening("", "door", at, a.r, angle, wall.id if wall else "", conf["door_arc_gap_leaf"] if leaf else conf["door_arc_only"], reason, hinge=a.c, swing=in_room)


def door_arcs(prims: Primitives, T: float, ctx: Context) -> List[Arc]:
    lo, hi = door_range(T, ctx)
    smin, smax = ctx.params["doors"]["arc_span_deg"]
    return [a for a in prims.arcs if smin <= arc_span(a.start, a.end) <= smax and lo <= a.r <= hi and ctx.hints.of(a.layer) != "wall"]


def _match_gap(door: Opening, gaps: List[Gap], used: set, cfg: dict) -> Optional[int]:
    best, where = None, 0.0
    for i, g in enumerate(gaps):
        near = math.hypot(g.at[0] - door.at[0], g.at[1] - door.at[1])
        if i not in used and abs(g.width - door.width) <= cfg["gap_match"] * door.width and near <= 0.6 * door.width and (best is None or near < where):
            best, where = i, near
    return best


def _window_evidence(g: Gap, lines: List[Line], T: float, ctx: Context) -> int:
    """How many distinct thin strokes cross the gap along the wall: the panes and sill of a window."""
    cfg = ctx.params["windows"]
    ax = axis_of(g.theta)
    seen: List[float] = []
    for l in lines:
        if angle_gap(seg_angle(l.a, l.b), g.theta) > ctx.params["walls"]["angle_tolerance_deg"] * 2:
            continue
        t0, t1 = sorted((ax.t(l.a), ax.t(l.b)))
        o = ax.o(((l.a[0] + l.b[0]) / 2, (l.a[1] + l.b[1]) / 2))
        covers = min(t1, g.t1) - max(t0, g.t0) >= cfg["cover"] * g.width
        if covers and abs(o - g.offset) <= cfg["offset_factor"] * T and not any(abs(o - s) < T / 8 for s in seen):
            seen.append(o)
    return len(seen)


def on_the_outside(g: Gap, walls: List[Wall], T: float) -> bool:
    """Does one side of the gap look out of the building: a line drawn across the wall from the gap reaches past all the walls without meeting another?"""
    xs = [c for w in walls for c in (w.a[0], w.b[0])]
    ys = [c for w in walls for c in (w.a[1], w.b[1])]
    reach = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) + T
    ax = axis_of(g.theta)
    for s in (1.0, -1.0):
        start = (g.at[0] + ax.nx * s * T, g.at[1] + ax.ny * s * T)
        end = (g.at[0] + ax.nx * s * reach, g.at[1] + ax.ny * s * reach)
        if not any(segment_distance(start, end, w.a, w.b) <= 0.25 * T for w in walls):
            return True
    return False


def _opening_from_gap(g: Gap, lines: List[Line], walls: List[Wall], T: float, ctx: Context) -> Opening:
    """What lies in a gap. Windows are in the walls that face outside (every sample plan agrees): thin lines across a gap between two rooms are a sill, a sliding door or a piece of
    furniture, and the gap is a plain opening."""
    conf, cfg = ctx.params["confidence"], ctx.params["windows"]
    n = _window_evidence(g, lines, T, ctx)
    outside = on_the_outside(g, walls, T)
    if n >= cfg["min_lines"] and outside:
        return Opening("", "window", g.at, g.width, g.theta, g.wall, conf["window_lines"], f"{n} lines across the gap")
    if n == 1 and outside:
        return Opening("", "window", g.at, g.width, g.theta, g.wall, conf["window_one_line"], "1 line across the gap")
    return Opening("", "opening", g.at, g.width, g.theta, g.wall, conf["opening_gap"], "gap in the wall" if not n else f"gap between rooms ({n} lines across)")


def _from_gap_with_door(door: Opening, g: Gap) -> Opening:
    conf_wall = g.wall or door.wall
    return Opening("", "door", g.at, g.width, g.theta, conf_wall, min(0.95, door.confidence + 0.1), door.reason + " in a gap", hinge=door.hinge, swing=door.swing)


def _from_block(b: Block, kind: str, walls: List[Wall], T: float, ctx: Context) -> Opening:
    conf = ctx.params["confidence"]
    lo, hi = door_range(T, ctx) if kind == "door" else opening_range(T, ctx)
    wall = _nearest_wall(b.at, walls, 1.5 * T)
    width = b.width if lo <= b.width <= hi * 2 else lo * (1.0 if kind == "door" else 1.5)
    return Opening("", kind, b.at, width, seg_angle(wall.a, wall.b) if wall else b.rotation % 180.0, wall.id if wall else "", conf["door_block"], f"block {b.name}")


def _dedupe(found: List[Opening], T: float, ctx: Context) -> List[Opening]:
    """Two findings at the same place are one: the more confident stays, a door or window wins over a plain opening."""
    reach = ctx.params["dedupe"]["opening_distance_factor"]
    rank = {"door": 2, "window": 2, "opening": 1}
    kept: List[Opening] = []
    for o in sorted(found, key=lambda o: (-rank[o.kind], -o.confidence)):
        if not any(math.hypot(o.at[0] - k.at[0], o.at[1] - k.at[1]) <= reach * max(o.width, k.width) for k in kept):
            kept.append(o)
    return kept


def _number(found: List[Opening], T: float) -> List[Opening]:
    prefix = {"door": "d", "window": "v", "opening": "o"}
    count = {k: 0 for k in prefix}
    out = []
    for o in sorted(found, key=lambda o: (round(o.at[1] / T), o.at[0])):
        count[o.kind] += 1
        out.append(Opening(f"{prefix[o.kind]}{count[o.kind]}", o.kind, o.at, o.width, o.angle, o.wall, o.confidence, o.reason, o.hinge, o.swing))
    return out


def _alike(doors: List[Opening], T: float, ctx: Context) -> List[Opening]:
    """The doors of one plan are of a few standard widths (0.70 to 1.00 m): a swing far wider or narrower than the usual one of the plan is a curve of furniture, a planter or a car.
    With few doors, the usual width is the one the sample plans agree on, a few wall thicknesses."""
    if not doors:
        return doors
    cfg = ctx.params["swings"]
    if len(doors) >= 3:
        lo, hi = cfg["width_spread"]
        usual = sorted(d.width for d in doors)[len(doors) // 2]
    else:                                                                     # few doors: a looser band around the usual width (a thin partition makes a door many thicknesses wide)
        lo, hi = cfg["width_spread_few"]
        usual = cfg["usual_width_in_walls"] * T
    return [d for d in doors if lo * usual <= d.width <= hi * usual]


def _faces_outside(walls: List[Wall], gaps: List[Gap], T: float):
    """The test a window inside a wall must pass: a line across the wall reaches past the building. The gaps of the walls count as shut for it (a garage gate is not the outside of the rooms behind it)."""
    shut = list(walls)
    for g in gaps:
        ax = axis_of(g.theta)
        shut.append(Wall("", (g.at[0] - ax.ux * g.width / 2, g.at[1] - ax.uy * g.width / 2), (g.at[0] + ax.ux * g.width / 2, g.at[1] + ax.uy * g.width / 2), T, 1.0, "gap"))
    return lambda at, theta: on_the_outside(Gap(at, 0.0, theta, 0.0, 0.0, 0.0, ""), shut, T)


def recognize_openings(prims: Primitives, walls: List[Wall], T: float, ctx: Context) -> List[Opening]:
    gaps = find_gaps(walls, T, ctx, prims.lines)
    index = LineIndex(prims.lines, T)
    doors = [_door_from_arc(a, walls, index, T, ctx) for a in door_arcs(prims, T, ctx)]
    used: set = set()
    found: List[Opening] = []
    for d in doors:
        i = _match_gap(d, gaps, used, ctx.params["doors"])
        if i is None:
            found.append(d)
        else:
            used.add(i)
            found.append(_from_gap_with_door(d, gaps[i]))
    if prims.ink is not None:                                                  # a picture: each door is looked for where it hinges, at a wall end; the gap it stands in is then taken
        candidates = doors_at_wall_ends(prims, walls, T, ctx)
        if prims.faint is not None:                                           # swings drawn in a pale grey: looked for again among every mark on the paper
            candidates += doors_at_wall_ends(Primitives(**{**prims.__dict__, "ink": prims.faint}), walls, T, ctx)
        for d in _alike(_dedupe(candidates, T, ctx), T, ctx):
            found.append(d)
            for i, g in enumerate(gaps):
                if i not in used and math.hypot(g.at[0] - d.at[0], g.at[1] - d.at[1]) <= 0.6 * max(g.width, d.width):
                    used.add(i)
    found += [o for i, g in enumerate(gaps) if i not in used for o in [_opening_from_gap(g, prims.lines, walls, T, ctx)] if not (g.at_end and o.kind == "opening")]
    found += [_from_block(b, kind, walls, T, ctx) for b in prims.blocks for kind in [ctx.hints.of(b.name)] if kind in ("door", "window")]
    found += windows_in_walls(prims.lines, walls, T, ctx, _faces_outside(walls, gaps, T))
    return _number(_dedupe(found, T, ctx), T)
