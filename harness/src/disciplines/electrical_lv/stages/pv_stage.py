"""Slice 32 of stage 3 (photovoltaic plant: hourly energy yield and string layout), optional.

The discipline calculates nothing: it hands the `pv` section of `context.engine_inputs` to `epc_pv.run` and returns what comes back.
The section is `{"document": <input document of epc_pv>, "options": {<epc_pv.Options fields>}, "layout": {<input of epc_pv.plan_layout>}}`; `options` and `layout` are optional. `document` carries the site, the
hourly weather, the arrays with their module and inverter data and the typical-value assumptions (nothing is defaulted here). It is the photovoltaic
counterpart of the `lighting` section: the generation side cannot come from the load list, which only holds consumption.

  no `pv` section   the slice is not available and the stage goes on without it (`optional`, see `grouped.py`)
  invalid section   `blocked` with the engine's message in English and Spanish (or the unknown key); the grouped stage adds the `pv:` prefix
  valid section     `ok`: the engine result as it is, one engine call, and one `note` finding per engine warning (draft, D21: the engine's typical values are not confirmed)
  `weather_file`  path inside the project `inputs/` of the PVGIS file written by the data step `epc_pv.weather` (`{"weather", "source"}`); its `weather` replaces the one of `document` and its `source` is stated by one
                    `note` finding (typical year, pending review). The stage never reads the network: PVGIS is asked before the run (landing page or `python -m epc_pv.weather`).
  `roof`          the roof planes (`epc_pv.plan_roof`): the modules are placed on each plane and the arrays of the run are the result (one per plane); the plane's tilt and azimuth are optional.
  `flat_roof`     nothing is known about the roof: it is assumed flat and the harness proposes the structure (`epc_pv.flatroof`): the tilt that gives the most energy from the roof, the frames that fit,
                    their heights, the layout (so stage 10 draws the plans) and a `note` finding that states the assumption. Wind, ballast and fixings are not calculated.
  without tilt or azimuth   the harness chooses them (`epc_pv.orient.optimal`: facing the equator, tilt searched on the weather year) and says so in one `note` finding.
  with `layout`     the plant layout (`epc_pv.plan_layout`: tables, inverters, station, strings on each table) is added as `outputs["layout"]`, one more engine call, a `major` finding when the
                    tables do not fit the site, and stage 10 draws the layout, stringing and cabling plans and the single-line diagram of the plant from it (`pv_drawings.py`)

The result does not change the load list: the plant generates, the load list consumes. The auxiliary services of the plant are loads as any other.
"""
import json
from pathlib import Path

from disciplines.electrical_lv.stages import engine_calls as EC
from disciplines.electrical_lv.stages.base import Stage, StageInputError

ENGINE = "calculation/pv"
FUNCTION = "epc_pv.run"
LAYOUT_FUNCTION = "epc_pv.plan_layout"
KEYS = ("document", "options", "layout", "weather_file", "roof", "flat_roof")
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
    doc = section["document"]
    return json.loads(doc) if isinstance(doc, (str, bytes)) else doc


def source_finding(n, run_id, slug, source):
    """A note finding that states where the weather of the run comes from (origin, edition, date, status)."""
    value = f"{source.get('provider')} {source.get('radiation_db')}/{source.get('meteo_db')} {source.get('year_min')}-{source.get('year_max')}, retrieved {source.get('retrieved')}, {source.get('status')}"
    return {"id": f"F-{n:04d}", "run_id": run_id, "verifier": "calc-check", "severity": "note", "document": slug, "field": "weather/source", "value": value, "expected": "weather confirmed by the engineer of record",
            "clause": "data source", "action": "Review the typical year (not a measured year) before relying on the yield.", "evidence": [f"{source.get('citation')}"], "status": "open"}


