"""Automatic exterior dimensions of a set of straight walls with openings.

Rules (a plain description of the behaviour, written for this engine): walls that are not longer than the minimum or not parallel to an axis are left out with a
note. The outer face of each wall gives the bounds of the building. A total dimension is made along the south edge (X) and the west edge (Y). Along each of the
four edges one chain is made from stop to stop: the ends of the walls on that edge, the edges of their openings and the centre of every wall that arrives at
the edge. The chain row is at `gap` from the outer face and the total row one `step` farther. A dimension whose two points already exist (in either order) is
not made again. Dimensions are `{id, kind, edge, orientation, p1, p2, line, value}`: `p1` and `p2` are on the outer face, `line` is the coordinate of the
dimension line (a Y for horizontal dimensions, an X for vertical ones).
"""
import math

from epc_dims import inputs
from epc_dims.messages import text


def _note(code, **params):
    return {"code": code, **text(code, **params)}


def _segment(w, tol, min_wall):
    """`(segment or None, note or None)`: the wall as `{id, o, c, lo, hi, mid, t, dir, a_axis}` when it is along X (`o` 'h') or Y ('v')."""
    dx, dy = w["b"][0] - w["a"][0], w["b"][1] - w["a"][1]
    if math.hypot(dx, dy) <= min_wall:
        return None, _note("note_wall_skipped_short", id=w["id"], min=min_wall)
    if abs(dy) <= tol:
        o, axis, cross, along = "h", 0, 1, dx
    elif abs(dx) <= tol:
        o, axis, cross, along = "v", 1, 0, dy
    else:
        return None, _note("note_wall_skipped_oblique", id=w["id"])
    unit = 1 if along > 0 else -1
    left = (-dy, dx)[cross] / math.hypot(dx, dy)                  # component of the left normal across the wall
    face = w["a"][cross] + (left if w["ext_side"] == "left" else -left) * w["t"] / 2
    ends = sorted((w["a"][axis], w["b"][axis]))
    return {"id": w["id"], "o": o, "c": face, "lo": ends[0], "hi": ends[1], "mid": w["a"][cross], "t": w["t"], "dir": unit, "a_axis": w["a"][axis]}, None


def _segments(items, tol, min_wall):
    segments, issues = [], []
    for w in items:
        seg, note = _segment(w, tol, min_wall)
        segments += [seg] if seg else []
        issues += [note] if note else []
    return segments, issues


def _bounds(segments):
    """`{x: (min, max), y: (min, max)}` of the outer faces."""
    xs = [v for s in segments for v in ((s["c"],) if s["o"] == "v" else (s["lo"], s["hi"]))]
    ys = [v for s in segments for v in ((s["c"],) if s["o"] == "h" else (s["lo"], s["hi"]))]
    return {"x": (min(xs), max(xs)), "y": (min(ys), max(ys))}


def _snap(segments, bounds):
    """A wall end that lies within the wall's own thickness of the building bound across it is the exterior corner: it is moved onto that bound."""
    across = {"h": bounds["x"], "v": bounds["y"]}
    for s in segments:
        for key, bound in (("lo", across[s["o"]][0]), ("hi", across[s["o"]][1])):
            if abs(s[key] - bound) <= s["t"]:
                s[key] = bound
    return segments


def _opening_stops(seg, openings):
    """The two edges of each opening of the wall, as coordinates along its axis."""
    stops = []
    for op in openings:
        if op["wall"] == seg["id"]:
            first = seg["a_axis"] + seg["dir"] * op["from"]
            stops += [first, first + seg["dir"] * op["width"]]
    return stops


def _arriving(segments, o, value, near, reach, bounds_across, tol):
    """The centres of the walls that arrive at the edge from across it (the walls that are themselves corner walls of the building are left out)."""
    found = []
    for s in segments:
        corner = any(abs(s["c"] - b) <= tol for b in bounds_across)
        end = s["lo"] if near == "min" else s["hi"]
        if s["o"] != o and not corner and abs(end - value) <= reach:
            found.append(s["mid"])
    return found


