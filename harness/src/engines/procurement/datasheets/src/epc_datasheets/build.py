"""Draft equipment datasheet records of one board: pure functions, no I/O.

For each requirement (a protective device or a cable spec derived from the calculation) the record lists the catalog products that satisfy it by
comparison, with the catalog fields copied verbatim. No winner is chosen, no electrical value is calculated, no product data is invented.
"""
from epc_datasheets import catalog as catalog_mod
from epc_datasheets import inputs, match

PENDING = "pending review"
PENDING_REASON = "catalog values are unverified manufacturer data"
NO_CANDIDATE = "no catalog product satisfies the requirement"
PREFIX = {inputs.DEVICE_KIND: "DS-DEV", inputs.CABLE_KIND: "DS-CAB"}
ASSUMPTIONS = (
    "the datasheet records are drafts (D21): every candidate carries the catalog status verbatim and the record stays pending review because catalog values are unverified manufacturer data",
    "no product is chosen: the candidates are all the catalog products that satisfy the requirement by comparison, in the order manufacturer, family, id",
    "a protective-device candidate has the requested type, a rated-current range containing the requested In, and a catalog breaking capacity at a voltage >= the required voltage that is >= the required kA",
    "a requirement the catalog cannot answer (no rated-current or breaking-capacity data) is not satisfied: requirements are never relaxed",
    "poles are compared only when the catalog lists them; otherwise the candidate says `poles` is unconfirmed",
    "a cable candidate must mention the required insulation in its catalog text; the catalog carries no material, section or conductor count, so those stay unconfirmed",
    "the engine reads no file: the catalog is an argument")


def _fmt(value):
    return f"{value:g}"


def _device_requirement(spec, tags, voltage_v):
    return {"kind": inputs.DEVICE_KIND, "device_kind": spec[0], "in_a": spec[1], "poles": spec[2], "breaking_capacity_ka": spec[3],
            "voltage_v": voltage_v, "circuits": sorted(tags)}


def _cable_requirement(spec, tags):
    return {"kind": inputs.CABLE_KIND, "material": spec[0], "insulation": spec[1], "phase_conductors": spec[2], "s_mm2": spec[3], "neutral_mm2": spec[4],
            "pe_mm2": spec[5], "cores": spec[6], "circuits": sorted(tags)}


def _rank(value):
    return -1 if value is None else value


def _text_rank(value):
    return "" if value is None else value


def requirements_from_circuits(circuits, voltage_v=None):
    """The deduplicated requirements of a list of circuits (same shape as the bill-of-quantities engine), sorted, with ids `DS-DEV-001`, `DS-CAB-001`...

    One device requirement per distinct (kind, In, poles, breaking capacity) and one cable requirement per distinct (material, insulation, phase conductors,
    sections), each with the sorted circuit tags. A circuit without any device data gives no device requirement. `voltage_v` (optional, positive) is the
    voltage the breaking capacity must be given at; it is copied to every device requirement, never guessed.
    """
    checked = inputs.circuits(circuits)
    voltage = inputs.number(voltage_v, "voltage_v", True)
    devices, cables = {}, {}
    for c in checked:
        dkey = (c["device_kind"], c["in_a"], c["poles"], c["breaking_capacity_ka"])
        if any(v is not None for v in dkey):
            devices.setdefault(dkey, []).append(c["tag"])
        conductors = 1 if c["phases"] == 1 else 3
        cores = conductors + (c["neutral_mm2"] is not None) + (c["pe_mm2"] is not None)
        cables.setdefault((c["material"], c["insulation"], conductors, c["s_mm2"], c["neutral_mm2"], c["pe_mm2"], cores), []).append(c["tag"])
    out = []
    for n, key in enumerate(sorted(devices, key=lambda k: (_text_rank(k[0]),) + tuple(_rank(v) for v in k[1:])), start=1):
        out.append(dict(_device_requirement(key, devices[key], voltage), item_id=f"{PREFIX[inputs.DEVICE_KIND]}-{n:03d}"))
    for n, key in enumerate(sorted(cables, key=lambda k: (_text_rank(k[0]), _text_rank(k[1])) + tuple(_rank(v) for v in k[2:])), start=1):
        out.append(dict(_cable_requirement(key, cables[key]), item_id=f"{PREFIX[inputs.CABLE_KIND]}-{n:03d}"))
    return out


def _missing(requirement):
    """The fields the matching needs and the requirement does not carry."""
    if requirement["kind"] == inputs.DEVICE_KIND:
        return [f for f in ("device_kind", "in_a") if requirement[f] is None]
    return []


