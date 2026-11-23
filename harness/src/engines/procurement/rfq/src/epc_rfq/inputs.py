"""Validation of the inputs of the RFQ engine: clear `ValueError` messages, no defaults for the commercial terms."""
import datetime
import math
import re
from epc_rfq.errors import RfqError

REQUIRED_TERMS = ("suppliers", "currency", "response_deadline", "delivery_site", "validity_days")
SUPPLIER_KEYS = ("name", "contact")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
DATASHEET_KINDS = ("protective_device", "cable")


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise RfqError("err_not_text", name=name, value=value)
    return value.strip()


def optional_text(value, name):
    return None if value is None else text(value, name)


def iso_date(value, name):
    """An ISO calendar date `YYYY-MM-DD` (format and calendar validity only; no comparison with today)."""
    value = text(value, name)
    if not ISO_DATE.fullmatch(value):
        raise RfqError("err_not_iso_date", name=name, value=value)
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise RfqError("err_not_calendar_date", name=name, value=value) from None
    return value


def positive_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RfqError("err_not_positive_integer", name=name, value=value)
    return value


def number_or_none(value, name):
    """A positive finite number, or None (a line without quantity is carried and flagged)."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise RfqError("err_not_positive_number_or_null", name=name, value=value)
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
        raise RfqError("err_suppliers_empty")
    out = []
    for n, raw in enumerate(items, start=1):
        if not isinstance(raw, dict):
            raise RfqError("err_supplier_not_object", n=n, got=type(raw).__name__)
        unknown = sorted(set(raw) - set(SUPPLIER_KEYS))
        if unknown:
            raise RfqError("err_supplier_unknown_keys", n=n, keys=', '.join(unknown))
        out.append({"name": text(raw.get("name"), f"supplier {n}: name"), "contact": optional_text(raw.get("contact"), f"supplier {n}: contact")})
    names = [s["name"].lower() for s in out]
    duplicates = sorted({s["name"] for s in out if names.count(s["name"].lower()) > 1})
    if duplicates:
        raise RfqError("err_duplicate_suppliers", names=', '.join(duplicates))
    return out


def terms(given):
    """The validated commercial terms: `{"suppliers": [...], "terms": {...}}`.

    `given` maps every field of `REQUIRED_TERMS` plus `payment_terms` and `notes` to the caller's value (None when not given).
    """
    missing = missing_terms(given)
    if missing:
        raise RfqError("err_missing_commercial_fields", fields=', '.join(missing))
    return {"suppliers": suppliers(given["suppliers"]),
            "terms": {"currency": text(given["currency"], "currency"), "response_deadline": iso_date(given["response_deadline"], "response_deadline"),
                      "delivery_site": text(given["delivery_site"], "delivery_site"), "validity_days": positive_int(given["validity_days"], "validity_days"),
                      "payment_terms": optional_text(given["payment_terms"], "payment_terms"), "notes": optional_text(given["notes"], "notes")}}


def categories(requested):
    """A validated category filter (None keeps every category), as a sorted list without duplicates."""
    if requested is None:
        return None
    if not isinstance(requested, (list, tuple)) or not requested:
        raise RfqError("err_categories_invalid")
    return sorted({text(c, "requestable_categories entry") for c in requested})


def _text_list(value, where, what):
    value = value or []
    if not isinstance(value, (list, tuple)) or not all(isinstance(v, str) for v in value):
        raise RfqError("err_not_list_of_text", where=where, what=what)
    return list(value)


def line(raw, n):
    """A validated copy of one BOQ item (a plain dict; unknown keys such as `basis` are ignored)."""
    if not isinstance(raw, dict):
        raise RfqError("err_boq_item_not_object", n=n, got=type(raw).__name__)
    item_id = text(raw.get("item_id"), f"BOQ item {n}: item_id")
    where = f"BOQ item {item_id}"
    spec = raw.get("spec") or {}
    if not isinstance(spec, dict):
        raise RfqError("err_spec_not_object", where=where)
    return {"item_id": item_id, "category": text(raw.get("category"), f"{where}: category"), "description": text(raw.get("description"), f"{where}: description"),
            "unit": text(raw.get("unit"), f"{where}: unit"), "quantity": number_or_none(raw.get("quantity"), f"{where}: quantity"),
            "source": sorted(_text_list(raw.get("source"), where, "source")), "issues": _text_list(raw.get("issues"), where, "issues"), "spec": dict(spec)}


def boq_items(boq):
    """The validated items of a BOQ structure (plain dict with `items`), sorted by item_id; duplicate ids are rejected."""
    if not isinstance(boq, dict) or not isinstance(boq.get("items"), (list, tuple)) or not boq["items"]:
        raise RfqError("err_boq_invalid")
    items = [line(r, n) for n, r in enumerate(boq["items"], start=1)]
    ids = [i["item_id"] for i in items]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise RfqError("err_duplicate_boq_ids", ids=', '.join(duplicates))
    return sorted(items, key=lambda i: i["item_id"])


def _candidate(raw, where):
    if not isinstance(raw, dict):
        raise RfqError("err_candidate_not_object", where=where)
    out = {"manufacturer": text(raw.get("manufacturer"), f"{where}: manufacturer"), "product_id": text(raw.get("product_id"), f"{where}: product_id")}
    out.update({k: raw.get(k) for k in ("family", "source", "catalog_status")})
    return out


def _sheet(raw, n):
    if not isinstance(raw, dict):
        raise RfqError("err_datasheet_not_object", n=n, got=type(raw).__name__)
    item_id = text(raw.get("item_id"), f"datasheet {n}: item_id")
    where = f"datasheet {item_id}"
    if raw.get("kind") not in DATASHEET_KINDS:
        raise RfqError("err_kind_invalid", where=where, allowed=', '.join(DATASHEET_KINDS), got=raw.get('kind'))
    if not isinstance(raw.get("requirement"), dict) or not isinstance(raw.get("candidates"), (list, tuple)):
        raise RfqError("err_requirement_invalid", where=where)
    return {"item_id": item_id, "kind": raw["kind"], "requirement": dict(raw["requirement"]), "candidates": [_candidate(c, where) for c in raw["candidates"]]}


def datasheets(ds):
    """The validated datasheet records of an `epc_datasheets` structure (plain dict with `datasheets`), or an empty list for None."""
    if ds is None:
        return []
    if not isinstance(ds, dict) or not isinstance(ds.get("datasheets"), (list, tuple)):
        raise RfqError("err_datasheets_invalid")
    return [_sheet(r, n) for n, r in enumerate(ds["datasheets"], start=1)]
