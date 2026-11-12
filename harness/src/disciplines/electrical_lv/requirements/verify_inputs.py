"""Input verification (stage 3 entry): cross-checks of the load list against the areas and the stored inputs.

Findings follow docs/harness/seeds/finding.schema.json. The rule id is carried in `clause`
("project criterion IV-nn") and in `evidence`. Nothing is calculated.

  IV-01 the load list has no loads
  IV-02 a load references an area that is not declared
  IV-03 an area references a plan that is not among the inputs
  IV-04 two loads share an id
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


def _raw(loads, areas, plans):
    """(rule, field, value, expected, action) tuples, in a fixed order."""
    empty = [("IV-01", "loads", [], "at least one load", "Add the loads of the installation.")] if not loads else []
    return empty + _area_refs(loads, areas) + _plan_refs(areas, plans) + _duplicates(loads)


def verify_inputs(load_list, manifest, run_id="run-0"):
    """Findings for a validated load list and the inputs manifest (see intake.hashing.build_manifest)."""
    plans = {entry["path"] for entry in manifest["files"]}
    raw = _raw(load_list["loads"], load_list["areas"], plans)
    return [_finding(n, run_id, *item) for n, item in enumerate(raw, start=1)]
