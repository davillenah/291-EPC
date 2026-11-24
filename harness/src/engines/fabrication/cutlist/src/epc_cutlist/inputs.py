"""Validation of the inputs of the cut list: clear `CutlistError` messages, no defaults for values that matter (the saw kerf is required)."""
import math

from epc_cutlist.errors import CutlistError

PART_KEYS = ("id", "material", "length_mm", "quantity", "size", "label", "angle_1_deg", "angle_2_deg", "angle_source")
STOCK_KEYS = ("length_mm", "count")
ANGLE_SOURCES = ("given", "derived", "unknown")


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def positive(value, name):
    if not _is_number(value) or value <= 0:
        raise CutlistError("err_not_positive_number", name=name, value=value)
    return float(value)


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise CutlistError("err_not_text", name=name, value=value)
    return value.strip()


def whole(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CutlistError("err_not_integer", name=name, value=value)
    return value


def kerf(value):
    """The saw kerf: REQUIRED (no default), 0 allowed, never negative."""
    if value is None:
        raise CutlistError("err_kerf_required")
    if not _is_number(value) or value < 0:
        raise CutlistError("err_kerf_invalid", value=value)
    return float(value)


def _unknown(raw, allowed, where):
    unknown = sorted(set(raw) - set(allowed))
    if unknown:
        raise CutlistError("err_unknown_keys", where=where, keys=", ".join(unknown))


def _stock_entry(raw, material):
    """One stock length: a number, or `{length_mm, count}` where `count` (optional) limits how many bars are available."""
    where = f"stock {material}"
    if not isinstance(raw, dict):
        return {"length_mm": positive(raw, f"{where}: length_mm"), "count": None}
    _unknown(raw, STOCK_KEYS, where)
    count = raw.get("count")
    return {"length_mm": positive(raw.get("length_mm"), f"{where}: length_mm"), "count": None if count is None else whole(count, f"{where}: count")}


def stock(value):
    """`{material: [stock entries]}` sorted by length, one entry per distinct length (counts of equal lengths are added; an unlimited one stays unlimited)."""
    if not isinstance(value, dict) or not value:
        raise CutlistError("err_stock_empty")
    checked = {}
    for material, entries in value.items():
        name = text(material, "stock material").lower()
        listed = entries if isinstance(entries, (list, tuple)) else [entries]
        if not listed:
            raise CutlistError("err_stock_empty")
        checked[name] = _merge([_stock_entry(e, name) for e in listed])
    return checked


def _merge(entries):
    by_length = {}
    for e in entries:
        by_length.setdefault(e["length_mm"], []).append(e["count"])
    merged = []
    for length in sorted(by_length):
        counts = by_length[length]
        merged.append({"length_mm": length, "count": None if None in counts else sum(counts)})
    return merged


def _angle(raw, name, where):
    value = raw.get(name)
    if value is None:
        return None
    if not _is_number(value) or abs(value) > 90:
        raise CutlistError("err_angle_invalid", where=where, name=name, value=value)
    return float(value)


def part(raw, n):
    """A validated copy of one part. Unknown keys are rejected; optional fields stay `None` (never guessed)."""
    if not isinstance(raw, dict):
        raise CutlistError("err_not_object", where=f"part {n}", got=type(raw).__name__)
    _unknown(raw, PART_KEYS, f"part {n}")
    ident = text(raw.get("id"), f"part {n}: id")
    where = f"part {ident}"
    source = raw.get("angle_source", "given")
    if source not in ANGLE_SOURCES:
        raise CutlistError("err_angle_source_invalid", where=where, value=source)
    size = raw.get("size")
    return {"id": ident, "material": text(raw.get("material"), f"{where}: material").lower(), "length_mm": positive(raw.get("length_mm"), f"{where}: length_mm"),
            "quantity": whole(raw.get("quantity", 1), f"{where}: quantity"), "size": None if size is None else text(size, f"{where}: size"),
            "label": raw.get("label") if isinstance(raw.get("label"), str) else None, "angle_1_deg": _angle(raw, "angle_1_deg", where),
            "angle_2_deg": _angle(raw, "angle_2_deg", where), "angle_source": source}


def parts(items):
    if not isinstance(items, (list, tuple)) or not items:
        raise CutlistError("err_parts_empty")
    checked = [part(p, n) for n, p in enumerate(items, start=1)]
    ids = [p["id"] for p in checked]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise CutlistError("err_duplicate_part_ids", ids=", ".join(duplicates))
    return checked
