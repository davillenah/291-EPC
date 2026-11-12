"""Draft request for quotation (pedido de cotizacion) of one board: pure functions, no I/O, no data tables.

The engine lists what is requested (quantity, unit, description), the technical references (the datasheet candidates, copied verbatim) and EMPTY response
fields for the supplier. It never sets a price or any other commercial value: those are the caller's explicit terms or the supplier's answer.
"""
import hashlib
import json

from epc_rfq import inputs

RESPONSE_FIELDS = ("unit_price", "delivery_days", "brand_offered", "remarks")
FIXED_COLUMNS = ("line_no", "item_id", "description", "unit", "quantity")
SPEC_KEYS = {"protective_device": ("kind", "in_a", "poles", "breaking_capacity_ka"),
             "cable": ("material", "insulation", "phase_conductors", "s_mm2", "neutral_mm2", "pe_mm2", "cores")}
REQUIREMENT_KEYS = {"protective_device": ("device_kind", "in_a", "poles", "breaking_capacity_ka"), "cable": SPEC_KEYS["cable"]}
ASSUMPTIONS = (
    "the request is a draft (D21): it is a document, nothing is sent and no supplier is contacted by this engine",
    "the commercial terms (suppliers, currency, response deadline, delivery site, validity, payment terms) are explicit inputs of the caller; none has a default",
    "the engine sets no price and no commercial value: every supplier response field of every line is left empty",
    "the requested quantity, unit and description of each line are copied from the bill of quantities; nothing is recalculated",
    "the acceptable references of a line are the datasheet candidates whose requirement equals the line specification, copied verbatim with their catalog status; they are not a selection",
    "a line without quantity or with open issues in the bill of quantities is carried and flagged incomplete: it is never dropped",
    "the request identifier is derived from the board name and the supplier list only (no clock, no random value)")


def _identifier(board_name, supplier_list):
    canonical = json.dumps({"board": board_name, "suppliers": supplier_list}, sort_keys=True, ensure_ascii=False)
    return "RFQ-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12].upper()


def _line_key(item):
    keys = SPEC_KEYS.get(item["category"])
    return None if keys is None else (item["category"],) + tuple(item["spec"].get(k) for k in keys)


def _sheet_key(sheet):
    return (sheet["kind"],) + tuple(sheet["requirement"].get(k) for k in REQUIREMENT_KEYS[sheet["kind"]])


def _index(sheets):
    found = {}
    for sheet in sheets:
        found.setdefault(_sheet_key(sheet), []).append(sheet)
    return found


def _references(item, index):
    """The acceptable references of a line: unique (manufacturer, product) candidates of the matching datasheets, verbatim, sorted."""
    key = _line_key(item)
    unique = {}
    for sheet in index.get(key, []) if key else []:
        for c in sheet["candidates"]:
            unique.setdefault((c["manufacturer"], c["product_id"]), dict(c, datasheet_item_id=sheet["item_id"]))
    return sorted(unique.values(), key=lambda r: (r["manufacturer"], r["family"] or "", r["product_id"]))


def _incomplete(item):
    cable_gap = item["category"] == "cable" and any(item["spec"].get(k) is None for k in ("material", "insulation"))
    return item["quantity"] is None or bool(item["issues"]) or cable_gap


def _lines(items, index):
    out = []
    for n, item in enumerate(items, start=1):
        out.append({"line_no": n, "item_id": item["item_id"], "category": item["category"], "description": item["description"], "unit": item["unit"],
                    "quantity": item["quantity"], "source": item["source"], "spec": item["spec"], "references": _references(item, index),
                    "incomplete": _incomplete(item), "issues": list(item["issues"]), "response": dict.fromkeys(RESPONSE_FIELDS)})
    return out


def _filtered(items, requested):
    return items if requested is None else [i for i in items if i["category"] in requested]


def _issues(lines, items, requested, with_datasheets):
    found = [f"{i['item_id']}: {text}" for i in lines for text in i["issues"]]
    found += [f"{i['item_id']}: no quantity (line carried, incomplete)" for i in lines if i["quantity"] is None]
    if with_datasheets:
        found += [f"{i['item_id']}: no acceptable reference in the datasheets" for i in lines if i["category"] in SPEC_KEYS and not i["references"]]
    present = {i["category"] for i in items}
    found += [f"requestable category {c} is not in the bill of quantities" for c in (requested or []) if c not in present]
    return sorted(set(found))


