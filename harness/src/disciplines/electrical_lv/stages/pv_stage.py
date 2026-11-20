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
  `roof`          the roof planes (`epc_pv.plan_roof`): the modules are placed on each plane and the arrays of the run are the result (one per plane, so one MPPT never mixes orientations); the plane's tilt and
                    azimuth are optional. Stage 10 draws the roof layout, stringing and cabling plans from it (`pv_drawings.py`). Wind uplift and ballast are not calculated (no wind value in the norm register).
  `roof_dxf`      `{"file": <DXF inside the project inputs>, "setback_m": <margin>}`: the planes of `roof` come from the DXF of the roof (`epc_pv.roofdxf`); `roof` then carries the rest (module size, gap,
                    array, target) and no `planes`.
  `flat_roof`     nothing is known about the roof: it is assumed flat and the harness proposes the structure (`epc_pv.flatroof`): the tilt that gives the most energy from the roof, the frames that fit,
                    their heights, the layout (so stage 10 draws the plans) and a `note` finding that states the assumption. Wind, ballast and fixings are not calculated.
  `layout.fill`   the structure is the site: `layout` carries `"fill": true` (and optional `target_modules` as a cap) and the harness fills the site with as many tables as fit at the chosen tilt
                    (`epc_pv.flatroof` rules): the arrays, strings, inverters and yield follow from the modules that really fit. A `note` finding states the result.
  inverter `"auto"`  (in an array template) the harness picks the catalog inverter whose count gives the DC/AC ratio closest to `dc_ac_ratio` for the modules that fit, and says so in a `note` finding.
  module `"auto"`  (`"auto": true` in the module block of an array template) the harness tries every module of the catalog (and both module orientations on a ground site or flat roof) on the structure and keeps the one
                    with the highest total installed power (`epc_pv.modulepick`), which may be a smaller module that fits more; the alternatives are stated in a `note` finding. `target_kwp` (a power cap) is turned into modules after the pick.
  `isc_max_input_a` null   the data sheet gap stays null: the engine checks the operating input current only and a `note` finding says the short-circuit limit was not checked (never silent).
  `economics`     `{"energy_price": <client price per kWh>, "currency": <text>, "investment": <optional client cost>}`: the saving is the yearly kWh of the engine times the client's price (all the energy is assumed
                    used on site, no export, no degradation, no price escalation); with an investment the simple payback is investment / saving. Every value is the client's own: none is recorded or invented here.
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
KEYS = ("document", "options", "layout", "weather_file", "roof", "flat_roof", "roof_dxf", "economics")
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


def _input_file(inputs_dir, name, label):
    """The file `name` inside the project inputs, or raises StageInputError (a path that leaves the inputs folder is refused)."""
    base = Path(inputs_dir).resolve() if inputs_dir else None
    target = (base / name).resolve() if base else None
    if target is None or base not in target.parents or not target.is_file():
        raise StageInputError([f"{label}: `{name}` is not a file inside the project inputs / no es un archivo dentro de las entradas del proyecto"])
    return target


def _with_weather_file(section, inputs_dir):
    """(section with the weather of the PVGIS file in its document, source) or raises StageInputError; `section` without `weather_file` comes back as it is."""
    name = section.get("weather_file")
    if name is None:
        return section, None
    target = _input_file(inputs_dir, name, "weather_file")
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


def _auto_module(array):
    return isinstance(array, dict) and isinstance(array.get("module"), dict) and bool(array["module"].get("auto"))


def _apply_module(spec, array, row, rows, pmax_key=True):
    """Puts the picked module in `array` and its size in `spec` (the structure input); returns the note warning. A `target_kwp` cap becomes `target_modules` with the picked module."""
    import epc_pv.modulepick as mp
    import epc_pv.orient as orient
    from epc_pv.messages import item
    rec = row["record"]
    array["module"] = mp.block(rec)
    spec["module_dimensions_mm"] = list(rec["dimensions_mm"][:2])
    if "target_kwp" in spec:
        spec["target_modules"] = orient.modules_for_kwp(spec.pop("target_kwp"), float(rec["module"]["pmax_w"]))
    return item("module_auto", model=rec["model"], n=row["modules"], kwp=row["dc_kwp"], table=mp.summary(rows))


