"""The design-basis document: sections of items, built by copying the profile, criteria, assumptions and requirements and by reading the engines' limits."""
import copy

from epc_design_basis import limits
from epc_design_basis.errors import DesignBasisError

CRITICAL = (("earthing_system", "earthing scheme (TT, TN or IT)"), ("short_circuit_level", "available short-circuit level with its origin"))
STATUSES = ("verified", "pending review", "rejected")
STATUS = "draft"
NOTE = ("The limits in the design-criteria section are the values the calculation engines will apply, read from the engines' own data, each with its source and its "
        "norm-register status. A status of pending review means that no person has verified the value against the standard yet. This document is a draft and does not "
        "approve any value.")


def item(key, label, value, unit=None, source=None, review=None):
    return {"key": key, "label": label, "value": copy.deepcopy(value), "unit": unit, "source": source, "review_status": review}


def _section(section_id, title, items):
    return {"id": section_id, "title": title, "items": items}


def _get(data, *path):
    for key in path:
        data = data.get(key) if isinstance(data, dict) else None
    return data


def check_profile(profile):
    """ValueError listing every D24 field missing in the profile (the same field names as the discipline)."""
    if not isinstance(profile, dict):
        raise DesignBasisError("err_profile_not_object")
    supply = profile.get("supply") or {}
    missing = [f"supply.{key} ({label})" for key, label in CRITICAL if supply.get(key) in (None, "", {})]
    if missing:
        raise DesignBasisError("err_d24_missing", missing='; '.join(missing))


def check_norm_status(norm_status):
    if norm_status is None:
        return {}
    if not isinstance(norm_status, dict) or any(v not in STATUSES for v in norm_status.values()):
        raise DesignBasisError("err_norm_status_invalid", allowed=', '.join(STATUSES))
    return dict(norm_status)


def assumptions_of(items):
    out = []
    for n, entry in enumerate(items or [], start=1):
        text, reason = str(entry.get("text", "")).strip(), str(entry.get("reason", "")).strip()
        if not text or not reason:
            raise DesignBasisError("err_assumption_incomplete", n=n)
        out.append({"id": f"A-{n:02d}", "text": text, "reason": reason})
    return out


def insulation_items(rules, norm_status):
    if rules is None:
        return []
    if not isinstance(rules, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in rules.items()):
        raise DesignBasisError("err_insulation_rules_invalid")
    status = limits.review_status((), norm_status)
    return [item(f"insulation_by_role.{role}", f"Insulation for role {role}", rules[role], None, "caller (insulation_rules)", status) for role in sorted(rules)]


def identification(profile):
    where = (("project_code", "Project code", ("project_code",)), ("client_name", "Client", ("client", "name")), ("site_address", "Site", ("site", "address")),
             ("site_country", "Country", ("site", "country")), ("site_installation_type", "Installation type", ("site", "installation_type")), ("language", "Language", ("language",)))
    return _section("identification", "Project identification", [item(k, label, _get(profile, *p), None, "profile." + ".".join(p)) for k, label, p in where])


def supply_section(profile, issues):
    supply = profile.get("supply") or {}
    voltage, level = supply.get("voltage") or {}, supply.get("short_circuit_level") or {}
    if isinstance(level, dict) and not level.get("origin"):
        issues.append("supply.short_circuit_level.origin is missing in the profile")
    items = [item("supply_source", "Supply source", supply.get("source"), None, "profile.supply.source"),
             item("supply_voltage", "Supply voltage", voltage.get("value"), voltage.get("unit"), "profile.supply.voltage"),
             item("earthing_system", "Earthing system", supply.get("earthing_system"), None, "profile.supply.earthing_system"),
             item("short_circuit_level", "Short-circuit level", level.get("value"), level.get("unit"), "profile.supply.short_circuit_level"),
             item("short_circuit_origin", "Origin of the short-circuit level", level.get("origin"), None, "profile.supply.short_circuit_level.origin")]
    return _section("supply", "Supply data", items)


def normative_section(profile):
    norms = profile.get("normative_profile") or {}
    items = [item("jurisdiction", "Jurisdiction", norms.get("jurisdiction"), None, "profile.normative_profile.jurisdiction")]
    revisions = norms.get("revisions") or {}
    items += [item(f"revision.{part}", f"Revision of {part}", revisions[part], None, f"profile.normative_profile.revisions.{part}") for part in revisions]
    return _section("normative_profile", "Normative profile", items)


def criteria_of(profile, criteria):
    base, extra = profile.get("criteria") or {}, criteria or {}
    return {"set": extra.get("set") or base.get("set"), "exceptions": list(base.get("exceptions") or []) + list(extra.get("exceptions") or [])}


def criteria_section(profile, criteria, norm_status, insulation_rules, issues, records):
    chosen = criteria_of(profile, criteria)
    items = [item("criteria_set", "Design criteria set", chosen["set"], None, "profile.criteria.set"),
             item("criteria_exceptions", "Exceptions to the criteria", chosen["exceptions"], None, "profile.criteria.exceptions")]
    found, problems, ids = limits.read_limits(profile.get("supply") or {}, norm_status)
    issues.extend(problems)
    records.extend(r for r in ids if r not in records)
    return _section("design_criteria", "Design criteria and limits", items + found + insulation_items(insulation_rules, norm_status))


def assumptions_section(assumptions):
    return _section("assumptions", "Assumptions", [item(a["id"], "Assumption", a["text"], None, a["reason"]) for a in assumptions])


def requirements_section(requirements):
    rows = list((requirements or {}).get("items") or [])
    items = [dict(item(r.get("id"), "Requirement", r.get("text"), None, r.get("source")), status=r.get("status")) for r in rows]
    return _section("requirements", "Requirements and open items", items), [r.get("id") for r in rows if r.get("status") == "open"]


def build_design_basis_document(profile, *, criteria=None, assumptions=None, requirements=None, norm_status=None, insulation_rules=None):
    """The design-basis document as a draft dict {sections, issues, assumptions, open_items, norm_records, status}; ValueError when D24 data is missing."""
    check_profile(profile)
    status = check_norm_status(norm_status)
    listed = assumptions_of(assumptions)
    issues, records = [], []
    requirement_section, open_items = requirements_section(requirements)
    sections = [identification(profile), supply_section(profile, issues), normative_section(profile),
                criteria_section(profile, criteria, status, insulation_rules, issues, records), assumptions_section(listed), requirement_section,
                _section("values_note", "What the values mean", [item("what_the_values_mean", "Note", NOTE)])]
    return {"sections": sections, "issues": issues, "assumptions": listed, "open_items": open_items, "norm_records": records, "status": STATUS}
