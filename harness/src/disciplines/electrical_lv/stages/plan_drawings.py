"""The floor plans of stage 10: for each routed floor, the plan with everything (luminaires, outlets, trays, conduits, circuits) and the lighting plan (luminaires and the runs of the lighting circuits).

The discipline draws nothing: it hands each floor document to `epc_plan.core.process` and the result to `epc_plan.dxfout.write_dxf` (with the walls and room names of the architecture under it).
The lighting plan is the same floor with the outlets and the circuits of the receptacles taken out, and only the lines that the engine says carry a lighting circuit.
"""
import copy

from disciplines.electrical_lv.stages.routing_stage import routed_document

ENGINE = "cad/plan"
FUNCTION = "epc_plan.dxfout.write_dxf"
LIGHTING_KINDS = ("TB", "LU", "LE")


def _process(doc):
    import epc_plan.core as core
    return core.process(doc)


def _lighting_lines(design, tags):
    """Ids of the lines the engine routes the circuits `tags` over."""
    circuits = _process(routed_document(design))["circuits"]
    return {line for tag in tags for line in circuits[tag]["lines"]}


def lighting_document(design):
    """The floor document reduced to the lighting: its luminaires and board, its circuits and the lines the engine routes them over."""
    tags = {c["tag"] for c in design["wiring"]["circuits"] if c["family"].startswith("I")}
    keep = _lighting_lines(design, tags)
    doc = routed_document(design)
    doc["nodes"] = [n for n in doc["nodes"] if n["kind"] in LIGHTING_KINDS]
    doc["circuits"] = [c for c in doc["circuits"] if c["tag"] in tags]
    doc["lines"] = [ln for ln in doc.get("lines", []) if ln["id"] in keep]
    return doc


def write_floor_plans(routing, out_dir, board):
    """Writes `<board>_plan_<floor>.dxf` and `<board>_lighting_<floor>.dxf` for every floor of the routing section; returns the warnings of the engine."""
    import epc_plan.dxfout as dxfout
    warnings = []
    for floor, design in sorted(routing.items()):
        backdrop = copy.deepcopy(design.get("backdrop"))
        for stem, doc in (("plan", routed_document(design)), ("lighting", lighting_document(design))):
            warnings += [f"{floor}: {w}" for w in dxfout.write_dxf(_process(doc), out_dir / f"{board}_{stem}_{floor}.dxf", backdrop=backdrop)]
    return warnings
