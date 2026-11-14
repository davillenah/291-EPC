"""Input verification (stage 3 entry): cross-checks of the load list against the areas and the stored inputs.

Findings follow docs/harness/seeds/finding.schema.json. The rule id is carried in `clause`
("project criterion IV-nn") and in `evidence`. Nothing is calculated.

  IV-01 the load list has no loads
  IV-02 a load references an area that is not declared
  IV-03 an area references a plan that is not among the inputs
  IV-04 two loads share an id
  IV-05 a plan listed in an area is a .dxf file that cannot be read as a DXF drawing (only checked when the inputs folder is given)
"""

VERIFIER = "input-verifier"


def _finding(n, run_id, rule, field, value, expected, action):
    return {
        "id": f"F-{n:04d}", "run_id": run_id, "verifier": VERIFIER, "severity": "blocking",
        "document": "load_list", "field": field, "value": value, "expected": expected,
        "clause": f"project criterion {rule}", "action": action,
        "evidence": [f"rule {rule}"], "status": "open",
    }


def _area_refs(loads, areas):
    known = {a["id"] for a in areas}
    return [("IV-02", f"loads/{x['id']}/area", x["area"], "a declared area id", "Declare the area or correct the reference.")
            for x in loads if x["area"] not in known]


def _plan_refs(areas, plans):
    return [("IV-03", f"areas/{a['id']}/plan", a["plan"], "a file present in inputs/", "Add the plan to the inputs or correct the path.")
            for a in areas if a.get("plan") and a["plan"] not in plans]


def _duplicates(loads):
    ids = [x["id"] for x in loads]
    return [("IV-04", f"loads/{d}/id", d, "unique load ids", "Give each load its own id.") for d in sorted({i for i in ids if ids.count(i) > 1})]


def _unreadable_plans(areas, inputs_dir):
    """IV-05: a `.dxf` plan that exists but the architecture reader (`epc_arch`) cannot read (the content is looked at, not only the name).

    Other formats are not opened here. A plan shared by several areas is read once."""
    if not inputs_dir:
        return []
    from pathlib import Path

    from epc_arch import ArchError
    from epc_arch.sources import read as read_plan
    bad, out = {}, []
    for a in areas:
        plan = a.get("plan")
        path = Path(inputs_dir) / plan if plan else None
        if not (path and plan.lower().endswith(".dxf") and path.is_file()):
            continue
        if plan not in bad:
            try:
                read_plan(path.read_bytes(), plan)
                bad[plan] = None
            except ArchError as exc:
                bad[plan] = str(exc)
        if bad[plan]:
            out.append(("IV-05", f"areas/{a['id']}/plan", plan, "a readable DXF drawing", f"Replace the plan with a valid DXF ({bad[plan]})."))
    return out


def _raw(loads, areas, plans, inputs_dir=None):
    """(rule, field, value, expected, action) tuples, in a fixed order."""
    empty = [("IV-01", "loads", [], "at least one load", "Add the loads of the installation.")] if not loads else []
    return empty + _area_refs(loads, areas) + _plan_refs(areas, plans) + _duplicates(loads) + _unreadable_plans(areas, inputs_dir)


def verify_inputs(load_list, manifest, run_id="run-0", inputs_dir=None):
    """Findings for a validated load list and the inputs manifest (see intake.hashing.build_manifest)."""
    plans = {entry["path"] for entry in manifest["files"]}
    raw = _raw(load_list["loads"], load_list["areas"], plans, inputs_dir)
    return [_finding(n, run_id, *item) for n, item in enumerate(raw, start=1)]