def _pick_site_module(document, spec, array, make_spec):
    """The best module row and the alternatives for a site or flat roof `spec` (the `propose` input) whose `array` has an `auto` module: the tilt comes from a first proposal, then every module is counted
    on the structure `make_spec(record, orientation)` gives (for a site, with the table reduced to fit)."""
    import copy
    import epc_pv.flatroof as flatroof
    import epc_pv.modulepick as mp
    site = document["site"]
    altitude = flatroof.lay.solar_altitude_deg(float(site["latitude_deg"]), float(site["longitude_deg"]))
    tilt = flatroof.propose(document, copy.deepcopy(dict(spec, array=array)))["tilt_deg"] if "tilt_deg" not in spec else float(spec["tilt_deg"])

    def count(rec, orientation):
        return flatroof.capacity(make_spec(rec, orientation), tilt, altitude)["modules"]
    return mp.best(count, ("portrait", "landscape"))


def _templates(section):
    """Every array template of the section (arrays of the document, roof, flat roof), as the dicts the engine will read."""
    document = section.get("document")
    arrays = list(document.get("arrays") or []) if isinstance(document, dict) else []
    return [a for a in arrays + [(section.get(k) or {}).get("array") for k in ("roof", "flat_roof")] if isinstance(a, dict)]


def equipment_finding(n, run_id, slug, warning):
    """A note finding for an equipment assumption of the harness (inverter chosen, short-circuit current assumed)."""
    out = warning_finding(n, run_id, slug, warning)
    return dict(out, clause="engine proposal", action="Confirm the equipment with the engineer of record (pending review).", evidence=["engine epc_pv.catalog"])


def _with_equipment(section):
    """(section whose templates carry a usable inverter block, warnings): a placeholder for `auto` (the final pick needs the module count)."""
    import copy
    import epc_pv.catalog as catalog
    section = copy.deepcopy(section)
    for array in _templates(section):
        if array.get("inverter") == catalog.AUTO:
            array["inverter"] = catalog.with_isc(catalog.inverters()[0])
    return section, []


def _pick_inverters(section, originals):
    """(section whose `auto` arrays carry the catalog inverter that fits their module count, warnings); `originals` are the templates before `_with_equipment`."""
    import epc_pv.catalog as catalog
    from epc_pv.messages import item
    auto = [a for a in originals if a.get("inverter") == catalog.AUTO]
    if not auto:
        return section, []
    ratio = auto[0].get("dc_ac_ratio")
    if ratio is None:
        raise StageInputError(["inverter `auto` needs `dc_ac_ratio` in the array / el inversor `auto` necesita `dc_ac_ratio` en el arreglo"])
    warned, arrays = [], []
    for a in section["document"]["arrays"]:
        modules, pmax = int(a["n_modules"]), float(a["module"]["pmax_w"])
        rec = catalog.pick_inverter(modules, pmax, float(ratio), module=a["module"])
        block, notes = catalog.with_isc(rec), []
        n = max(1, catalog.half_up(modules * pmax / (float(ratio) * block["pac0_w"])))
        warned += notes + [item("inverter_auto", array=a["id"], model=rec["model"], n=n, kwp=round(modules * pmax / 1000.0, 2), ratio=ratio)]
        arrays.append(dict(a, inverter=dict(block, model=rec["model"], auto=True), **({"dc_ac_ratio": ratio} if "dc_ac_ratio" in a else {})))
    return dict(section, document=dict(section["document"], arrays=arrays)), warned


