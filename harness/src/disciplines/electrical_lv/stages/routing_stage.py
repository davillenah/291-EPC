"""Slice 18 of stage 3 (runs and circuits of the floors), optional.

The discipline measures nothing: with a `routing` section in `context.engine_inputs` (the design of each floor that `intake/building.py` derived from `engine_inputs.building` with
`epc_plan.design`: the plan document with its trays and conduits, and the circuits proposed over them) the stage hands each floor to `epc_plan.core.process` again, with the circuits
assigned, and returns what comes back: the route of each circuit, the schedule of trays and conduits and the engine warnings.

  no `routing` section   the slice is not available and the stage goes on without it (`optional`, see `grouped.py`)
  valid section          `ok`: per floor the circuits, the routes and the schedule of the engine, one engine call, a `major` finding for a circuit the runs do not reach, for a route whose
                         moment length is no longer the one the loads were derived with, and for a branch-circuit load of the load list whose length is not the riser plus that moment length
                         or whose power is not the one of its circuit; one `note` finding per warning
"""
import copy

from disciplines.electrical_lv.stages import engine_calls as EC
from disciplines.electrical_lv.stages.base import Stage, StageInputError, engine_finding

ENGINE = "cad/plan"
FUNCTION = "epc_plan.core.process"
TOLERANCE_M = 0.01
NOT_PROVIDED = "routing inputs not provided"


def routed_document(design):
    """The plan document of a floor with each circuit assigned to its loads and routed from the board to its last load."""
    wiring = design["wiring"]
    doc = copy.deepcopy(design["document"])
    for node in doc["nodes"]:
        if node["id"] in wiring["assignments"]:
            node["circuit"] = wiring["assignments"][node["id"]]
    doc["circuits"] = [{"tag": c["tag"], "from": c["from"], "to": c["to"], "via": [], "ternas": c.get("ternas", 1)} for c in wiring["circuits"]]
    return doc


def _process(floor, design):
    import epc_plan.core as core
    try:
        return core.process(routed_document(design))
    except core.PlanError as exc:
        raise StageInputError([f"floor {floor}: {exc}"]) from exc


def _circuit_checks(floor, tag, c, design, route, loads):
    """[(item, flag, value, expected)] of one branch circuit: reached, route length as recorded, and its load (length riser + moments, power)."""
    item, out = f"{floor}/{tag}", []
    if not route["found"]:
        out.append((item, "reached", False, True))
    moment = route.get("moment_length_m", 0.0)
    if abs(moment - c["moment_m"]) > TOLERANCE_M:
        out.append((item, "moment_length_m", moment, c["moment_m"]))
    load = loads.get(c["load"])
    if load is None:
        return out + [(c["load"], "in_load_list", False, True)]
    expected = round(design["riser_m"][c["part"]] + moment, 3)
    if abs(load["length"]["value"] - expected) > TOLERANCE_M:
        out.append((c["load"], "length", load["length"]["value"], expected))
    if load["power"] != {"value": c["power"], "unit": c["unit"]}:
        out.append((c["load"], "power", load["power"]["value"], c["power"]))
    return out


def _checks(floor, design, done, loads):
    """[(item, flag, value, expected)] of the checks of a floor: for every branch circuit the route and its load."""
    return [check for tag, c in design["circuits"].items() for check in _circuit_checks(floor, tag, c, design, done["circuits"][tag], loads)]


def _section(context):
    section = (context.engine_inputs or {}).get("routing")
    if section is None:
        return None
    if not isinstance(section, dict) or not section or not all(isinstance(d, dict) and {"document", "wiring", "riser_m", "circuits"} <= set(d) for d in section.values()):
        raise StageInputError(["must be an object {floor id: design of the floor} as derived from the building section"])
    return section


class RoutingStage(Stage):
    wired = True
    wiring_task = "MIG-41"
    optional = True      # without its inputs the grouped stage skips it instead of ending as not_available

    def execute(self, context):
        section = _section(context)
        if section is None:
            return self.result("not_available", message=NOT_PROVIDED, reason="no_routing_inputs")
        loads = {x["id"]: x for x in (context.loads or {}).get("loads") or []}
        floors, checks, warnings = {}, [], []
        for floor, design in section.items():
            done = _process(floor, design)
            checks += _checks(floor, design, done, loads)
            warnings += [f"{floor}: {w}" for w in done["warnings"] + design.get("warnings", [])]
            floors[floor] = {"circuits": done["circuits"], "schedule": done["schedule"], "proposed": [dict(copy.deepcopy(c), load=design["circuits"][c["tag"]]["load"]) for c in design["wiring"]["circuits"]],
                             "assignments": copy.deepcopy(design["wiring"]["assignments"])}
        run_id, slug = context.pipeline_run_id, self.spec.slug
        findings = [engine_finding(n, run_id, slug, item, flag, value, expected) for n, (item, flag, value, expected) in enumerate(checks, start=1)]
        findings += [{"id": f"F-{len(findings) + n:04d}", "run_id": run_id, "verifier": "calc-check", "severity": "note", "document": slug, "field": "warning", "value": w,
                      "expected": "reviewed by the engineer of record", "clause": "engine warning", "action": "Review the warning or correct the input.",
                      "evidence": [f"engine {FUNCTION}"], "status": "open"} for n, w in enumerate(warnings, start=1)]
        circuits = sum(len(f["circuits"]) for f in floors.values())
        return self.result("ok", outputs={"floors": floors}, findings=findings, engine_calls=[EC.record_for(ENGINE, FUNCTION)],
                           message=f"{len(floors)} floor(s), {circuits} circuit(s) routed (draft)")