def _with_weather_file(section, inputs_dir):
    """(section with the weather of the PVGIS file in its document, source) or raises StageInputError; `section` without `weather_file` comes back as it is."""
    name = section.get("weather_file")
    if name is None:
        return section, None
    base = Path(inputs_dir).resolve() if inputs_dir else None
    target = (base / name).resolve() if base else None
    if target is None or base not in target.parents or not target.is_file():
        raise StageInputError([f"weather_file: `{name}` is not a file inside the project inputs / no es un archivo dentro de las entradas del proyecto"])
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        document = dict(_document_of(section), weather=data["weather"])
    except (ValueError, KeyError, TypeError) as exc:
        raise StageInputError([f"weather_file: `{name}` is not a PVGIS weather file ({exc}) / no es un archivo de clima de PVGIS"]) from exc
    return dict(section, document=document), data.get("source") or {}


ORIENTATION_KEYS = ("tilt_deg", "azimuth_deg")


def orientation_finding(n, run_id, slug, chosen):
    value = f"tilt {chosen['tilt_deg']:g} deg, azimuth {chosen['azimuth_deg']:g} deg (from north), {chosen['specific_yield_kwh_kwp']:g} kWh/kWp: {chosen['method']}"
    return {"id": f"F-{n:04d}", "run_id": run_id, "verifier": "calc-check", "severity": "note", "document": slug, "field": "orientation/chosen", "value": value, "expected": "reviewed by the engineer of record",
            "clause": "engine proposal", "action": "Confirm the orientation or give the real one (a roof fixes it).", "evidence": ["engine epc_pv.orient.optimal"], "status": "open"}


def _choose_orientation(document, template):
    """The orientation the engine proposes for `document` with `template` as its array (module, inverter, ratio)."""
    import epc_pv.orient
    probe = dict(document, arrays=[dict(template, id="PROBE", tilt_deg=0, azimuth_deg=0, n_modules=1)])
    try:
        return epc_pv.orient.optimal(probe)
    except epc_pv.PvError as exc:
        raise StageInputError([f"orientation: {exc} / {exc.es}"]) from exc


def _fill_planes(roof, document):
    """The orientation the engine chose when some plane lacks tilt or azimuth (the planes are completed in place), else None."""
    planes = [p for p in roof.get("planes", []) if isinstance(p, dict)]
    if not any(k not in p for p in planes for k in ORIENTATION_KEYS):
        return None
    chosen = _choose_orientation(document, roof.get("array") or {})
    for p in planes:
        for k in ORIENTATION_KEYS:
            p.setdefault(k, chosen[k])
    return chosen


def flat_roof_finding(n, run_id, slug, proposal):
    s = proposal["structure"]
    value = (f"{proposal['assumption']}: {s['frames']} frame(s) of {s['modules_per_frame']} module(s) at {proposal['tilt_deg']:g} deg, azimuth {proposal['azimuth_deg']:g} deg, "
             f"heights {s['front_height_m']:g} to {s['rear_height_m']:g} m; not calculated: {s['not_calculated']['en']}")
    return {"id": f"F-{n:04d}", "run_id": run_id, "verifier": "calc-check", "severity": "note", "document": slug, "field": "roof/assumed_flat", "value": value, "expected": "roof data confirmed by the engineer of record",
            "clause": "engine proposal", "action": "Confirm the roof type and give its structure data; the wind and ballast study is pending.", "evidence": ["engine epc_pv.flatroof.propose"], "status": "open"}


def _with_flat_roof(section):
    """(section with the arrays and layout of the proposed structure, proposal or None)."""
    if section.get("flat_roof") is None:
        return section, None
    import copy
    import epc_pv
    import epc_pv.flatroof as flatroof
    spec, document = copy.deepcopy(section["flat_roof"]), _document_of(section)
    try:
        proposal = flatroof.propose(document, spec)
    except epc_pv.PvError as exc:
        raise StageInputError([f"flat_roof: {exc} / {exc.es}"]) from exc
    if proposal["modules"] < 1:
        raise StageInputError(["flat_roof: the roof holds no frame (smaller than one frame plus margins) / el techo no admite ningún bastidor (menor que un bastidor más los retiros)"])
    array = dict(spec["array"], id="A1", name="A1", tilt_deg=proposal["tilt_deg"], azimuth_deg=proposal["azimuth_deg"], n_modules=proposal["modules"])
    return dict(section, document=dict(document, arrays=[array]), layout=proposal["layout"]), proposal


