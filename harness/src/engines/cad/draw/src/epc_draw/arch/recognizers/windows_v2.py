"""Windows drawn inside a continuous wall. A window's frame often continues both faces of the wall across the opening, so the wall is not interrupted there and no gap is left for the gap
reader to find: what shows it is thin lines between the two faces (the panes), running along the wall over the span of the window. Two or more such lines with the same span, and a span of
a window's width, are a window; like the windows of a gap, they are looked for only in walls that face outside."""
import math
from typing import Callable, Dict, List, Tuple

from epc_draw.arch.geometry import angle_gap, axis_of, seg_angle
from epc_draw.arch.model import Line, Opening, Wall
from epc_draw.arch.recognizers import Context

Span = Tuple[float, float, float]                      # start, end, offset of one line along and across the wall


def _panes(lines: List[Line], w: Wall, T: float, ctx: Context) -> List[Span]:
    """The thin strokes parallel to a wall that lie between its faces, as (t0, t1, offset from its axis)."""
    theta = seg_angle(w.a, w.b)
    ax = axis_of(theta)
    wt0, wt1 = sorted((ax.t(w.a), ax.t(w.b)))
    axis_o = ax.o(w.a)
    tol, inner = ctx.params["walls"]["angle_tolerance_deg"] * 2, ctx.params["windows"]["pane_band"]
    out = []
    for l in lines:
        if l.width > 0.3 * T or angle_gap(seg_angle(l.a, l.b), theta) > tol:
            continue
        t0, t1 = sorted((ax.t(l.a), ax.t(l.b)))
        o = ax.o(((l.a[0] + l.b[0]) / 2, (l.a[1] + l.b[1]) / 2)) - axis_o
        if abs(o) <= inner * T and t0 >= wt0 - T / 2 and t1 <= wt1 + T / 2:
            out.append((t0, t1, o))
    return out


def _groups(panes: List[Span], T: float, bounds: Tuple[float, float]) -> Dict[Tuple[int, int], List[Span]]:
    """Panes that begin and end at the same places (within half a wall thickness) and are of the width of an opening."""
    groups: Dict[Tuple[int, int], List[Span]] = {}
    for t0, t1, o in panes:
        if bounds[0] <= t1 - t0 <= bounds[1]:
            groups.setdefault((round(t0 / (T / 2)), round(t1 / (T / 2))), []).append((t0, t1, o))
    return groups


def _distinct(spans: List[Span], T: float) -> int:
    offsets: List[float] = []
    for _, _, o in spans:
        if not any(abs(o - p) < T / 8 for p in offsets):
            offsets.append(o)
    return len(offsets)


def windows_in_walls(lines: List[Line], walls: List[Wall], T: float, ctx: Context, outside: Callable[[Tuple[float, float], float], bool]) -> List[Opening]:
    cfg = ctx.params["windows"]
    lo, hi = ctx.params["relative"]["opening_width_in_walls"] if not ctx.scale.known else (0, 0)
    bounds = ctx.scale.opening_width if ctx.scale.known else (lo * T, hi * T)
    found: List[Opening] = []
    for w in walls:
        theta = seg_angle(w.a, w.b)
        ax = axis_of(theta)
        axis_o = ax.o(w.a)
        length = math.hypot(w.b[0] - w.a[0], w.b[1] - w.a[1])
        for spans in _groups(_panes(lines, w, T, ctx), T, bounds).values():
            if _distinct(spans, T) < cfg["min_lines"]:
                continue
            t0, t1 = sum(s[0] for s in spans) / len(spans), sum(s[1] for s in spans) / len(spans)
            if t1 - t0 > cfg["pane_max_share"] * length:                    # lines along the whole wall are its hatching, not a window in it
                continue
            at = (ax.ux * (t0 + t1) / 2 + ax.nx * axis_o, ax.uy * (t0 + t1) / 2 + ax.ny * axis_o)
            if outside(at, theta):
                found.append(Opening("", "window", at, t1 - t0, theta, w.id, ctx.params["confidence"]["window_lines"], f"{len(spans)} panes inside the wall"))
    return found
