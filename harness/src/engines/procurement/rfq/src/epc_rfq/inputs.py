"""Validation of the inputs of the RFQ engine: clear `ValueError` messages, no defaults for the commercial terms."""
import datetime
import math
import re

REQUIRED_TERMS = ("suppliers", "currency", "response_deadline", "delivery_site", "validity_days")
SUPPLIER_KEYS = ("name", "contact")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
DATASHEET_KINDS = ("protective_device", "cable")


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string (got {value!r})")
    return value.strip()


def optional_text(value, name):
    return None if value is None else text(value, name)


def iso_date(value, name):
    """An ISO calendar date `YYYY-MM-DD` (format and calendar validity only; no comparison with today)."""
    value = text(value, name)
    if not ISO_DATE.fullmatch(value):
        raise ValueError(f"{name} must be an ISO date YYYY-MM-DD (got {value!r})")
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{name} is not a valid calendar date (got {value!r})") from None
    return value


def positive_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive whole number (got {value!r})")
    return value


def number_or_none(value, name):
    """A positive finite number, or None (a line without quantity is carried and flagged)."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number or null (got {value!r})")
    return value


def _absent(value):
    if isinstance(value, str):
        return not value.strip()
    return value is None or (isinstance(value, (list, tuple)) and not value)


def missing_terms(given):
    """The required commercial fields that are absent, null, empty or blank."""
    return [name for name in REQUIRED_TERMS if _absent(given[name])]


def suppliers(items):
    """A validated copy of the supplier list: objects `{name, contact?}`, names unique (case-insensitive), the caller's order kept."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("suppliers must be a non-empty list of supplier objects")
    out = []
    for n, raw in enumerate(items, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"supplier {n}: must be an object (got {type(raw).__name__})")
        unknown = sorted(set(raw) - set(SUPPLIER_KEYS))
        if unknown:
            raise ValueError(f"supplier {n}: unknown key(s) {', '.join(unknown)}")
        out.append({"name": text(raw.get("name"), f"supplier {n}: name"), "contact": optional_text(raw.get("contact"), f"supplier {n}: contact")})
    names = [s["name"].lower() for s in out]
    duplicates = sorted({s["name"] for s in out if names.count(s["name"].lower()) > 1})
    if duplicates:
        raise ValueError(f"duplicate supplier name(s): {', '.join(duplicates)}")
    return out


def terms(given):
    """The validated commercial terms: `{"suppliers": [...], "terms": {...}}`.

    `given` maps every field of `REQUIRED_TERMS` plus `payment_terms` and `notes` to the caller's value (None when not given).
    """
    missing = missing_terms(given)
    if missing:
        raise ValueError(f"missing required commercial field(s): {', '.join(missing)}")
    return {"suppliers": suppliers(given["suppliers"]),
            "terms": {"currency": text(given["currency"], "currency"), "response_deadline": iso_date(given["response_deadline"], "response_deadline"),
                      "delivery_site": text(given["delivery_site"], "delivery_site"), "validity_days": positive_int(given["validity_days"], "validity_days"),
                      "payment_terms": optional_text(given["payment_terms"], "payment_terms"), "notes": optional_text(given["notes"], "notes")}}


def categories(requested):
    """A validated category filter (None keeps every category), as a sorted list without duplicates."""
    if requested is None:
        return None
    if not isinstance(requested, (list, tuple)) or not requested:
        raise ValueError("requestable_categories must be a non-empty list of category names or null")
    return sorted({text(c, "requestable_categories entry") for c in requested})


def _text_list(value, where, what):
    value = value or []
    if not isinstance(value, (list, tuple)) or not all(isinstance(v, str) for v in value):
        raise ValueError(f"{where}: {what} must be a list of text")
    return list(value)


def line(raw, n):
    """A validated copy of one BOQ item (a plain dict; unknown keys such as `basis` are ignored)."""
    if not isinstance(raw, dict):
        raise ValueError(f"BOQ item {n}: must be an object (got {type(raw).__name__})")
    item_id = text(raw.get("item_id"), f"BOQ item {n}: item_id")
    where = f"BOQ item {item_id}"
    spec = raw.get("spec") or {}
    if not isinstance(spec, dict):
        raise ValueError(f"{where}: spec must be an object")
    return {"item_id": item_id, "category": text(raw.get("category"), f"{where}: category"), "description": text(raw.get("description"), f"{where}: description"),
            "unit": text(raw.get("unit"), f"{where}: unit"), "quantity": number_or_none(raw.get("quantity"), f"{where}: quantity"),
            "source": sorted(_text_list(raw.get("source"), where, "source")), "issues": _text_list(raw.get("issues"), where, "issues"), "spec": dict(spec)}


def boq_items(boq):
    """The validated items of a BOQ structure (plain dict with `items`), sorted by item_id; duplicate ids are rejected."""
    if not isinstance(boq, dict) or not isinstance(boq.get("items"), (list, tuple)) or not boq["items"]:
        raise ValueError("boq must be a dict with a non-empty list `items`")
    items = [line(r, n) for n, r in enumerate(boq["items"], start=1)]
    ids = [i["item_id"] for i in items]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate BOQ item_id(s): {', '.join(duplicates)}")
    return sorted(items, key=lambda i: i["item_id"])


def _candidate(raw, where):
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: a candidate must be an object")
    out = {"manufacturer": text(raw.get("manufacturer"), f"{where}: manufacturer"), "product_id": text(raw.get("product_id"), f"{where}: product_id")}
    out.update({k: raw.get(k) for k in ("family", "source", "catalog_status")})
    return out


def _sheet(raw, n):
    if not isinstance(raw, dict):
        raise ValueError(f"datasheet {n}: must be an object (got {type(raw).__name__})")
    item_id = text(raw.get("item_id"), f"datasheet {n}: item_id")
    where = f"datasheet {item_id}"
    if raw.get("kind") not in DATASHEET_KINDS:
        raise ValueError(f"{where}: kind must be one of {', '.join(DATASHEET_KINDS)} (got {raw.get('kind')!r})")
    if not isinstance(raw.get("requirement"), dict) or not isinstance(raw.get("candidates"), (list, tuple)):
        raise ValueError(f"{where}: requirement must be an object and candidates a list")
    return {"item_id": item_id, "kind": raw["kind"], "requirement": dict(raw["requirement"]), "candidates": [_candidate(c, where) for c in raw["candidates"]]}


def datasheets(ds):
    """The validated datasheet records of an `epc_datasheets` structure (plain dict with `datasheets`), or an empty list for None."""
    if ds is None:
        return []
    if not isinstance(ds, dict) or not isinstance(ds.get("datasheets"), (list, tuple)):
        raise ValueError("datasheets must be a dict with a list `datasheets`")
    return [_sheet(r, n) for n, r in enumerate(ds["datasheets"], start=1)]