def ground_fill_finding(n, run_id, slug, proposal):
    s = proposal["structure"]
    value = (f"{proposal['assumption']}: {proposal['modules']} module(s) in {s['frames']} table(s) at {proposal['tilt_deg']:g} deg, azimuth {proposal['azimuth_deg']:g} deg; "
             f"the site holds up to {proposal['capacity_modules']} module(s)")
    return {"id": f"F-{n:04d}", "run_id": run_id, "verifier": "calc-check", "severity": "note", "document": slug, "field": "layout/filled", "value": value, "expected": "site and table data confirmed by the engineer of record",
            "clause": "engine proposal", "action": "Confirm the site, the table and the tilt; the plant size is the result of the fill (pending review).", "evidence": ["engine epc_pv.flatroof.propose"], "status": "open"}


def _with_fill(section):
    """(section whose arrays and layout come from filling the site with tables, proposal or None): only for a `layout` with `fill: true`."""
    layout = section.get("layout")
    if not isinstance(layout, dict) or not layout.get("fill"):
        return section, None
    import copy
    import epc_pv
    import epc_pv.flatroof as flatroof
    from epc_pv.messages import item
    document, layout = _document_of(section), copy.deepcopy(layout)
    arrays = document.get("arrays") or []
    if not arrays:
        raise StageInputError(["layout.fill: needs one array with the module and inverter / necesita un arreglo con el módulo y el inversor"])
    target = layout.pop("target_modules", None)
    layout.pop("fill")
    wanted, picked, array = layout["table"], [], dict(arrays[0])
    try:
        if _auto_module(array):
            def make(rec, o):
                trial = dict(layout, module_dimensions_mm=list(rec["dimensions_mm"][:2]), table=dict(layout["table"], orientation=o))
                return flatroof.spec_from_layout(flatroof.fit_table(trial), array)
            row, rows = _pick_site_module(document, flatroof.spec_from_layout(flatroof.fit_table(layout), array), array, make)
            layout = dict(layout, table=dict(layout["table"], orientation=row["orientation"]))
            picked = [_apply_module(layout, array, row, rows)]
            layout["module_dimensions_mm"] = list(row["record"]["dimensions_mm"][:2])
            target = layout.pop("target_modules", target)
            wanted = layout["table"]
        layout = flatroof.fit_table(layout)
        proposal = flatroof.propose(document, flatroof.spec_from_layout(layout, array, target))
    except epc_pv.PvError as exc:
        raise StageInputError([f"layout: {exc} / {exc.es}"]) from exc
    proposal["warnings"] += picked
    if layout["table"] != wanted:
        proposal["warnings"].append(item("table_shrunk", rows=wanted["rows"], per_row=wanted["modules_per_row"], rows_fit=layout["table"]["rows"], per_row_fit=layout["table"]["modules_per_row"]))
    if proposal["modules"] < 1:
        raise StageInputError(["layout.fill: the site holds no table (smaller than one table plus margins) / el predio no admite ninguna mesa (menor que una mesa más los retiros)"])
    array = dict(array, id="A1", name="A1", tilt_deg=proposal["tilt_deg"], azimuth_deg=proposal["azimuth_deg"], n_modules=proposal["modules"])
    return dict(section, document=dict(document, arrays=[array]), layout=layout), proposal


