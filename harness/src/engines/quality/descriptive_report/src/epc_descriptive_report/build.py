"""The descriptive report: sections of items built by copying values of the design basis and by counting the given circuits (no other arithmetic)."""
import copy
from collections import Counter

STATUS = "draft"
NOT_SPECIFIED = "not specified"
DRAFT_NOTICE = "This document is a draft and cannot be approved for construction while any norm value is unreviewed (D21)."
ASSUMPTIONS = (
    "Counting is the only arithmetic: the numbers of circuits, of circuits by type, by phases, by device kind and by cable specification are counts of the given circuits list.",
    "A cable specification is the combination of material, insulation and phase-conductor section reported for a circuit; a field not reported is shown as 'not specified'.",
    "Values copied from the design basis keep the source and the review status they have there; this report adds no value of its own.",
    "The numbers of the calculation (currents, voltage drops, short-circuit levels per circuit) belong to the calculation report, not to this descriptive report.",
)
IDENTIFICATION = ("project_code", "client_name", "site_address", "site_country", "site_installation_type", "language")
SUPPLY = ("supply_source", "supply_voltage", "earthing_system", "short_circuit_level", "short_circuit_origin")
ORDER = ("object_scope", "supply_earthing", "board_organisation", "cables_installation", "protection_earthing", "standards", "status_limitations")
TITLES = {"object_scope": "Object and scope", "supply_earthing": "Supply and earthing", "board_organisation": "Board organisation",
          "cables_installation": "Cables and installation", "protection_earthing": "Protection and earthing", "standards": "Applicable standards",
          "status_limitations": "Status and limitations of this draft"}
COUNT_SOURCE = "count of the circuits given"


def item(key, label, value, unit=None, source=None, review=None, **extra):
    return dict({"key": key, "label": label, "value": copy.deepcopy(value), "unit": unit, "source": source, "review_status": review}, **extra)


def _section(section_id, items):
    return {"id": section_id, "title": TITLES[section_id], "items": items}


def check_design_basis(design_basis):
    if not isinstance(design_basis, dict) or not isinstance(design_basis.get("sections"), list):
        raise ValueError("design_basis must be a design-basis document (a dict with a list of sections)")


def check_circuits(circuits):
    if not isinstance(circuits, list) or not circuits:
        raise ValueError("circuits must be a non-empty list")
    seen = set()
    for n, row in enumerate(circuits, start=1):
        tag = row.get("tag") if isinstance(row, dict) else None
        if not isinstance(tag, str) or not tag.strip():
            raise ValueError(f"circuit {n}: a tag (non-empty text) is required")
        if tag in seen:
            raise ValueError(f"circuit {n}: duplicate tag {tag}")
        seen.add(tag)
        section = row.get("s_mm2")
        if section is not None and (isinstance(section, bool) or not isinstance(section, (int, float)) or section <= 0):
            raise ValueError(f"circuit {tag}: s_mm2 must be a number greater than zero")


def check_optional(terminals, boq, pending, unreviewed):
    for name, value in (("terminals", terminals), ("boq", boq)):
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"{name} must be a dict when given")
    if pending is not None and (not isinstance(pending, list) or not all(isinstance(p, dict) and p.get("name") for p in pending)):
        raise ValueError("pending_documents must be a list of dicts with a name")
    if unreviewed is not None and (isinstance(unreviewed, bool) or not isinstance(unreviewed, int) or unreviewed < 0):
        raise ValueError("unreviewed_norm_records must be a whole number, zero or more")


def design_basis_items(design_basis):
    """{section id: {item key: item}} of the design-basis document."""
    out = {}
    for section in design_basis["sections"]:
        if isinstance(section, dict) and isinstance(section.get("items"), list):
            out[section.get("id")] = {i.get("key"): i for i in section["items"] if isinstance(i, dict)}
    return out


def copied(db, section, issues, keys=None, prefix=None):
    """Items copied from a design-basis section: the given keys, or every key with the prefix (sorted). A missing section or key is an issue."""
    found = db.get(section)
    if found is None:
        issues.append(f"design basis: section {section} not found")
        return []
    chosen = [k for k in keys if k in found] if keys is not None else sorted(k for k in found if str(k).startswith(prefix))
    issues.extend(f"design basis: item {section}.{k} not found" for k in (keys or ()) if k not in found)
    return [item(k, found[k].get("label") or k, found[k].get("value"), found[k].get("unit"), f"design_basis.{section}.{k}", found[k].get("review_status")) for k in chosen]


def _count_items(prefix, label, counter, unit="circuits"):
    return [item(f"{prefix}.{name}", f"{label} {name}", counter[name], unit, COUNT_SOURCE) for name in sorted(counter, key=str)]


