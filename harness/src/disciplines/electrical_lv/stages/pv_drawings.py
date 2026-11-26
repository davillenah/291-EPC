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
WRITE_DETAIL = "epc_drawing.pv_details.write"
WRITE_CHARTS = "epc_drawing.pv_charts.render"
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
    """The drafts of the plant: those of the layout (if any) and those of the roof planes (if any), drawn by one call of `epc_drawing.draw_pv` (OPT-02)."""
    from disciplines.electrical_lv.stages import engine_calls as EC
    from epc_drawing import PvDrawInput, draw_pv
    found, roof = layout_of(context), roof_of(context)
    if found is None and roof is None:
        return {}
    parts = equipment_parts(found[0]) if found is not None else roof_parts(roof[0])
    result = (found or roof)[1]
    charts = result.get("charts") or {}
    disk = refine_disk(charts["disk"]) if charts.get("disk") else None
    drafts, ran = draw_pv(PvDrawInput(result=result, layout=found[0] if found else None, roof=roof[0] if roof else None, parts=parts, disk=disk, abacus=charts.get("abacus"), language=language, stamp_date=stamp_date), target, name)
    records = {"pv_diagrams.write_all": WRITE, "pv_roof.write_all": WRITE_ROOF, "pv_details.write": WRITE_DETAIL, "pv_charts.render": WRITE_CHARTS}
    calls.extend(EC.record_for("cad/drawing", records[r]) for r in ran)
    return drafts


def refine_disk(disk):
    """The coarse disk of stage 3 on the fine grid the drawing needs (bilinear, `epc_pv.disk.refine`)."""
    from epc_pv import disk as pv_disk
    return pv_disk.refine(disk)


def roof_parts(roof):
    """The equipment records of a roof plant for the detail sheet: the module format with the outline the planes use (`{}` when no record has it)."""
    from epc_pv import equipment
    module = (roof["planes"][0] or {}).get("module") or {}
    outline = sorted((module.get("width_m", 0) * 1000.0, module.get("depth_m", 0) * 1000.0), reverse=True)
    record = equipment.module_format(outline) if all(outline) else None
    return {"module": record} if record else {}


def write(context, target, name, stamp_date, language, calls):
    """Writes the PV sheets under `<target>/out`; returns {"pv_sheets": {sheet name: {format, scale}}} or {}."""
    from disciplines.electrical_lv.stages import engine_calls as EC
    drafts = _drafts(context, target, name, stamp_date, language, calls)
    if not drafts:
        return {}
    import epc_drawing.export.plan_sheet as plan_sheet
    fmt, scale = sheet_options(EC.inputs_of(context).get("drawings"))
    request = EC.titleblock_request(context, target)
    sheets = {}
    for sheet_name, path in sorted(drafts.items()):
        done = plan_sheet.compose(path, request, Path(target) / "out" / f"{sheet_name}_sheet.dxf", fmt, scale, sheet_name)
        sheets[f"{sheet_name}_sheet"] = {"format": done["format"], "scale": done["scale"]}
    calls.append(EC.record_for("cad/drawing", COMPOSE))
    return dict({"pv_sheets": sheets}, **_model3d(context, target, name, stamp_date, calls))


def equipment_parts(geometry):
    """The equipment records for the 3D detail, `{"module": record, "inverters": {inverter id: record}}`, from the ids the layout carries (`geometry["equipment"]`); {} without them. A missing record means the plain box."""
    ids = geometry.get("equipment")
    if not ids:
        return {}
    from epc_pv import equipment
    modules = {r["id"]: r for r in equipment.module_formats()}
    records = {r["id"]: r for r in equipment.inverter_records()}
    per_array = ids.get("inverter_records") or {}
    structure = (geometry.get("foundation") or {}).get("structure_id")
    return {"module": modules.get(ids.get("module_format")), "structure": next((r for r in equipment.structures() if r["id"] == structure), None),
            "inverters": {i["id"]: records.get(per_array.get(i.get("array"))) for i in geometry.get("inverters", [])}}


