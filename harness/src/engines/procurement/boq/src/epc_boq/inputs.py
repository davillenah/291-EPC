"""Validation of the inputs of the bill of quantities: clear `ValueError` messages, no defaults for values that matter."""
import math
from epc_boq.errors import BoqError

CIRCUIT_KEYS = ("tag", "phases", "s_mm2", "neutral_mm2", "pe_mm2", "length_m", "material", "insulation", "in_a", "device_kind", "poles",
                "breaking_capacity_ka", "description", "device")
TEXT_KEYS = ("material", "insulation", "device_kind")
OPTIONAL_NUMBERS = ("neutral_mm2", "pe_mm2", "length_m", "in_a", "breaking_capacity_ka")


def number(value, name, optional=False):
    """A positive finite number (None allowed when `optional`)."""
    if value is None and optional:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise BoqError("err_not_positive_number", name=name, value=value)
    return value


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise BoqError("err_not_text", name=name, value=value)
    return value


def optional_text(value, name):
    return None if value is None else text(value, name).strip().lower()


def allowance(value):
    """The wastage/allowance percentage: REQUIRED (no default), 0 allowed, never negative."""
    if value is None:
        raise BoqError("err_allowance_required")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
        raise BoqError("err_allowance_invalid", value=value)
    return value


def poles(value, where):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value not in (1, 2, 3, 4):
        raise BoqError("err_poles_invalid", where=where, value=value)
    return value


def circuit(raw, n):
    """A validated copy of one input circuit. Unknown keys are rejected; optional fields stay `None` (never guessed)."""
    if not isinstance(raw, dict):
        raise BoqError("err_circuit_not_object", n=n, got=type(raw).__name__)
    unknown = sorted(set(raw) - set(CIRCUIT_KEYS))
    if unknown:
        raise BoqError("err_circuit_unknown_keys", n=n, keys=', '.join(unknown))
    tag = text(raw.get("tag"), f"circuit {n}: tag")
    where = f"circuit {tag}"
    if raw.get("phases") not in (1, 3) or isinstance(raw.get("phases"), bool):
        raise BoqError("err_phases_not_1_or_3", where=where, value=raw.get('phases'))
    checked = {"tag": tag, "phases": raw["phases"], "s_mm2": number(raw.get("s_mm2"), f"{where}: s_mm2"), "poles": poles(raw.get("poles"), where)}
    checked.update({k: number(raw.get(k), f"{where}: {k}", True) for k in OPTIONAL_NUMBERS})
    checked.update({k: optional_text(raw.get(k), f"{where}: {k}") for k in TEXT_KEYS})
    return checked


def circuits(items):
    if not isinstance(items, (list, tuple)) or not items:
        raise BoqError("err_circuits_empty")
    checked = [circuit(c, n) for n, c in enumerate(items, start=1)]
    tags = [c["tag"] for c in checked]
    duplicates = sorted({t for t in tags if tags.count(t) > 1})
    if duplicates:
        raise BoqError("err_duplicate_tags", tags=', '.join(duplicates))
    return checked


def terminal_totals(value):
    """`{size_mm2 (text): count}` from the totals of a terminal-block list (`totals.by_terminal_size`), or `{}` when none is given.

    Accepts the totals object, or the whole list (its `totals` key). The size `none` (terminals without a size) is kept and reported by the caller.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise BoqError("err_terminal_totals_not_object", got=type(value).__name__)
    totals = value.get("totals", value)
    by_size = totals.get("by_terminal_size") if isinstance(totals, dict) else None
    if not isinstance(by_size, dict):
        raise BoqError("err_terminal_totals_no_sizes")
    return {str(size): _count(count, size) for size, count in by_size.items()}


def _count(count, size):
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise BoqError("err_terminal_count_invalid", size=size, count=count)
    if size != "none":
        number(_size(size), f"terminal_totals: size {size!r}")
    return count


def _size(size):
    try:
        return float(size)
    except (TypeError, ValueError):
        raise BoqError("err_terminal_size_invalid", size=size) from None