def _with_flat_roof(section):
    """(section with the arrays and layout of the proposed structure, proposal or None)."""
    if section.get("flat_roof") is None:
        return section, None
    import copy
    import epc_pv
    import epc_pv.flatroof as flatroof
    from epc_pv.messages import item
    spec, document = copy.deepcopy(section["flat_roof"]), _document_of(section)
    picked, wanted = [], None
    try:
        flatroof.check(spec)
        wanted = spec["table"]
        if _auto_module(spec.get("array")):
            row, rows = _pick_site_module(document, flatroof.fit_spec(spec), spec["array"], lambda rec, o: flatroof.fit_spec(dict(spec, module_dimensions_mm=list(rec["dimensions_mm"][:2]), table=dict(spec["table"], orientation=o))))
            spec["table"] = dict(spec["table"], orientation=row["orientation"])
            picked = [_apply_module(spec, spec["array"], row, rows)]
        spec = flatroof.fit_spec(spec)
        proposal = flatroof.propose(document, spec)
    except epc_pv.PvError as exc:
        raise StageInputError([f"flat_roof: {exc} / {exc.es}"]) from exc
    proposal["warnings"] += picked
    if spec["table"] != wanted:
        proposal["warnings"].append(item("table_shrunk", rows=wanted["rows"], per_row=wanted["modules_per_row"], rows_fit=spec["table"]["rows"], per_row_fit=spec["table"]["modules_per_row"]))
    if proposal["modules"] < 1:
        need = flatroof.minimum_roof_m(spec)
        raise StageInputError([f"flat_roof: the roof ({spec['width_m']:g} x {spec['length_m']:g} m) holds no frame; with the setback and walkway given it needs at least {need['width_m']:g} x {need['length_m']:g} m for one module "
                               f"/ el techo ({spec['width_m']:g} x {spec['length_m']:g} m) no admite ningún bastidor; con el retiro y el pasillo dados necesita al menos {need['width_m']:g} x {need['length_m']:g} m para un módulo"])
    array = dict(spec["array"], id="A1", name="A1", tilt_deg=proposal["tilt_deg"], azimuth_deg=proposal["azimuth_deg"], n_modules=proposal["modules"])
    return dict(section, document=dict(document, arrays=[array]), layout=proposal["layout"]), proposal


def _dxf_planes(section, inputs_dir):
    """(roof with the planes of the DXF, warnings of the reading); a section without `roof_dxf` comes back as it is."""
    spec = section.get("roof_dxf")
    roof = section.get("roof")
    if spec is None:
        return roof, []
    import epc_pv
    import epc_pv.roofdxf as roofdxf
    if not isinstance(spec, dict) or "file" not in spec or "setback_m" not in spec or not isinstance(roof, dict) or "planes" in roof:
        raise StageInputError(["roof_dxf: needs `file` and `setback_m`, and `roof` without `planes` (module size, gap and array) / necesita `file` y `setback_m`, y `roof` sin `planes` (tamaño del módulo, separación y arreglo)"])
    target = _input_file(inputs_dir, spec["file"], "roof_dxf")
    try:
        read = roofdxf.read(target.read_bytes().decode("utf-8", errors="replace"), spec["setback_m"])
    except epc_pv.PvError as exc:
        raise StageInputError([f"roof_dxf: {exc} / {exc.es}"]) from exc
    return dict(roof, planes=read["planes"]), read["warnings"]


def _with_roof(section, inputs_dir=None):
    """(section, roof result or None, orientation chosen or None): the arrays come from the roof planes; tilt and azimuth missing are chosen by the engine."""
    if section.get("roof") is None:
        return section, None, None
    import copy
    import epc_pv
    roof, warned = _dxf_planes(copy.deepcopy(section), inputs_dir)
    document = _document_of(section)
    chosen = _fill_planes(roof, document)
    picked = []
    try:
        if _auto_module(roof.get("array")):
            import epc_pv.modulepick as mp
            count = lambda rec, _o: epc_pv.plan_roof({k: v for k, v in dict(roof, module_dimensions_mm=list(rec["dimensions_mm"][:2])).items() if k != "target_modules"})["counts"]["capacity"]      # noqa: E731
            row, rows = mp.best(count)
            roof = dict(roof, array=dict(roof["array"]))
            picked = [_apply_module(roof, roof["array"], row, rows)]
        result = epc_pv.plan_roof(roof)
    except epc_pv.PvError as exc:
        raise StageInputError([f"roof: {exc} / {exc.es}"]) from exc
    return dict(section, document=dict(document, arrays=result["arrays"])), dict(result, warnings=warned + result["warnings"] + picked), chosen


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


