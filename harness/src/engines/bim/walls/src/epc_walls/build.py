"""The outlines of straight walls and the join records between them.

Every wall starts as a rectangle (its centre line widened by half its thickness each side). Each L join then trims or extends the two ends that meet according to
its style; each T join cuts the stem on the face of the host that is nearest to it; an X join only records the crossing. What cannot be made as asked keeps its
square ends and comes back as a note (never silently).
"""
from epc_walls import assembly, corners, inputs, joins, vec
from epc_walls.errors import WallsError
from epc_walls.messages import text


def _note(code, **params):
    return {"code": code, **text(code, **params)}


def _frame(w):
    """The unit direction a to b, half thickness and the default square ends `{start: (left, right), end: (left, right)}` in that frame."""
    d = vec.unit(vec.sub(w["b"], w["a"]))
    n, h = vec.left(d), w["t"] / 2
    ends = {"start": (vec.at(w["a"], n, h), vec.at(w["a"], n, -h)), "end": (vec.at(w["b"], n, h), vec.at(w["b"], n, -h))}
    return d, h, ends


def _out(w, pos, d):
    """The unit direction out of the wall at its end `pos`, and the end's point."""
    return (d, w["a"]) if pos == "start" else (vec.mul(d, -1.0), w["b"])


def _set_end(ends, pos, pair):
    """Store an end given as `(left, right)` looking OUT of the wall; the stored frame looks along a to b, so at the far end the two swap."""
    ends[pos] = pair if pos == "start" else (pair[1], pair[0])


def _busy(records):
    """The ends that take part in more than one join: `{(wall, pos): how many}`."""
    count = {}
    for r in records:
        for side in ("a", "b"):
            if r[side]["pos"] != "mid":
                key = (r[side]["wall"], r[side]["pos"])
                count[key] = count.get(key, 0) + 1
    return {k: n for k, n in count.items() if n > 1}


def _style_of(record, styles, ids):
    """`(style, through)` asked for this join: `through` is 'a' or 'b' (record side)."""
    given = styles.get(record["key"])
    if given is None:
        return "mitre", "a"
    through = given["through"]
    if through is None:
        return given["style"], "a"
    names = {record["a"]["wall"]: "a", record["b"]["wall"]: "b"}
    if through not in names:
        raise WallsError("err_style_invalid", key=record["key"], value=through)
    return given["style"], names[through]


def _apply_l(record, frames, ends, walls_by_id, styles, ratio):
    """Cut an L join; returns `(applied style, note or None)`."""
    style, through = _style_of(record, styles, walls_by_id)
    sides = {}
    for tag in ("a", "b"):
        w = walls_by_id[record[tag]["wall"]]
        d, _, _ = frames[w["id"]]
        out, point = _out(w, record[tag]["pos"], d)
        sides[tag] = (out, w["t"] / 2, point)
    point = sides["a"][2]
    made = corners.corner(point, sides["a"][:2], sides["b"][:2], style=style, through=through, ratio=ratio)
    if made is None:
        return "square", _note("note_corner_square", key=record["key"], limit=ratio)
    for tag in ("a", "b"):
        _set_end(ends[record[tag]["wall"]], record[tag]["pos"], made[tag])
    return style, None


def _apply_t(record, frames, ends, walls_by_id, ratio):
    """Cut the stem of a T join on the host's near face; returns `(applied, note or None)`."""
    stem, host = (record["a"], record["b"]) if record["b"]["pos"] == "mid" else (record["b"], record["a"])
    sw, hw = walls_by_id[stem["wall"]], walls_by_id[host["wall"]]
    out, point = _out(sw, stem["pos"], frames[sw["id"]][0])
    made = corners.stem_end(point, out, sw["t"] / 2, hw["a"], frames[hw["id"]][0], hw["t"] / 2, ratio)
    if made is None:
        return "square", _note("note_t_not_through", key=record["key"])
    _set_end(ends[sw["id"]], stem["pos"], made)
    return "tee", None


def _polygon(ends):
    """The outline, counter-clockwise from the start's left point."""
    (ls, rs), (le, re) = ends["start"], ends["end"]
    return [vec.round_point(p) for p in (ls, le, re, rs)]


def _wall_entry(w, ends):
    entry = {"thickness": w["t"], "outline": _polygon(ends), "layered": w["layers"] is not None}
    if w["layers"] is not None:
        entry["bands"] = assembly.bands(w["layers"], w["ext_side"])
    return entry


def _busy_notes(busy, walls_by_id):
    return [_note("note_node_complex", at=vec.round_point(walls_by_id[wall]["a" if pos == "start" else "b"]), count=n + 1) for (wall, pos), n in sorted(busy.items())]


def outlines(walls, *, tol, styles=None, max_mitre_ratio=None):
    """The outline of each wall and the joins: `{walls: {id: {thickness, outline, layered, bands?}}, joins: [{key, kind, a, b, applied}], issues: [...]}`.

    `tol` is the distance (same unit as the points) within which two ends count as meeting; it has no default on purpose. `styles` is `{join key: style or
    {style, through}}` for L joins (default `mitre`).
    """
    tol = inputs.positive(tol, "tol")
    ratio = inputs.positive(max_mitre_ratio, "max_mitre_ratio") if max_mitre_ratio is not None else inputs.PARAMS["max_mitre_ratio"]
    items, asked = inputs.walls(walls), inputs.styles(styles)
    by_id = {w["id"]: w for w in items}
    frames = {w["id"]: _frame(w) for w in items}
    ends = {i: dict(f[2]) for i, f in frames.items()}
    records = joins.derive(items, tol)
    busy = _busy(records)
    issues = _busy_notes(busy, by_id)
    done = []
    for r in records:
        applied, note = _join(r, busy, frames, ends, by_id, asked, ratio)
        done.append({**r, "applied": applied})
        issues += [note] if note else []
    return {"walls": {w["id"]: _wall_entry(w, ends[w["id"]]) for w in items}, "joins": done, "issues": issues}


def _join(r, busy, frames, ends, by_id, asked, ratio):
    if r["kind"] == "X":
        return "cross", None
    if any((r[s]["wall"], r[s]["pos"]) in busy for s in ("a", "b")):
        return "square", None
    if r["kind"] == "T":
        return _apply_t(r, frames, ends, by_id, ratio)
    return _apply_l(r, frames, ends, by_id, asked, ratio)
