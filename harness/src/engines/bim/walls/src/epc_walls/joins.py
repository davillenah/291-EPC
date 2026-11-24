"""The join records of a set of straight walls: where a wall end lands on another wall.

A join is `{key, kind, a: {wall, pos}, b: {wall, pos}}`. `pos` is where on the wall: `start`, `end` or `mid`. The kind comes from the positions: L (end and end),
T (end and mid), X (mid and mid). The key is the same whatever the order of the pair. An end whose `join_off` is set makes no join.
"""
from epc_walls import vec


def _ends(w):
    return (("start", w["a"]), ("end", w["b"]))


def _key(x, y):
    p, q = f"{x['wall']}:{x['pos']}", f"{y['wall']}:{y['pos']}"
    return f"{p}|{q}" if p <= q else f"{q}|{p}"


def _record(x, y):
    first, second = (x, y) if f"{x['wall']}:{x['pos']}" <= f"{y['wall']}:{y['pos']}" else (y, x)
    kind = "X" if "mid" == first["pos"] == second["pos"] else ("T" if "mid" in (first["pos"], second["pos"]) else "L")
    return {"key": _key(x, y), "kind": kind, "a": first, "b": second}


def _on_side(point, w, tol):
    """True when `point` lies on the wall's centre line, farther than `tol` from both ends."""
    d = vec.sub(w["b"], w["a"])
    n = vec.length(d)
    s = vec.dot(vec.sub(point, w["a"]), d) / n
    return tol < s < n - tol and abs(vec.cross(vec.sub(point, w["a"]), d)) / n <= tol


def _crossing(x, y, tol):
    """True when the centre lines cross strictly inside both walls."""
    d, e = vec.sub(x["b"], x["a"]), vec.sub(y["b"], y["a"])
    hit = vec.intersect(x["a"], d, y["a"], e)
    if hit is None:
        return False
    s, t = hit[0] * vec.length(d), hit[1] * vec.length(e)
    return tol < s < vec.length(d) - tol and tol < t < vec.length(e) - tol


def _pair(x, y, tol):
    """The records between two walls: L for ends within `tol`, T for an end on the other's side, X for a crossing."""
    found, used = [], set()
    for px, pa in _ends(x):
        for py, pb in _ends(y):
            if not x["join_off"][px] and not y["join_off"][py] and vec.length(vec.sub(pa, pb)) <= tol:
                found.append(_record({"wall": x["id"], "pos": px}, {"wall": y["id"], "pos": py}))
                used.update({("x", px), ("y", py)})
    for mine, other, tag in ((x, y, "x"), (y, x, "y")):
        for pos, point in _ends(mine):
            if (tag, pos) not in used and not mine["join_off"][pos] and _on_side(point, other, tol):
                found.append(_record({"wall": mine["id"], "pos": pos}, {"wall": other["id"], "pos": "mid"}))
    if not found and _crossing(x, y, tol):
        found.append(_record({"wall": x["id"], "pos": "mid"}, {"wall": y["id"], "pos": "mid"}))
    return found


def derive(walls, tol):
    """The join records the geometry of `walls` (already validated) asks for, sorted by key."""
    records = []
    for n, x in enumerate(walls):
        for y in walls[n + 1:]:
            records += _pair(x, y, tol)
    return sorted(records, key=lambda r: r["key"])