def _trim_to_site(section, result, proposal):
    """(section, result) where the modules of a filled site are whole strings that still fit: strings round the module count up, and one more string can overflow the last table."""
    capacity, array = proposal["capacity_modules"], result["arrays"][0]
    if array["modules"] <= capacity:
        return section, result
    fitted = (capacity // array["strings"]["n_series"]) * array["strings"]["n_series"]
    if fitted < 1:
        n = array["strings"]["n_series"]
        raise StageInputError([f"site fill: one string is {n} module(s) long and the site or roof holds only {capacity} / un string tiene {n} módulo(s) y el predio o techo admite solo {capacity}"])
    arrays = [dict(a, n_modules=fitted) for a in section["document"]["arrays"]]
    section = dict(section, document=dict(section["document"], arrays=arrays))
    return section, _run(section)


def economic_summary(result, economics):
    """The saving the client's own price gives: yearly and monthly kWh times `energy_price`; the simple payback when the client gave its investment."""
    if not economics:
        return {"en": "Not calculated: give your energy price (per kWh) and the saving is the yearly energy times it.", "es": "No se calcula: indicá tu precio de la energía (por kWh) y el ahorro es la energía anual por ese precio."}
    price, totals = float(economics["energy_price"]), result["totals"]
    saving = totals["ac_kwh"] * price
    out = {"energy_kwh_year": totals["ac_kwh"], "energy_price": price, "currency": economics.get("currency", ""), "saving_year": round(saving, 2),
           "saving_month": [round(m * price, 2) for m in totals["monthly_ac_kwh"]], "assumes": {"en": "all the energy is used on site (no export), no degradation, no price escalation", "es": "toda la energía se usa en el sitio (sin inyección), sin degradación y sin aumento de precio"}, "status": "pending review"}
    if economics.get("investment") is not None and saving > 0:
        out["investment"] = float(economics["investment"])
        out["simple_payback_years"] = round(float(economics["investment"]) / saving, 2)
    return out


def technical_summary(result, economics=None):
    """The technical feasibility in one block, from the engine result only (no threshold is invented): what was installed, what it yields and which of the engine's own limits hold."""
    arrays, totals = result["arrays"], result["totals"]
    string_ok = all(a["strings"]["strings_per_mppt"] <= a["strings"]["strings_per_mppt_limit"] for a in arrays)
    fits = result["layout"]["fits"] if result.get("layout") else (result["roof"]["fits"] if result.get("roof") else True)
    clipping = round(100.0 * totals["clipping_kwh"] / (totals["ac_kwh"] + totals["clipping_kwh"]), 2) if totals["ac_kwh"] + totals["clipping_kwh"] else 0.0
    return {"installed": {"modules": result["counts"]["modules"], "dc_kwp": totals["dc_kwp"], "ac_kw": totals["ac_kw"], "inverters": result["counts"]["inverters"]},
            "yield": {"ac_kwh_year": totals["ac_kwh"], "specific_yield_kwh_kwp": totals["specific_yield_kwh_kwp"], "clipping_pct": clipping},
            "checks": {"structure_holds_the_modules": bool(fits), "strings_inside_inverter_current_limits": string_ok},
            "status": "pending review", "feasible": bool(fits and string_ok),
            "economic": economic_summary(result, economics)}


def _proposals(roof, flat):
    """The roof result and the flat roof / site fill proposal as extra outputs."""
    key = "site_fill" if flat is not None and flat["assumption"].startswith("ground") else "flat_roof"
    return {**({"roof": roof} if roof is not None else {}), **({key: flat} if flat is not None else {})}


def _add_inverters_for_current(section, result):
    """(section, result) where an `auto` inverter count also respects the input current of its MPPT inputs: the ratio alone can leave more strings per input than the data sheet allows, so inverters are added."""
    arrays, changed = [], False
    for spec, res in zip(section["document"]["arrays"], result["arrays"]):
        st, inv = res["strings"], spec["inverter"]
        if inv.get("auto") and st["strings_per_mppt"] > st["strings_per_mppt_limit"] and st["strings_per_mppt_limit"] > 0:
            spec, changed = dict(spec, n_inverters=-(-st["strings"] // (int(inv["n_mppt"]) * st["strings_per_mppt_limit"]))), True
        arrays.append(spec)
    if not changed:
        return section, result
    section = dict(section, document=dict(section["document"], arrays=arrays))
    return section, _run(section)


class PvStage(Stage):
    wired = True
    wiring_task = "PV-1"
    optional = True      # without its inputs the grouped stage skips it instead of ending as not_available

    def _prepare(self, context):
        """(section ready for the engine, source, flat roof proposal, roof result, orientation chosen): every step that completes the section before the run."""
        section, source = _with_weather_file(_section(context), context.inputs_dir)
        originals = [dict(a) for a in _templates(section)]
        section, assumed = _with_equipment(section)
        section, flat = _with_flat_roof(section)
        section, fill = _with_fill(section)
        section, roof, chosen = _with_roof(section, context.inputs_dir)
        if roof is None and flat is None and fill is None:
            section, chosen = _with_orientation(section)
        section, picked = _pick_inverters(section, originals)
        return section, source, flat or fill, roof, chosen, assumed + picked

    def _notes(self, context, found, first):
        """The note findings of the steps above, numbered after `first` findings."""
        _, source, flat, _, chosen, equipment = found
        proposal_finding = ground_fill_finding if flat and flat["assumption"].startswith("ground") else flat_roof_finding
        make = [(flat, proposal_finding), (chosen, orientation_finding), (source, source_finding)]
        out = []
        for value, fn in make:
            out += [fn(first + len(out) + 1, context.pipeline_run_id, self.spec.slug, value)] if value else []
        return out + [equipment_finding(first + len(out) + k, context.pipeline_run_id, self.spec.slug, w) for k, w in enumerate(equipment, start=1)]

    def _with_layout(self, context, section, result, state):
        """(result, warnings, calls, findings) with the plant layout added when the section has one."""
        warnings, calls, findings = state
        if section.get("layout") is None:
            return result, warnings, calls, findings
        geometry = _layout(section, _document_of(section), result)
        findings = findings + ([layout_finding(1, context.pipeline_run_id, self.spec.slug, geometry)] if not geometry["fits"] else [])
        return dict(result, layout=geometry), warnings + geometry["warnings"], calls + [EC.record_for(ENGINE, LAYOUT_FUNCTION)], findings

    def execute(self, context):
        if _section(context) is None:
            return self.result("not_available", message=NOT_PROVIDED, reason="no_pv_inputs")
        found = self._prepare(context)
        section, _, flat, roof, _, _ = found
        result = _run(section)
        section, result = _add_inverters_for_current(section, result)
        if flat is not None:
            section, result = _trim_to_site(section, result, flat)
        result = dict(result, **_proposals(roof, flat))
        warnings, calls, findings = list(result["warnings"]) + (roof or flat or {"warnings": []})["warnings"], [EC.record_for(ENGINE, FUNCTION)], []
        calls += [EC.record_for(ENGINE, "epc_pv.plan_roof")] if roof is not None else []
        result, warnings, calls, findings = self._with_layout(context, section, result, (warnings, calls, findings))
        findings += self._notes(context, found, len(findings))
        findings += [warning_finding(len(findings) + n, context.pipeline_run_id, self.spec.slug, w) for n, w in enumerate(warnings, start=1)]
        totals, counts = result["totals"], result["counts"]
        result = dict(result, technical_feasibility=technical_summary(result, section.get("economics")))
        return self.result("ok", outputs=result, findings=findings, engine_calls=calls,
                           message=f"{counts['arrays']} array(s), {counts['inverters']} inverter(s), {counts['modules']} module(s), "
                                   f"{totals['dc_kwp']} kWp DC, {totals['ac_kw']} kW AC (draft)")
