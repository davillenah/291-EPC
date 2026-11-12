"""Validation of the inputs of the bill of quantities: clear `ValueError` messages, no defaults for values that matter."""
import math

CIRCUIT_KEYS = ("tag", "phases", "s_mm2", "neutral_mm2", "pe_mm2", "length_m", "material", "insulation", "in_a", "device_kind", "poles",
                "breaking_capacity_ka", "description", "device")
TEXT_KEYS = ("material", "insulation", "device_kind")
OPTIONAL_NUMBERS = ("neutral_mm2", "pe_mm2", "length_m", "in_a", "breaking_capacity_ka")


def number(value, name, optional=False):
    """A positive finite number (None allowed when `optional`)."""
    if value is None and optional:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number (got {value!r})")
    return value


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string (got {value!r})")
    return value


def optional_text(value, name):
    return None if value is None else text(value, name).strip().lower()


def allowance(value):
    """The wastage/allowance percentage: REQUIRED (no default), 0 allowed, never negative."""
    if value is None:
        raise ValueError("allowance_pct is required: give the wastage/allowance percentage of the cable lengths explicitly (0 is allowed)")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
        raise ValueError(f"allowance_pct must be a finite number >= 0 (got {value!r})")
    return value


def poles(value, where):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value not in (1, 2, 3, 4):
        raise ValueError(f"{where}: poles must be 1, 2, 3 or 4 (got {value!r})")
    return value


def circuit(raw, n):
    """A validated copy of one input circuit. Unknown keys are rejected; optional fields stay `None` (never guessed)."""
    if not isinstance(raw, dict):
        raise ValueError(f"circuit {n}: must be an object (got {type(raw).__name__})")
    unknown = sorted(set(raw) - set(CIRCUIT_KEYS))
    if unknown:
        raise ValueError(f"circuit {n}: unknown key(s) {', '.join(unknown)}")
    tag = text(raw.get("tag"), f"circuit {n}: tag")
    where = f"circuit {tag}"
    if raw.get("phases") not in (1, 3) or isinstance(raw.get("phases"), bool):
        raise ValueError(f"{where}: phases must be 1 or 3 (got {raw.get('phases')!r})")
    checked = {"tag": tag, "phases": raw["phases"], "s_mm2": number(raw.get("s_mm2"), f"{where}: s_mm2"), "poles": poles(raw.get("poles"), where)}
    checked.update({k: number(raw.get(k), f"{where}: {k}", True) for k in OPTIONAL_NUMBERS})
    checked.update({k: optional_text(raw.get(k), f"{where}: {k}") for k in TEXT_KEYS})
    return checked


def circuits(items):
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("circuits must be a non-empty list of circuit objects")
    checked = [circuit(c, n) for n, c in enumerate(items, start=1)]
    tags = [c["tag"] for c in checked]
    duplicates = sorted({t for t in tags if tags.count(t) > 1})
    if duplicates:
        raise ValueError(f"duplicate circuit tag(s): {', '.join(duplicates)}")
    return checked


def terminal_totals(value):
    """`{size_mm2 (text): count}` from the totals of a terminal-block list (`totals.by_terminal_size`), or `{}` when none is given.

    Accepts the totals object, or the whole list (its `totals` key). The size `none` (terminals without a size) is kept and reported by the caller.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"terminal_totals must be an object (got {type(value).__name__})")
    totals = value.get("totals", value)
    by_size = totals.get("by_terminal_size") if isinstance(totals, dict) else None
    if not isinstance(by_size, dict):
        raise ValueError("terminal_totals must have a by_terminal_size object ({size_mm2: count})")
    return {str(size): _count(count, size) for size, count in by_size.items()}


def _count(count, size):
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError(f"terminal_totals: the count of size {size} must be an integer >= 0 (got {count!r})")
    if size != "none":
        number(_size(size), f"terminal_totals: size {size!r}")
    return count


def _size(size):
    try:
        return float(size)
    except (TypeError, ValueError):
        raise ValueError(f"terminal_totals: size {size!r} is not a number of mm2 or 'none'") from None
