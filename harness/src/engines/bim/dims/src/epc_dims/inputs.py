"""Validation of the inputs of the dimensions engine. The distances that shape the result (`gap`, `step`, `min_wall`, `tol`) have no defaults: they are design choices of the project."""
import math

from epc_dims.errors import DimsError

WALL_KEYS = ("id", "a", "b", "t", "ext_side")
OPENING_KEYS = ("id", "wall", "from", "width")


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def positive(value, name):
    if not _number(value) or value <= 0:
        raise DimsError("err_not_positive_number", name=name, value=value)
    return float(value)


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise DimsError("err_not_text", name=name, value=value)
    return value.strip()


def point(value, where):
    if not isinstance(value, (list, tuple)) or len(value) != 2 or not all(_number(v) for v in value):
        raise DimsError("err_not_point", where=where, value=value)
    return (float(value[0]), float(value[1]))


def _object(raw, allowed, where):
    if not isinstance(raw, dict):
        raise DimsError("err_not_object", where=where, got=type(raw).__name__)
    unknown = sorted(set(raw) - set(allowed))
    if unknown:
        raise DimsError("err_unknown_keys", where=where, keys=", ".join(unknown))


def _wall(raw, n):
    _object(raw, WALL_KEYS, f"wall {n}")
    ident = text(raw.get("id"), f"wall {n}: id")
    side = raw.get("ext_side", "left")
    if side not in ("left", "right"):
        raise DimsError("err_ext_side", where=f"wall {ident}", value=side)
    return {"id": ident, "a": point(raw.get("a"), f"wall {ident}: a"), "b": point(raw.get("b"), f"wall {ident}: b"),
            "t": positive(raw.get("t"), f"wall {ident}: t"), "ext_side": side}


def _unique(items, what):
    ids = [i["id"] for i in items]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise DimsError("err_duplicate_ids", what=what, ids=", ".join(duplicates))
    return items


def walls(items):
    if not isinstance(items, (list, tuple)) or not items:
        raise DimsError("err_walls_empty")
    return _unique([_wall(w, n) for n, w in enumerate(items, start=1)], "wall")


def _opening(raw, n, walls_by_id):
    _object(raw, OPENING_KEYS, f"opening {n}")
    ident, wall_id = text(raw.get("id"), f"opening {n}: id"), text(raw.get("wall"), f"opening {n}: wall")
    if wall_id not in walls_by_id:
        raise DimsError("err_opening_wall", id=ident, wall=wall_id)
    start, width = raw.get("from"), positive(raw.get("width"), f"opening {ident}: width")
    w = walls_by_id[wall_id]
    length = math.hypot(w["b"][0] - w["a"][0], w["b"][1] - w["a"][1])
    first = float(start) if _number(start) else 0.0
    if not _number(start) or start < 0 or start + width > length + 1e-9:
        raise DimsError("err_opening_range", id=ident, length=length, start=first, end=first + width)
    return {"id": ident, "wall": wall_id, "from": first, "width": width}


def openings(items, walls_by_id):
    """Openings checked: each lies inside its wall, measured along the wall from its start `a`."""
    return _unique([_opening(raw, n, walls_by_id) for n, raw in enumerate(items or [], start=1)], "opening")


def existing(items):
    """The dimensions already drawn: a list of `{p1, p2}`; the order of the two points does not matter."""
    out = []
    for n, raw in enumerate(items or [], start=1):
        _object(raw, ("p1", "p2"), f"existing dimension {n}")
        out.append((point(raw.get("p1"), f"existing dimension {n}: p1"), point(raw.get("p2"), f"existing dimension {n}: p2")))
    return out