def _edge_stops(segments, openings, o, value, near, tol, bounds_across):
    """The stops along an edge: `o` 'h' for the south and north edges (stops are X), 'v' for west and east. `value` is the edge's coordinate."""
    on_edge = [s for s in segments if s["o"] == o and abs(s["c"] - value) <= tol]
    stops = [v for s in on_edge for v in (s["lo"], s["hi"], *_opening_stops(s, openings))]
    reach = tol + max((s["t"] for s in on_edge), default=0.0)
    return stops + _arriving(segments, o, value, near, reach, bounds_across, tol)


def _merge(stops, tol):
    """Sorted stops with the ones within `tol` of the previous kept one dropped."""
    kept = []
    for v in sorted(stops):
        if not kept or v - kept[-1] > tol:
            kept.append(v)
    return kept


def _pair_key(p1, p2):
    a, b = (round(p1[0], 6), round(p1[1], 6)), (round(p2[0], 6), round(p2[1], 6))
    return (a, b) if a <= b else (b, a)


def _dim(n, kind, edge, o, p1, p2, line):
    value = abs(p2[0] - p1[0]) if o == "h" else abs(p2[1] - p1[1])
    return {"id": f"D{n}", "kind": kind, "edge": edge, "orientation": o, "p1": [round(p1[0], 6) + 0.0, round(p1[1], 6) + 0.0],
            "p2": [round(p2[0], 6) + 0.0, round(p2[1], 6) + 0.0], "line": round(line, 6) + 0.0, "value": round(value, 6)}


EDGES = (("south", "h", "y", "min", -1), ("north", "h", "y", "max", 1), ("west", "v", "x", "min", -1), ("east", "v", "x", "max", 1))


def _place(edge_value, o, a, b):
    """The two dimension points on the edge for the stops `a` and `b` along it."""
    return ((a, edge_value), (b, edge_value)) if o == "h" else ((edge_value, a), (edge_value, b))


def _edge_dims(edge, segments, openings, bounds, geo):
    """The chain of one edge and, on the south and west edges, the total: `[(kind, edge, o, p1, p2, line)]`."""
    name, o, key, near, sign = edge
    value = bounds[key][0 if near == "min" else 1]
    across = bounds["y" if key == "x" else "x"]
    stops = _merge(_edge_stops(segments, openings, o, value, near, geo["tol"], across), geo["tol"])
    out = []
    if name in ("south", "west"):
        p1, p2 = _place(value, o, *(bounds["x" if o == "h" else "y"]))
        out.append(("total", name, o, p1, p2, value + sign * (geo["gap"] + geo["step"])))
    for a, b in zip(stops, stops[1:]):
        p1, p2 = _place(value, o, a, b)
        out.append(("chain", name, o, p1, p2, value + sign * geo["gap"]))
    return out


def dimensions(walls, *, tol, gap, step, min_wall, openings=None, existing=None):
    """The exterior dimensions for `walls` (and `openings`, measured along the wall from its start `a`): `{dims, bounds, issues}`.

    `tol` (stops closer than this are one), `gap` (first row from the outer face), `step` (between rows) and `min_wall` (shorter walls are ignored) have no defaults.
    `existing` is a list of `{p1, p2}` already drawn; those are not made again.
    """
    tol, gap, step, min_wall = (inputs.positive(v, n) for v, n in ((tol, "tol"), (gap, "gap"), (step, "step"), (min_wall, "min_wall")))
    items = inputs.walls(walls)
    ops = inputs.openings(openings, {w["id"]: w for w in items})
    taken = {_pair_key(*pair) for pair in inputs.existing(existing)}
    segments, issues = _segments(items, tol, min_wall)
    issues.append(_note("note_not_done"))
    if not segments:
        return {"dims": [], "bounds": None, "issues": [_note("note_no_walls")] + issues}
    bounds = _bounds(segments)
    segments = _snap(segments, bounds)
    geo = {"tol": tol, "gap": gap, "step": step}
    dims = []
    for edge in EDGES:
        for kind, name, o, p1, p2, line in _edge_dims(edge, segments, ops, bounds, geo):
            key = _pair_key(p1, p2)
            if key not in taken:
                taken.add(key)
                dims.append(_dim(len(dims) + 1, kind, name, o, p1, p2, line))
    return {"dims": dims, "bounds": {"x": list(bounds["x"]), "y": list(bounds["y"])}, "issues": issues}