def _template(supplier_list, lines):
    names = [s["name"] for s in supplier_list]
    columns = list(FIXED_COLUMNS) + [f"{n}: {f}" for n in names for f in RESPONSE_FIELDS]
    rows = [{"line_no": ln["line_no"], "item_id": ln["item_id"], "quotes": {n: dict.fromkeys(RESPONSE_FIELDS) for n in names}} for ln in lines]
    return {"suppliers": names, "response_fields": list(RESPONSE_FIELDS), "columns": columns, "rows": rows}


def build_rfq(board_name, boq, *, suppliers=None, currency=None, response_deadline=None, delivery_site=None, validity_days=None, payment_terms=None,
              notes=None, datasheets=None, requestable_categories=None):
    """The draft request for quotation of a board.

    `boq`: the structure of `epc_boq.build_boq` as a plain dict (`items`: item_id, category, description, unit, quantity, source, issues, spec).
    REQUIRED commercial terms, with no defaults (a ValueError lists every missing one): `suppliers` (list of {name, contact?}), `currency` (text),
    `response_deadline` (ISO date YYYY-MM-DD), `delivery_site` (text), `validity_days` (positive whole number). Optional: `payment_terms`, `notes`,
    `datasheets` (the structure of `epc_datasheets.build_datasheets` as a plain dict) and `requestable_categories` (category filter; default all).
    Returns {"rfq_id", "board", "issued_for", "terms", "requestable_categories", "lines", "totals", "comparison_template", "assumptions", "norm_records",
    "issues"}; a ValueError names an invalid input.
    """
    inputs.text(board_name, "board_name")
    given = {"suppliers": suppliers, "currency": currency, "response_deadline": response_deadline, "delivery_site": delivery_site,
             "validity_days": validity_days, "payment_terms": payment_terms, "notes": notes}
    checked = inputs.terms(given)
    requested = inputs.categories(requestable_categories)
    items = inputs.boq_items(boq)
    sheets = inputs.datasheets(datasheets)
    chosen = _filtered(items, requested)
    if not chosen:
        raise ValueError("no bill-of-quantities line is requestable with the given categories")
    lines = _lines(chosen, _index(sheets))
    supplier_list = checked["suppliers"]
    return {"rfq_id": _identifier(board_name, [s["name"] for s in supplier_list]), "board": board_name, "issued_for": supplier_list, "terms": checked["terms"],
            "requestable_categories": sorted({i["category"] for i in chosen}), "lines": lines,
            "totals": {"lines": len(lines), "incomplete_lines": sum(1 for ln in lines if ln["incomplete"])},
            "comparison_template": _template(supplier_list, lines), "assumptions": list(ASSUMPTIONS), "norm_records": [],
            "issues": _issues(lines, items, requested, datasheets is not None)}


def reference_text(ref):
    name = " ".join(p for p in (ref["manufacturer"], ref["family"]) if p)
    extra = [x for x in (ref["catalog_status"], ref["source"]) if x]
    return f"{name} ({ref['product_id']})" + (f" [{'; '.join(extra)}]" if extra else "")


def render_rows(rfq):
    """Flat rows: one per line, in line order. Fixed columns, the references as one text, `incomplete`, `issue`, and one blank column per
    (supplier, response field) named like `comparison_template["columns"]` (`<supplier>: unit_price`...). No file is written."""
    blank = rfq["comparison_template"]["columns"][len(FIXED_COLUMNS):]
    rows = []
    for ln in rfq["lines"]:
        row = {"rfq_id": rfq["rfq_id"], "board": rfq["board"], "line_no": ln["line_no"], "item_id": ln["item_id"], "category": ln["category"],
               "description": ln["description"], "unit": ln["unit"], "quantity": ln["quantity"],
               "references": "; ".join(reference_text(r) for r in ln["references"]), "incomplete": ln["incomplete"], "issue": "; ".join(ln["issues"])}
        row.update(dict.fromkeys(blank, ""))
        rows.append(row)
    return rows
