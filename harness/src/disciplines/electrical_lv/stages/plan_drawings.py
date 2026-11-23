"""The floor plans of stage 10: for each routed floor, the plan with everything (luminaires, outlets, trays, conduits, circuits) and the lighting plan (luminaires and the runs of the lighting circuits) and, when the engine gave the lux of the cells, the lux map (`luxmap`: the lighting plan over the coloured cells and lines of equal level of `lux_map.py`).

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


def write_floor_plans(routing, out_dir, board, scales=None):
    """Writes `<board>_plan_<floor>.dxf` and `<board>_lighting_<floor>.dxf` for every floor of the routing section; returns the warnings of the engine.
    `scales` ({plan name: N of 1:N}): the scale each plan will be printed at, so its text and symbols are sized for it (see `epc_plan.dxfout.write_dxf`)."""
    import epc_plan.dxfout as dxfout
    warnings, written = [], {}
    for floor, design in sorted(routing.items()):
        backdrop = copy.deepcopy(design.get("backdrop"))
        luxmap = design.get("luxmap")
        drawn = [("plan", routed_document(design), None), ("lighting", lighting_document(design), None)] + ([("luxmap", lighting_document(design), luxmap)] if luxmap else [])
        for stem, doc, lux in drawn:
            path = out_dir / f"{board}_{stem}_{floor}.dxf"
            name = f"{board}_{stem}_{floor}"
            warnings += [f"{floor}: {w}" for w in dxfout.write_dxf(_process(doc), path, backdrop=backdrop, paper_scale=(scales or {}).get(name), luxmap=lux)]
            written[name] = path
    return warnings, written


SHEET_FORMATS = ("A0", "A1", "A2", "A3", "A4")


def sheet_options(given):
    """The format and the scale of the plan sheets from `engine_inputs["drawings"]` (`sheet_format`, `paper_scale`): None for both when not given (the engine takes A1 and the largest scale that fits)."""
    given = given or {}
    fmt, scale = given.get("sheet_format"), given.get("paper_scale")
    if fmt is not None and fmt not in SHEET_FORMATS:
        raise ValueError(f"engine_inputs.drawings.sheet_format: {fmt!r} is not one of {', '.join(SHEET_FORMATS)}")
    if scale is not None and (isinstance(scale, bool) or not isinstance(scale, int) or scale <= 0):
        raise ValueError(f"engine_inputs.drawings.paper_scale: {scale!r} is not a whole number (the N of 1:N)")
    return fmt or "A1", scale


def place_on_sheets(plans, request, fmt, scale):
    """Puts each plan DXF of `plans` ({name: path}) on the IRAM sheet of the project (`epc_drawing.export.plan_sheet.compose`, with `request`, the title block request of stage 10 as data) as `<plan>_sheet.dxf`; returns {name: result}."""
    from epc_drawing.export import plan_sheet
    asked = lambda name: scale.get(name) if isinstance(scale, dict) else scale                                        # noqa: E731 - one scale for all, or one for each plan
    return {name: plan_sheet.compose(path, request, path.with_name(path.stem + "_sheet.dxf"), fmt, asked(name), name) for name, path in sorted(plans.items())}