def _with_roof(section):
    """(section, roof result or None, orientation chosen or None): the arrays come from the roof planes; tilt and azimuth missing are chosen by the engine."""
    if section.get("roof") is None:
        return section, None, None
    import copy
    import epc_pv
    roof, document = copy.deepcopy(section["roof"]), _document_of(section)
    chosen = _fill_planes(roof, document)
    try:
        result = epc_pv.plan_roof(roof)
    except epc_pv.PvError as exc:
        raise StageInputError([f"roof: {exc} / {exc.es}"]) from exc
    return dict(section, document=dict(document, arrays=result["arrays"])), result, chosen


def _with_orientation(section):
    """Arrays of the document without tilt or azimuth get the engine's choice; (section, chosen or None)."""
    document = _document_of(section)
    arrays = document.get("arrays") or []
    if not arrays or all(k in a for a in arrays for k in ORIENTATION_KEYS):
        return section, None
    chosen = _choose_orientation(document, arrays[0])
    return dict(section, document=dict(document, arrays=[{**chosen_keys(chosen), **a} for a in arrays])), chosen


def chosen_keys(chosen):
    return {k: chosen[k] for k in ORIENTATION_KEYS}


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

    def _prepare(self, context):
        """(section ready for the engine, source, flat roof proposal, roof result, orientation chosen): every step that completes the section before the run."""
        section, source = _with_weather_file(_section(context), context.inputs_dir)
        section, flat = _with_flat_roof(section)
        section, roof, chosen = _with_roof(section)
        if roof is None and flat is None:
            section, chosen = _with_orientation(section)
        return section, source, flat, roof, chosen

    def _notes(self, context, found, first):
        """The note findings of the steps above, numbered after `first` findings."""
        _, source, flat, _, chosen = found
        make = [(flat, flat_roof_finding), (chosen, orientation_finding), (source, source_finding)]
        out = []
        for value, fn in make:
            out += [fn(first + len(out) + 1, context.pipeline_run_id, self.spec.slug, value)] if value else []
        return out

    def execute(self, context):
        if _section(context) is None:
            return self.result("not_available", message=NOT_PROVIDED, reason="no_pv_inputs")
        found = self._prepare(context)
        section, _, flat, roof, _ = found
        result = _run(section)
        result = dict(result, **({"roof": roof} if roof is not None else {}), **({"flat_roof": flat} if flat is not None else {}))
        warnings, calls, findings = list(result["warnings"]) + (roof or flat or {"warnings": []})["warnings"], [EC.record_for(ENGINE, FUNCTION)], []
        if section.get("layout") is not None:
            geometry = _layout(section, _document_of(section), result)
            result, warnings = dict(result, layout=geometry), warnings + geometry["warnings"]
            calls.append(EC.record_for(ENGINE, LAYOUT_FUNCTION))
            findings += [layout_finding(1, context.pipeline_run_id, self.spec.slug, geometry)] if not geometry["fits"] else []
        findings += self._notes(context, found, len(findings))
        findings += [warning_finding(len(findings) + n, context.pipeline_run_id, self.spec.slug, w) for n, w in enumerate(warnings, start=1)]
        totals, counts = result["totals"], result["counts"]
        return self.result("ok", outputs=result, findings=findings, engine_calls=calls,
                           message=f"{counts['arrays']} array(s), {counts['inverters']} inverter(s), {counts['modules']} module(s), "
                                   f"{totals['dc_kwp']} kWp DC, {totals['ac_kw']} kW AC (draft)")
