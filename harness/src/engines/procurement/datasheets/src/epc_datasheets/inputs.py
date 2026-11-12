"""Validation of the inputs of the datasheets engine: clear `ValueError` messages, no defaults for values that matter.

The circuit shape is the one of the bill-of-quantities engine (duplicated here on purpose: engines stay independent).
"""
import math

CIRCUIT_KEYS = ("tag", "phases", "s_mm2", "neutral_mm2", "pe_mm2", "length_m", "material", "insulation", "in_a", "device_kind", "poles",
                "breaking_capacity_ka", "description", "device")
TEXT_KEYS = ("material", "insulation", "device_kind")
OPTIONAL_NUMBERS = ("neutral_mm2", "pe_mm2", "length_m", "in_a", "breaking_capacity_ka")
DEVICE_KIND = "protective_device"
CABLE_KIND = "cable"
DEVICE_FIELDS = ("item_id", "kind", "device_kind", "in_a", "poles", "breaking_capacity_ka", "voltage_v", "circuits")
CABLE_FIELDS = ("item_id", "kind", "material", "insulation", "phase_conductors", "s_mm2", "neutral_mm2", "pe_mm2", "cores", "circuits")


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


def _requirement(raw, n):
    """A validated copy of one requirement (the shape `requirements_from_circuits` produces)."""
    if not isinstance(raw, dict):
        raise ValueError(f"requirement {n}: must be an object (got {type(raw).__name__})")
    kind = raw.get("kind")
    fields = {DEVICE_KIND: DEVICE_FIELDS, CABLE_KIND: CABLE_FIELDS}.get(kind)
    if fields is None:
        raise ValueError(f"requirement {n}: kind must be '{DEVICE_KIND}' or '{CABLE_KIND}' (got {kind!r})")
    unknown = sorted(set(raw) - set(fields))
    if unknown:
        raise ValueError(f"requirement {n}: unknown key(s) {', '.join(unknown)}")
    where = f"requirement {text(raw.get('item_id'), f'requirement {n}: item_id')}"
    checked = {"item_id": raw["item_id"], "kind": kind, "circuits": _tags(raw.get("circuits"), where)}
    if kind == DEVICE_KIND:
        checked.update(_device(raw, where))
    else:
        checked.update(_cable(raw, where))
    return checked


def _tags(value, where):
    if not isinstance(value, (list, tuple)) or not all(isinstance(t, str) and t.strip() for t in value):
        raise ValueError(f"{where}: circuits must be a list of circuit tags")
    return sorted(value)


def _device(raw, where):
    out = {k: number(raw.get(k), f"{where}: {k}", True) for k in ("in_a", "breaking_capacity_ka", "voltage_v")}
    out.update({"device_kind": optional_text(raw.get("device_kind"), f"{where}: device_kind"), "poles": poles(raw.get("poles"), where)})
    return out


def _cable(raw, where):
    out = {k: number(raw.get(k), f"{where}: {k}") for k in ("s_mm2", "phase_conductors", "cores")}
    out.update({k: number(raw.get(k), f"{where}: {k}", True) for k in ("neutral_mm2", "pe_mm2")})
    out.update({k: optional_text(raw.get(k), f"{where}: {k}") for k in ("material", "insulation")})
    return out


def requirements(items):
    if not isinstance(items, (list, tuple)):
        raise ValueError("requirements must be a list of requirement objects")
    checked = [_requirement(r, n) for n, r in enumerate(items, start=1)]
    ids = [r["item_id"] for r in checked]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate requirement item_id(s): {', '.join(duplicates)}")
    return checked