def organisation(circuits):
    by_type = Counter(c.get("kind") or NOT_SPECIFIED for c in circuits)
    by_phases = Counter(str(c["phases"]) if c.get("phases") is not None else NOT_SPECIFIED for c in circuits)
    return ([item("circuits_total", "Circuits", len(circuits), "circuits", COUNT_SOURCE)] + _count_items("circuits_by_type", "Circuits of type", by_type)
            + _count_items("circuits_by_phases", "Circuits with phases", by_phases))


def _spec(circuit):
    section = circuit.get("s_mm2")
    return (circuit.get("material") or NOT_SPECIFIED, circuit.get("insulation") or NOT_SPECIFIED, "" if section is None else f"{section:g}")


def cable_specs(circuits):
    """One item per distinct (material, insulation, section), value = number of circuits with it."""
    counts = Counter(_spec(c) for c in circuits)
    out = [item("cable_specs_distinct", "Distinct cable specifications", len(counts), "specifications", COUNT_SOURCE)]
    for key in sorted(counts):
        material, insulation, section = key
        out.append(item("cable_spec." + "|".join(key), f"{material} / {insulation} / {section or NOT_SPECIFIED}", counts[key], "circuits", COUNT_SOURCE,
                        spec={"material": material, "insulation": insulation, "section": section or None, "section_unit": "mm2" if section else None}))
    return out


def optional_counts(terminals, boq, issues):
    out = []
    if terminals is None:
        issues.append("not provided: terminals")
    else:
        totals = terminals.get("totals", terminals)
        out.append(item("terminals_total", "Terminals in the terminal-block list", totals.get("terminals"), "terminals", "terminal-block list totals"))
    if boq is None:
        issues.append("not provided: boq")
    else:
        totals = boq.get("totals") or {}
        out += [item("boq_lines", "Lines of the bill of quantities", totals.get("lines"), "lines", "boq.totals.lines"),
                item("boq_devices", "Protective devices in the bill of quantities", totals.get("devices"), "devices", "boq.totals.devices"),
                item("boq_cable_m", "Cable length in the bill of quantities", totals.get("cable_m"), "m", "boq.totals.cable_m")]
    return out


def protection(circuits, db, issues):
    kinds = Counter(c.get("device_kind") or NOT_SPECIFIED for c in circuits)
    earthing = copied(db, "supply", issues, keys=("earthing_system",))
    return _count_items("protective_device", "Circuits protected by", kinds) + earthing + copied(db, "design_criteria", [], prefix="disconnection_time.")


def standards(db, issues):
    return copied(db, "normative_profile", issues, keys=("jurisdiction",)) + copied(db, "normative_profile", [], prefix="revision.") \
        + copied(db, "design_criteria", [], keys=("criteria_set",))


def status_items(design_basis, pending, unreviewed, issues):
    out = [item("draft_notice", "Status of this document", DRAFT_NOTICE, None, "D21")]
    if pending is None:
        issues.append("not provided: pending_documents")
    else:
        out.append(item("pending_documents_total", "Pending documents", len(pending), "documents", "count of the pending documents given"))
        out += [item("pending." + p["name"], f"Pending document {p['name']}", p.get("reason") or p.get("status"), None, "pending_documents") for p in pending]
    if unreviewed is None:
        issues.append("not provided: unreviewed_norm_records")
    else:
        out.append(item("unreviewed_norm_records", "Norm records not reviewed", unreviewed, "records", "unreviewed_norm_records"))
    if isinstance(design_basis.get("open_items"), list):
        out.append(item("open_requirements", "Open requirements of the design basis", len(design_basis["open_items"]), "requirements", "count of design_basis.open_items"))
    return out


def build_descriptive_report(design_basis, circuits, *, terminals=None, boq=None, pending_documents=None, unreviewed_norm_records=None):
    """The descriptive report as a draft dict {sections, issues, assumptions, norm_records, status}; ValueError when the design basis or the circuits are invalid."""
    check_design_basis(design_basis)
    check_circuits(circuits)
    check_optional(terminals, boq, pending_documents, unreviewed_norm_records)
    db, issues = design_basis_items(design_basis), []
    items = {"object_scope": copied(db, "identification", issues, keys=IDENTIFICATION),
             "supply_earthing": copied(db, "supply", issues, keys=SUPPLY),
             "board_organisation": organisation(circuits),
             "cables_installation": cable_specs(circuits) + optional_counts(terminals, boq, issues),
             "protection_earthing": protection(circuits, db, issues),
             "standards": standards(db, issues),
             "status_limitations": status_items(design_basis, pending_documents, unreviewed_norm_records, issues)}
    return {"sections": [_section(s, items[s]) for s in ORDER], "issues": issues, "assumptions": list(ASSUMPTIONS), "norm_records": [], "status": STATUS}
