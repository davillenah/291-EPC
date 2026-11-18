"""The drawings of the photovoltaic plant of stage 10: layout plan, stringing plan, cabling plan and single-line diagram.

The discipline draws nothing: it hands the layout of stage 3 (`outputs["pv"]["layout"]`, from `epc_pv.plan_layout`) and the yield result to `epc_drawing.pv_diagrams.write_all`, then puts every
drawing on the IRAM sheet of the project (`epc_drawing.export.plan_sheet.compose`, the same call the floor plans use). The sheets are written to `<out>/<board>_pv_<drawing>_sheet.dxf`; the drafts stay in
`<run>/pv_drafts/` and are not deliverables. Without the `layout` of the `pv` section there is nothing to draw and the function returns {}.
"""
import copy
from pathlib import Path

from disciplines.electrical_lv.stages.plan_drawings import sheet_options

ENGINE = "cad/drawing"
WRITE = "epc_drawing.pv_diagrams.write_all"
COMPOSE = "epc_drawing.export.plan_sheet.compose"


def layout_of(context):
    """(geometry, yield result) from stage 3 when it ran the photovoltaic slice with a layout, else None."""
    res = context.results.get(3)
    pv = res.outputs.get("pv") if res is not None and res.status == "ok" else None
    return (pv["layout"], pv) if pv and pv.get("layout") else None


def write(context, target, name, stamp_date, language, calls):
    """Writes the PV sheets under `<target>/out`; returns {"pv_sheets": {sheet name: {format, scale}}} or {}."""
    from disciplines.electrical_lv.stages import engine_calls as EC
    found = layout_of(context)
    if found is None:
        return {}
    import epc_drawing.export.plan_sheet as plan_sheet
    from epc_drawing import pv_diagrams
    geometry, result = found
    fmt, scale = sheet_options(EC.inputs_of(context).get("drawings"))
    drafts = pv_diagrams.write_all(copy.deepcopy(geometry), result, Path(target) / "pv_drafts", f"{name}_pv", language, stamp_date)
    request = __import__("json").loads((Path(target) / "titleblock-request.json").read_text(encoding="utf-8"))
    sheets = {}
    for sheet_name, path in sorted(drafts.items()):
        done = plan_sheet.compose(path, request, Path(target) / "out" / f"{sheet_name}_sheet.dxf", fmt, scale, sheet_name)
        sheets[f"{sheet_name}_sheet"] = {"format": done["format"], "scale": done["scale"]}
    calls += [EC.record_for("cad/drawing", WRITE), EC.record_for("cad/drawing", COMPOSE)]
    return {"pv_sheets": sheets}
