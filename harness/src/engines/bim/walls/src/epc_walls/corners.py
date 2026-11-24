"""Corner geometry of two walls that meet end to end (an L join) and the end of a wall that lands on the side of another (a T join).

Everything is trigonometry on lines: for each wall the two face lines are `p + (+-h) n + s d`, where `d` is the unit direction OUT of the corner along the
wall's centre line, `n` its left normal and `h` the half thickness. An end is described by two points named looking along `d`: `left` and `right`.
Styles of a corner: `mitre` (both ends cut on the line through the inner and the outer corner), `butt` (one wall runs through to the far face of the other, which
stops against its near face) and `square` (as butt, but the wall that runs through ends square, at the farthest point where the far face of the other reaches it).
"""
from epc_walls import vec


def _face(p, d, h, side):
    """`(point, direction)` of the face of a wall on its `left` or `right`."""
    n = vec.left(d)
    k = h if side == "left" else -h
    return ((p[0] + n[0] * k, p[1] + n[1] * k), d)


def _cut(face, other):
    """The point where a face line meets another line."""
    hit = vec.intersect(face[0], face[1], other[0], other[1])
    return None if hit is None else vec.at(face[0], face[1], hit[0])


def _within(points, p, h_max, ratio):
    return all(vec.length(vec.sub(q, p)) <= ratio * h_max for q in points)


def _mitre(p, a, b):
    (da, ha), (db, hb) = a, b
    al, ar = _face(p, da, ha, "left"), _face(p, da, ha, "right")
    bl, br = _face(p, db, hb, "left"), _face(p, db, hb, "right")
    outer_a, inner_a = _cut(al, br), _cut(ar, bl)
    return None if outer_a is None or inner_a is None else ((outer_a, inner_a), (inner_a, outer_a))


def _inner_side(da, db):
    """The side of wall A that faces wall B, and the side of B that faces A."""
    c = vec.cross(da, db)
    return ("left", "right") if c > 0 else ("right", "left")


def _opposite(side):
    return "right" if side == "left" else "left"


def _through(p, run, stop, style):
    """The ends when wall `run` runs through the corner and wall `stop` stops against it. Returns `(run_end, stop_end)` or None."""
    (dr, hr), (ds, hs) = run, stop
    side_run, side_stop = _inner_side(dr, ds)
    far_stop = _face(p, ds, hs, _opposite(side_stop))
    near_run = _face(p, dr, hr, side_run)
    rl, rr = _face(p, dr, hr, "left"), _face(p, dr, hr, "right")
    end_l, end_r = _cut(rl, far_stop), _cut(rr, far_stop)
    stop_l, stop_r = _cut(_face(p, ds, hs, "left"), near_run), _cut(_face(p, ds, hs, "right"), near_run)
    if None in (end_l, end_r, stop_l, stop_r):
        return None
    if style == "square":
        s = min(vec.dot(vec.sub(end_l, rl[0]), dr), vec.dot(vec.sub(end_r, rr[0]), dr))
        end_l, end_r = vec.at(rl[0], dr, s), vec.at(rr[0], dr, s)
    return (end_l, end_r), (stop_l, stop_r)


def corner(p, a, b, *, style, through, ratio):
    """The two ends of an L corner at `p`: `a` and `b` are `(d, h)` of each wall. Returns `{style, a: (left, right), b: (left, right)}` or None.

    None means the corner cannot be made as asked (walls in one line, or an end point farther than `ratio` times the larger half thickness): the caller keeps square
    ends. `through` is `'a'` or `'b'`, the wall that runs through for `butt` and `square` (default `'a'`).
    """
    h_max = max(a[1], b[1])
    if style == "mitre":
        result = _mitre(p, a, b)
        ends = None if result is None else {"a": result[0], "b": result[1]}
    else:
        run, stop = (a, b) if through != "b" else (b, a)
        made = _through(p, run, stop, style)
        ends = None if made is None else ({"a": made[0], "b": made[1]} if through != "b" else {"a": made[1], "b": made[0]})
    if ends is None or not _within([q for e in ends.values() for q in e], p, h_max, ratio):
        return None
    return {"style": style, "a": ends["a"], "b": ends["b"]}


def stem_end(q, d, h, host_point, host_d, host_h, ratio):
    """The end of a wall (`q`, out direction `d`, half thickness `h`) that lands on the side of a host wall: it is cut on the host's face nearest to it.

    Returns `(left, right)` or None when the walls are parallel or the cut is too far from `q`.
    """
    host_n = vec.left(host_d)
    side = "left" if vec.dot(host_n, d) > 0 else "right"
    near = _face(host_point, host_d, host_h, side)
    left, right = _cut(_face(q, d, h, "left"), near), _cut(_face(q, d, h, "right"), near)
    if left is None or right is None or not _within([left, right], q, max(h, host_h), ratio):
        return None
    return (left, right)
