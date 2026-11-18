"""Slice 32 of stage 3 (photovoltaic plant: hourly energy yield and string layout), optional.

The discipline calculates nothing: it hands the `pv` section of `context.engine_inputs` to `epc_pv.run` and returns what comes back.
The section is `{"document": <input document of epc_pv>, "options": {<epc_pv.Options fields>}, "layout": {<input of epc_pv.plan_layout>}}`; `options` and `layout` are optional. `document` carries the site, the
hourly weather, the arrays with their module and inverter data and the typical-value assumptions (nothing is defaulted here). It is the photovoltaic
counterpart of the `lighting` section: the generation side cannot come from the load list, which only holds consumption.

  no `pv` section   the slice is not available and the stage goes on without it (`optional`, see `grouped.py`)
  invalid section   `blocked` with the engine's message in English and Spanish (or the unknown key); the grouped stage adds the `pv:` prefix
  valid section     `ok`: the engine result as it is, one engine call, and one `note` finding per engine warning (draft, D21: the engine's typical values are not confirmed)
  with `layout`     the plant layout (`epc_pv.plan_layout`: tables, inverters, station, strings on each table) is added as `outputs["layout"]`, one more engine call, a `major` finding when the
                    tables do not fit the site, and stage 10 draws the layout, stringing and cabling plans and the single-line diagram of the plant from it (`pv_drawings.py`)

The result does not change the load list: the plant generates, the load list consumes. The auxiliary services of the plant are loads as any other.
"""
from disciplines.electrical_lv.stages import engine_calls as EC
from disciplines.electrical_lv.stages.base import Stage, StageInputError

ENGINE = "calculation/pv"
FUNCTION = "epc_pv.run"
LAYOUT_FUNCTION = "epc_pv.plan_layout"
KEYS = ("document", "options", "layout")
NOT_PROVIDED = "pv inputs not provided"


def warning_finding(n, run_id, slug, warning):
    """A note-severity finding that states one warning of the engine (text in English and Spanish)."""
    return {"id": f"F-{n:04d}", "run_id": run_id, "verifier": "calc-check", "severity": "note", "document": slug, "field": f"warning/{warning['code']}",
            "value": {"en": warning["en"], "es": warning["es"]}, "expected": "reviewed by the engineer of record", "clause": "engine warning",
            "action": "Review the warning or correct the input.", "evidence": [f"engine {FUNCTION}"], "status": "open"}


def layout_finding(n, run_id, slug, geometry):
    """A major finding: some tables of the plant do not fit the site (the engine says how many)."""
    left = geometry["counts"]["tables_left_out"]
    return {"id": f"F-{n:04d}", "run_id": run_id, "verifier": "calc-check", "severity": "major", "document": slug, "field": "layout/fits", "value": f"{left} table(s) left out", "expected": "all tables inside the site",
            "clause": "engine result layout fits", "action": "Enlarge the site, raise the modules per table or reduce the tilt; or confirm the reduced plant with the engineer of record.",
            "evidence": [f"engine {FUNCTION} / {LAYOUT_FUNCTION}"], "status": "open"}


def _section(context):
    section = (context.engine_inputs or {}).get("pv")
    if section is None:
        return None
    if not isinstance(section, dict) or not isinstance(section.get("document"), (dict, str, bytes)):
        raise StageInputError(["must be an object with `document` (the epc_pv input) and optional `options`"])
    unknown = sorted(set(section) - set(KEYS))
    if unknown:
        raise StageInputError([f"unknown input(s) {', '.join(unknown)}"])
    if not isinstance(section.get("options", {}), dict):
        raise StageInputError(["`options` must be an object"])
    return section


def _layout(section, document, result):
    import epc_pv
    try:
        return epc_pv.plan_layout(document, result, section["layout"])
    except epc_pv.PvError as exc:
        raise StageInputError([f"layout: {exc} / {exc.es}"]) from exc


def _document_of(section):
    import json
    doc = section["document"]
    return json.loads(doc) if isinstance(doc, (str, bytes)) else doc


def _run(section):
    import epc_pv
    try:
        options = epc_pv.Options(**(section.get("options") or {}))
        return epc_pv.run(section["document"], options).as_dict()
    except epc_pv.PvError as exc:
        raise StageInputError([f"{exc} / {exc.es}"]) from exc
    except TypeError as exc:                      # an option the engine does not have
        raise StageInputError([str(exc)]) from exc


class PvStage(Stage):
    wired = True
    wiring_task = "PV-1"
    optional = True      # without its inputs the grouped stage skips it instead of ending as not_available

    def execute(self, context):
        section = _section(context)
        if section is None:
            return self.result("not_available", message=NOT_PROVIDED, reason="no_pv_inputs")
        result = _run(section)
        warnings = list(result["warnings"])
        calls = [EC.record_for(ENGINE, FUNCTION)]
        findings = []
        if section.get("layout") is not None:
            geometry = _layout(section, _document_of(section), result)
            result = dict(result, layout=geometry)
            warnings += geometry["warnings"]
            calls.append(EC.record_for(ENGINE, LAYOUT_FUNCTION))
            findings += [layout_finding(1, context.pipeline_run_id, self.spec.slug, geometry)] if not geometry["fits"] else []
        findings += [warning_finding(len(findings) + n, context.pipeline_run_id, self.spec.slug, w) for n, w in enumerate(warnings, start=1)]
        totals, counts = result["totals"], result["counts"]
        return self.result("ok", outputs=result, findings=findings, engine_calls=calls,
                           message=f"{counts['arrays']} array(s), {counts['inverters']} inverter(s), {counts['modules']} module(s), "
                                   f"{totals['dc_kwp']} kWp DC, {totals['ac_kw']} kW AC (draft)")
