"""Validation of the inputs of the walls engine: clear `WallsError` messages, no defaults for values that matter (the join tolerance is required)."""
import json
import math
from pathlib import Path

from epc_walls.errors import WallsError

PARAMS = json.loads((Path(__file__).resolve().parent / "params.json").read_text(encoding="utf-8"))
WALL_KEYS = ("id", "a", "b", "t", "layers", "ext_side", "join_off")
LAYER_KEYS = ("mat", "t", "function", "kind", "priority", "core")
SIDES = ("left", "right")
STYLES = ("mitre", "butt", "square")


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def positive(value, name):
    if not _number(value) or value <= 0:
        raise WallsError("err_not_positive_number", name=name, value=value)
    return float(value)


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise WallsError("err_not_text", name=name, value=value)
    return value.strip()


def point(value, where):
    if not isinstance(value, (list, tuple)) or len(value) != 2 or not all(_number(v) for v in value):
        raise WallsError("err_not_point", where=where, value=value)
    return (float(value[0]), float(value[1]))


def _unknown(raw, allowed, where):
    unknown = sorted(set(raw) - set(allowed))
    if unknown:
        raise WallsError("err_unknown_keys", where=where, keys=", ".join(unknown))


def layer(raw, where):
    """A validated layer: from the exterior inward, with material, thickness (mm), function, kind, optional priority and core flag."""
    if not isinstance(raw, dict):
        raise WallsError("err_not_object", where=where, got=type(raw).__name__)
    _unknown(raw, LAYER_KEYS, where)
    high = PARAMS["layer_thickness_max_mm"]
    thickness = raw.get("t")
    if not _number(thickness) or thickness < 0 or thickness > high:
        raise WallsError("err_layer_thickness", where=where, high=high, value=thickness)
    function, kind = raw.get("function"), raw.get("kind", "material")
    if function not in PARAMS["layer_functions"]:
        raise WallsError("err_layer_function", where=where, allowed=", ".join(PARAMS["layer_functions"]), value=function)
    if kind not in ("material", "cavity"):
        raise WallsError("err_layer_kind", where=where, value=kind)
    if thickness == 0 and (kind != "material" or function != "membrane"):
        raise WallsError("err_layer_zero_not_membrane", where=where)
    return {"mat": text(raw.get("mat"), f"{where}: mat"), "t": float(thickness), "function": function, "kind": kind, "priority": _priority(raw.get("priority"), where),
            "core": raw.get("core") is True}


def _priority(value, where):
    low, high = PARAMS["layer_priority_range"]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise WallsError("err_layer_priority", where=where, low=low, high=high, value=value)
    return value


def layers(items, where="assembly"):
    high = PARAMS["layers_max"]
    if not isinstance(items, (list, tuple)) or not 1 <= len(items) <= high:
        raise WallsError("err_layers_count", high=high, count=len(items) if isinstance(items, (list, tuple)) else 0)
    checked = [layer(item, f"{where} layer {n}") for n, item in enumerate(items, start=1)]
    if not sum(c["t"] for c in checked) > 0:
        raise WallsError("err_layers_no_thickness")
    return checked


def _thickness(raw, where):
    """`(thickness, layers or None)`: either `t` or `layers`, never both (the thickness of a layered wall is the sum of its layers)."""
    if raw.get("t") is not None and raw.get("layers") is not None:
        raise WallsError("err_wall_both_thickness", where=where)
    if raw.get("layers") is not None:
        checked = layers(raw["layers"], where)
        return round(sum(c["t"] for c in checked), 6), checked
    if raw.get("t") is None:
        raise WallsError("err_wall_no_thickness", where=where)
    return positive(raw["t"], f"{where}: t"), None


def wall(raw, n):
    if not isinstance(raw, dict):
        raise WallsError("err_not_object", where=f"wall {n}", got=type(raw).__name__)
    _unknown(raw, WALL_KEYS, f"wall {n}")
    ident = text(raw.get("id"), f"wall {n}: id")
    where = f"wall {ident}"
    a, b = point(raw.get("a"), f"{where}: a"), point(raw.get("b"), f"{where}: b")
    if a == b:
        raise WallsError("err_wall_zero_length", where=where)
    thickness, parts = _thickness(raw, where)
    side = raw.get("ext_side", "left")
    if side not in SIDES:
        raise WallsError("err_unknown_keys", where=where, keys=f"ext_side={side!r}")
    off = raw.get("join_off") or {}
    return {"id": ident, "a": a, "b": b, "t": thickness, "layers": parts, "ext_side": side, "join_off": {"start": bool(off.get("a")), "end": bool(off.get("b"))}}


def walls(items):
    if not isinstance(items, (list, tuple)) or not items:
        raise WallsError("err_walls_empty")
    checked = [wall(w, n) for n, w in enumerate(items, start=1)]
    ids = [w["id"] for w in checked]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise WallsError("err_duplicate_wall_ids", ids=", ".join(duplicates))
    return checked


def styles(raw):
    """`{join key: {style, through}}` checked; an unknown style is refused."""
    checked = {}
    for key, value in (raw or {}).items():
        style = value.get("style") if isinstance(value, dict) else value
        if style not in STYLES:
            raise WallsError("err_style_invalid", key=key, value=style)
        checked[key] = {"style": style, "through": value.get("through") if isinstance(value, dict) else None}
    return checked