def _requirement_issues(requirement):
    issues = [f"{requirement['item_id']}: missing {f} (nothing to compare)" for f in _missing(requirement)]
    if requirement["kind"] == inputs.DEVICE_KIND:
        if requirement["breaking_capacity_ka"] is None:
            issues.append(f"{requirement['item_id']}: breaking capacity not specified (not compared)")
        elif requirement["voltage_v"] is None:
            issues.append(f"{requirement['item_id']}: voltage not specified (breaking capacity compared at any catalog voltage)")
    elif requirement["insulation"] is None:
        issues.append(f"{requirement['item_id']}: insulation not specified (not compared)")
    return issues


def _candidate(product, found):
    candidate = {"manufacturer": product["manufacturer"], "product_id": product["id"], "category": product["category"]}
    candidate.update({k: product[k] for k in catalog_mod.COPIED if k in product})
    candidate.update({"catalog_status": product["status"], "matched": found["matched"], "unconfirmed": found["unconfirmed"]})
    del candidate["status"]
    return candidate


def _sheet(requirement, catalog_products):
    issues = _requirement_issues(requirement)
    candidates = []
    if not _missing(requirement):
        rule = match.device_match if requirement["kind"] == inputs.DEVICE_KIND else match.cable_match
        for product in catalog_products:
            found = rule(requirement, product)
            if found is not None:
                candidates.append(_candidate(product, found))
    if not candidates:
        issues.append(f"{requirement['item_id']}: {NO_CANDIDATE}")
    return {"item_id": requirement["item_id"], "kind": requirement["kind"], "requirement": requirement, "candidates": candidates, "issues": issues,
            "review_status": PENDING, "review_reason": PENDING_REASON}


def _norm_records(sheets):
    """One entry per (manufacturer, category) catalog file that supplied at least one candidate: the catalog values used, pending review."""
    used = {(c["manufacturer"], c["category"], c["catalog_status"]) for s in sheets for c in s["candidates"]}
    return [{"manufacturer": m, "category": cat, "catalog_status": status, "review_status": PENDING, "reason": PENDING_REASON} for m, cat, status in sorted(used)]


def build_datasheets(board_name, requirements, catalog):
    """The draft datasheet records of a board.

    `requirements`: list of requirement objects (see `requirements_from_circuits`; each has a unique `item_id`). `catalog`: list of manufacturer product
    documents as parsed JSON (see `epc_datasheets.catalog`). Returns {"board", "datasheets": [{item_id, kind, requirement, candidates, issues,
    review_status, review_reason}], "totals": {items, items_without_candidate}, "assumptions", "norm_records", "issues"}; a ValueError names an invalid input.
    """
    inputs.text(board_name, "board_name")
    checked = inputs.requirements(requirements)
    flat = catalog_mod.products(catalog)
    sheets = [_sheet(r, flat) for r in sorted(checked, key=lambda r: r["item_id"])]
    return {"board": board_name, "datasheets": sheets,
            "totals": {"items": len(sheets), "items_without_candidate": sum(1 for s in sheets if not s["candidates"])},
            "assumptions": list(ASSUMPTIONS), "norm_records": _norm_records(sheets), "issues": sorted({i for s in sheets for i in s["issues"]})}


def _requirement_text(r):
    if r["kind"] == inputs.DEVICE_KIND:
        kind = r["device_kind"].upper() if r["device_kind"] else "unspecified-kind"
        bits = [kind, f"{_fmt(r['in_a'])} A" if r["in_a"] is not None else "rated current unspecified",
                f"{r['poles']} poles" if r["poles"] is not None else "poles unspecified",
                f"{_fmt(r['breaking_capacity_ka'])} kA" if r["breaking_capacity_ka"] is not None else "breaking capacity unspecified"]
        if r["voltage_v"] is not None:
            bits.append(f"at {_fmt(r['voltage_v'])} V")
        return ", ".join(bits)
    return (f"{r['material'] or 'material unspecified'} {(r['insulation'] or 'insulation unspecified').upper()} cable "
            f"{r['phase_conductors']}x{_fmt(r['s_mm2'])} mm2 ({r['cores']} cores)")


def render_rows(ds):
    """Flat rows for the document builders (one per candidate; a record without candidate gives one row with empty product columns)."""
    rows = []
    for s in ds["datasheets"]:
        base = {"board": ds["board"], "item_id": s["item_id"], "kind": s["kind"], "requirement": _requirement_text(s["requirement"]),
                "circuits": ", ".join(s["requirement"]["circuits"]), "review_status": s["review_status"], "issue": "; ".join(s["issues"])}
        for c in s["candidates"] or [None]:
            rows.append(dict(base, **({"manufacturer": c["manufacturer"], "family": c["family"], "product_id": c["product_id"], "catalog_status": c["catalog_status"],
                                      "source": c["source"]} if c else {"manufacturer": "", "family": "", "product_id": "", "catalog_status": "", "source": ""})))
    return rows