# Size of the 3D model, measured on simulated plants: one face set per module took 206 MB of DXF and 2 minutes at 16 128 modules, 939 MB and 10 minutes (7 GB) at 73 680, and ran out of memory (14 GB) at
# 307 440. Up to MODEL3D_SINGLE_MAX_MODULES the model is one DXF; above, it is written as parts (table and inverter blocks, one DXF per sector of at most `epc_drawing.pv_model3d.SECTOR_MODULES` modules,
# and a common one) and a master DXF that attaches them, so no step holds the plant in memory. A software limit, not a norm value.
MODEL3D_SINGLE_MAX_MODULES = 20000
MODEL3D_PARTS = {"en": "The 3D model is written in {n} sector part(s) plus a common part (ground, fence, station, inverters) and a master file that attaches them (the plant has {modules} modules). Open the master file, keeping the parts in the same folder.",
                 "es": "El modelo 3D se escribe en {n} parte(s) por sector más una parte común (suelo, vallado, estación, inversores) y un archivo maestro que las une (la planta tiene {modules} módulos). Abrir el archivo maestro, con las partes en la misma carpeta."}


def model3d_plan(modules):
    """("single" | "assembly", note or None): how the 3D model of a plant of `modules` modules is written; the note (English and Spanish) is for the assembly."""
    return ("single", None) if modules <= MODEL3D_SINGLE_MAX_MODULES else ("assembly", None)


MODEL3D_FORMATS = ("both", "dxf", "freecad")


def model3d_formats(given):
    """(write the DXF, write the FreeCAD macro) from `engine_inputs["drawings"]["model3d_format"]` (`both` when not given)."""
    fmt = (given or {}).get("model3d_format") or "both"
    if fmt not in MODEL3D_FORMATS:
        raise ValueError(f"engine_inputs.drawings.model3d_format: {fmt!r} is not one of {', '.join(MODEL3D_FORMATS)}")
    return fmt in ("both", "dxf"), fmt in ("both", "freecad")


def _model3d(context, target, name, stamp_date, calls):
    """The 3D model of the plant (`epc_drawing.pv_model3d`) when stage 3 placed tables; it lands in the 3D folder of the transmittal. Big plants are written as parts and a master (`model3d_plan`)."""
    out = {}
    roof = roof_of(context)
    if roof is not None:
        from disciplines.electrical_lv.stages import engine_calls as EC
        from epc_drawing import pv_roof_model3d
        calls.append(EC.record_for("cad/drawing", "epc_drawing.pv_roof_model3d.write"))
        out["pv_roof_model_3d"] = pv_roof_model3d.write(copy.deepcopy(roof[0]), roof[1], Path(target) / "out", f"{name}", stamp_date).name
    found = layout_of(context)
    if found is None:
        return out
    from disciplines.electrical_lv.stages import engine_calls as EC
    want_dxf, want_freecad = model3d_formats(EC.inputs_of(context).get("drawings"))
    parts, modules = equipment_parts(found[0]), sum(int(t["modules"]) for t in found[0]["tables"])
    folder = Path(target) / "out"
    if want_freecad:
        from epc_drawing import pv_freecad
        calls.append(EC.record_for("cad/drawing", "epc_drawing.pv_freecad.write"))
        out["pv_model_3d_freecad"] = pv_freecad.write(copy.deepcopy(found[0]), found[1], folder, f"{name}", stamp_date, parts=parts)["macro"].name
    return dict(out, **(_dxf_model(found, folder, name, stamp_date, parts, modules, calls) if want_dxf else {}))


def _dxf_model(found, folder, name, stamp_date, parts, modules, calls):
    """The DXF of the plant: one file, or parts and a master for a big plant (`model3d_plan`)."""
    from disciplines.electrical_lv.stages import engine_calls as EC
    from epc_drawing import pv_model3d
    kind, _ = model3d_plan(modules)
    calls.append(EC.record_for("cad/drawing", "epc_drawing.pv_model3d.write" if kind == "single" else "epc_drawing.pv_model3d.write_assembly"))
    if kind == "single":
        return {"pv_model_3d": pv_model3d.write(copy.deepcopy(found[0]), found[1], folder, f"{name}", stamp_date, parts=parts).name}
    done = pv_model3d.write_assembly(copy.deepcopy(found[0]), found[1], folder, f"{name}", stamp_date, parts=parts)
    note = {k: v.format(n=done["sectors"], modules=modules) for k, v in MODEL3D_PARTS.items()}
    return {"pv_model_3d": done["master"].name, "pv_model_3d_parts": [p.name for p in done["parts"]], "pv_model_3d_note": note}
