"""The drawings of the photovoltaic plant of stage 10 (and its 3D model, `<name>_pv_model_3d.dxf`, raised from the same layout): layout plan, stringing plan, cabling plan and single-line diagram (ground or assumed-flat roof, from the `layout`) and the roof layout, roof stringing
and roof cabling plans (pitched roof planes, from the `roof` result of `epc_pv.plan_roof`).

The discipline draws nothing: it hands the layout of stage 3 (`outputs["pv"]["layout"]`, from `epc_pv.plan_layout`) and the yield result to `epc_drawing.pv_diagrams.write_all`, then puts every
drawing on the IRAM sheet of the project (`epc_drawing.export.plan_sheet.compose`, the same call the floor plans use). The sheets are written to `<out>/<board>_pv_<drawing>_sheet.dxf`; the drafts stay in
`<run>/pv_drafts/` and are not deliverables. Without the `layout` or the `roof` of the `pv` section there is nothing to draw and the function returns {}.
"""
import copy
from pathlib import Path

from disciplines.electrical_lv.stages.plan_drawings import sheet_options

ENGINE = "cad/drawing"
WRITE = "epc_drawing.pv_diagrams.write_all"
WRITE_ROOF = "epc_drawing.pv_roof.write_all"
COMPOSE = "epc_drawing.export.plan_sheet.compose"


def layout_of(context):
    """(geometry, yield result) from stage 3 when it ran the photovoltaic slice with a layout, else None."""
    res = context.results.get(3)
    pv = res.outputs.get("pv") if res is not None and res.status == "ok" else None
    return (pv["layout"], pv) if pv and pv.get("layout") else None


def roof_of(context):
    """(roof placement, yield result) from stage 3 when it ran the photovoltaic slice with roof planes, else None."""
    res = context.results.get(3)
    pv = res.outputs.get("pv") if res is not None and res.status == "ok" else None
    return (pv["roof"], pv) if pv and pv.get("roof") else None


def _drafts(context, target, name, stamp_date, language, calls):
    """The drafts of the plant: those of the layout (if any) and those of the roof planes (if any)."""
    from disciplines.electrical_lv.stages import engine_calls as EC
    drafts = {}
    found, roof = layout_of(context), roof_of(context)
    if found is not None:
        from epc_drawing import pv_diagrams
        drafts.update(pv_diagrams.write_all(copy.deepcopy(found[0]), found[1], Path(target) / "pv_drafts", f"{name}_pv", language, stamp_date))
        calls.append(EC.record_for("cad/drawing", WRITE))
    if roof is not None:
        from epc_drawing import pv_roof
        drafts.update(pv_roof.write_all(copy.deepcopy(roof[0]), roof[1], Path(target) / "pv_drafts", f"{name}_pv", language, stamp_date))
        calls.append(EC.record_for("cad/drawing", WRITE_ROOF))
    return drafts


def write(context, target, name, stamp_date, language, calls):
    """Writes the PV sheets under `<target>/out`; returns {"pv_sheets": {sheet name: {format, scale}}} or {}."""
    from disciplines.electrical_lv.stages import engine_calls as EC
    drafts = _drafts(context, target, name, stamp_date, language, calls)
    if not drafts:
        return {}
    import epc_drawing.export.plan_sheet as plan_sheet
    fmt, scale = sheet_options(EC.inputs_of(context).get("drawings"))
    request = __import__("json").loads((Path(target) / "titleblock-request.json").read_text(encoding="utf-8"))
    sheets = {}
    for sheet_name, path in sorted(drafts.items()):
        done = plan_sheet.compose(path, request, Path(target) / "out" / f"{sheet_name}_sheet.dxf", fmt, scale, sheet_name)
        sheets[f"{sheet_name}_sheet"] = {"format": done["format"], "scale": done["scale"]}
    calls.append(EC.record_for("cad/drawing", COMPOSE))
    return dict({"pv_sheets": sheets}, **_model3d(context, target, name, stamp_date, calls))


def _model3d(context, target, name, stamp_date, calls):
    """The 3D model of the plant (`epc_drawing.pv_model3d`, one DXF with solid faces) when stage 3 placed tables; it lands in the 3D folder of the transmittal."""
    found = layout_of(context)
    if found is None:
        return {}
    from disciplines.electrical_lv.stages import engine_calls as EC
    from epc_drawing import pv_model3d
    path = pv_model3d.write(copy.deepcopy(found[0]), found[1], Path(target) / "out", f"{name}", stamp_date)
    calls.append(EC.record_for("cad/drawing", "epc_drawing.pv_model3d.write"))
    return {"pv_model_3d": path.name}
