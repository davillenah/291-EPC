"""The photovoltaic project of the landing page: the form (latitude and longitude for PVGIS, plant data) and the inputs of the pipeline.

Nothing here calculates. The form values become the `pv` section of `engine_inputs` that stage 3 hands to `epc_pv` (see `stages/pv_stage.py`); the typical year comes from PVGIS
(`epc_pv.weather`, one call before the project is created) and is stored in the project as `inputs/weather/weather_pvgis.json`, so the run itself never touches the network.
Proposals (`pv_defaults.json`) are pending review. Two kinds of plant: `ground` (tables in a site, the layout and its four drawings) and `rooftop` (yield and strings only: roof geometry is a gap, see BACKLOG).
"""
import json
from pathlib import Path

DEFAULTS = json.loads(Path(__file__).with_name("pv_defaults.json").read_text(encoding="utf-8"))
WEATHER_FILE = "weather/weather_pvgis.json"
MODES = ("ground", "rooftop")
ORIENTATIONS = ("portrait", "landscape")
ROOF_TYPES = ("flat", "pitched")
NUMBERS = ("latitude_deg", "longitude_deg", "utc_offset_h", "target_kwp", "tilt_deg", "azimuth_deg", "dc_ac_ratio", "albedo", "design_t_min_c", "isc_max_input_a",
           "aux_load_kw", "aux_phases", "aux_length_m", "board_fp", "roof_width_m", "roof_slope_m", "roof_setback_m", "site_width_m", "site_length_m", "setback_m", "table_rows", "table_modules_per_row", "module_gap_m", "table_gap_m", "road_width_m")
GROUND_ONLY = ("site_width_m", "site_length_m", "setback_m", "table_rows", "table_modules_per_row", "table_orientation", "module_gap_m", "table_gap_m", "road_width_m")
REQUIRED = ("mode", "latitude_deg", "longitude_deg", "utc_offset_h", "module", "inverter", "target_kwp", "dc_ac_ratio")
RANGES = {"target_kwp": (0.001, 1e6), "tilt_deg": (0, 90), "azimuth_deg": (0, 360), "latitude_deg": (-90, 90), "longitude_deg": (-180, 180), "utc_offset_h": (-14, 14)}


def catalogs():
    """({id: module record}, {id: inverter record}) of the extracted catalogs of the engine (pending review)."""
    import epc_pv
    data = Path(epc_pv.__file__).parent / "data"
    read = lambda name, key: {r["id"]: r for r in json.loads((data / name).read_text(encoding="utf-8"))[key]}      # noqa: E731
    return read("module_catalog.json", "modules"), read("inverter_catalog.json", "inverters")


def form():
    """The form of the photovoltaic project (the page renders it; the model and inverter lists come from the catalogs, never typed by hand)."""
    modules, inverters = catalogs()
    num = lambda p, req=True: {"path": f"pv.{p}", "kind": "number", "required": req}      # noqa: E731
    sel = lambda p, options, req=True: {"path": f"pv.{p}", "kind": "select", "required": req, "options": options}      # noqa: E731
    out = {"id": "pv", "status": "available", "fields": [
        sel("mode", list(MODES)), sel("roof_type", list(ROOF_TYPES), False), num("latitude_deg"), num("longitude_deg"), num("utc_offset_h"),
        sel("module", sorted(modules)), sel("inverter", sorted(inverters)), num("isc_max_input_a", False),
        num("aux_load_kw", False), sel("aux_phases", ["1", "3"], False), num("aux_length_m", False), num("board_fp", False),
        num("target_kwp"), num("tilt_deg", False), num("azimuth_deg", False), num("dc_ac_ratio"), num("albedo", False), num("design_t_min_c", False),
        num("roof_width_m", False), num("roof_slope_m", False), num("roof_setback_m", False),
        num("site_width_m", False), num("site_length_m", False), num("setback_m", False), num("table_rows", False), num("table_modules_per_row", False),
        sel("table_orientation", list(ORIENTATIONS), False), num("module_gap_m", False), num("table_gap_m", False), num("road_width_m", False)]}
    for f in out["fields"]:
        if f["path"] in proposals():
            f["value"] = proposals()[f["path"]]
    return out


def proposals():
    """The form values the harness proposes (pending review): the Argentine offset, the albedo, the north azimuth and the usual layout distances."""
    d, lay = DEFAULTS, DEFAULTS["layout"]
    keys = ("setback_m", "table_rows", "table_modules_per_row", "table_orientation", "module_gap_m", "table_gap_m", "road_width_m")
    import house
    return {"pv.board_fp": house.DEFAULTS["board"]["fp_default"], "pv.utc_offset_h": d["utc_offset_h"], "pv.albedo": d["albedo"], "pv.dc_ac_ratio": d["dc_ac_ratio"], "pv.roof_type": d["roof_type"], "pv.roof_setback_m": d["roof_setback_m"], **{f"pv.{k}": lay[k] for k in keys}}


def values_of(flat):
    """The `pv.*` answers as {name: number or text}, empty ones dropped; (values, problem) where problem is {code, detail} or None."""
    out = {}
    for key, raw in flat.items():
        if not key.startswith("pv.") or raw in (None, ""):
            continue
        name = key[3:]
        try:
            out[name] = float(raw) if name in NUMBERS else str(raw)
        except (TypeError, ValueError):
            return {}, {"code": "pv_number", "detail": name}
    return out, None


def _catalog_problem(v):
    """The first problem with the equipment chosen (unknown ids, or a data sheet gap the person must fill), or None."""
    modules, inverters = catalogs()
    if v["module"] not in modules or v["inverter"] not in inverters:
        return {"code": "pv_range", "detail": "module / inverter"}
    if inverters[v["inverter"]]["inverter"].get("isc_max_input_a") is None and "isc_max_input_a" not in v:
        return {"code": "pv_isc", "detail": inverters[v["inverter"]]["model"]}
    return None


def _missing(v, building):
    """The first group of answers that is still missing (the auxiliaries of a plant-only run, the site of a ground plant or the plane of a roof), or None."""
    groups = [] if building else [("aux_load_kw", "aux_phases", "aux_length_m", "board_fp")]
    groups.append(("site_width_m", "site_length_m") if v["mode"] == "ground" else ("roof_width_m", "roof_slope_m"))
    gap = next((g for g in groups if not all(k in v for k in g)), None)
    return {"code": "pv_missing", "detail": ", ".join(gap)} if gap else None


def check(flat, building=False):
    """The first problem of the form as {code, detail}, or None. Catalog gaps are asked, never filled: a null `isc_max_input_a` must be typed by the person."""
    v, problem = values_of(flat)
    if problem:
        return problem
    missing = [k for k in REQUIRED if k not in v]
    if missing:
        return {"code": "pv_missing", "detail": ", ".join(missing)}
    out = next(({"code": "pv_range", "detail": f"{n} {lo}..{hi}"} for n, (lo, hi) in RANGES.items() if n in v and not lo <= v[n] <= hi), None)
    if v["mode"] not in MODES:
        out = {"code": "pv_range", "detail": "mode"}
    return out or _catalog_problem(v) or _missing(v, building)


def _template(v, modules, inverters):
    """The module and inverter of the plant and the DC/AC ratio: what every array shares."""
    inverter = dict(inverters[v["inverter"]]["inverter"])
    if inverter.get("isc_max_input_a") is None:
        inverter["isc_max_input_a"] = v["isc_max_input_a"]
    return {"module": dict(modules[v["module"]]["module"]), "inverter": inverter, "dc_ac_ratio": v["dc_ac_ratio"]}


def _n_modules(v, modules):
    import epc_pv.orient
    return epc_pv.orient.modules_for_kwp(v["target_kwp"], modules[v["module"]]["module"]["pmax_w"])


def _array(v, modules, inverters):
    """The array of a ground plant; tilt and azimuth only when the person gave them (otherwise the engine chooses them)."""
    given = {k: v[k] for k in ("tilt_deg", "azimuth_deg") if k in v}
    return {"id": "A1", "name": "A1", "n_modules": _n_modules(v, modules), **given, **_template(v, modules, inverters)}


def _flat_roof(v, modules, inverters):
    """Nothing is known about the roof (no pitch typed): it is assumed flat and the engine proposes the frames (`epc_pv.flatroof`)."""
    flat, lay = DEFAULTS["flat_roof"], DEFAULTS["layout"]
    return {"width_m": v["roof_width_m"], "length_m": v["roof_slope_m"], "setback_m": v.get("roof_setback_m", DEFAULTS["roof_setback_m"]), "walkway_m": flat["walkway_m"],
            "module_dimensions_mm": list(modules[v["module"]]["dimensions_mm"][:2]), "module_gap_m": v.get("module_gap_m", lay["module_gap_m"]), "table": dict(flat["table"]),
            "table_gap_m": flat["table_gap_m"], "front_clearance_m": flat["front_clearance_m"], "station": dict(flat["station"]), "inverter_pad": dict(lay["inverter_pad"]),
            "array": _template(v, modules, inverters), "target_modules": _n_modules(v, modules)}


def _roof(v, modules, inverters):
    """One roof plane typed in the form; the modules are placed by `epc_pv.plan_roof` and the orientation is the roof's or, when not given, the engine's."""
    plane = {"id": "R1", "width_m": v["roof_width_m"], "slope_m": v["roof_slope_m"], "setback_m": v.get("roof_setback_m", DEFAULTS["roof_setback_m"])}
    plane.update({k: v[k] for k in ("tilt_deg", "azimuth_deg") if k in v})
    return {"planes": [plane], "module_dimensions_mm": list(modules[v["module"]]["dimensions_mm"][:2]), "module_gap_m": v.get("module_gap_m", DEFAULTS["layout"]["module_gap_m"]),
            "array": _template(v, modules, inverters), "target_modules": _n_modules(v, modules)}


def _layout(v, module):
    lay = DEFAULTS["layout"]
    pick = lambda k: v.get(k, lay[k])      # noqa: E731
    return {"site": {"width_m": v["site_width_m"], "length_m": v["site_length_m"], "setback_m": pick("setback_m")}, "module_dimensions_mm": list(module["dimensions_mm"][:2]),
            "module_gap_m": pick("module_gap_m"), "table": {"rows": int(pick("table_rows")), "modules_per_row": int(pick("table_modules_per_row")), "orientation": v.get("table_orientation", lay["table_orientation"])},
            "table_gap_m": pick("table_gap_m"), "road_width_m": pick("road_width_m"), "station": dict(lay["station"]), "inverter_pad": dict(lay["inverter_pad"])}


def section(flat):
    """The `pv` section of `engine_inputs` from checked answers: the document without weather (it comes from the PVGIS file) and, for a ground plant, its layout."""
    v, _ = values_of(flat)
    modules, inverters = catalogs()
    site = {"latitude_deg": v["latitude_deg"], "longitude_deg": v["longitude_deg"], "albedo": v.get("albedo", DEFAULTS["albedo"])}
    if "design_t_min_c" in v:
        site["design_t_min_c"] = v["design_t_min_c"]
    if v["mode"] == "rooftop" and v.get("roof_type", DEFAULTS["roof_type"]) == "pitched":
        return {"document": {"site": site}, "weather_file": WEATHER_FILE, "roof": _roof(v, modules, inverters)}
    if v["mode"] == "rooftop":
        return {"document": {"site": site}, "weather_file": WEATHER_FILE, "flat_roof": _flat_roof(v, modules, inverters)}
    return {"document": {"site": site, "arrays": [_array(v, modules, inverters)]}, "weather_file": WEATHER_FILE, "layout": _layout(v, modules[v["module"]])}


def board_of(flat):
    """The `board` section of `engine_inputs` of a plant-only project: its name (the harness proposal) and the power factor the person confirmed."""
    import house
    v, _ = values_of(flat)
    return {"name": house.DEFAULTS["board"]["name"], "fp_default": v["board_fp"]}


def aux_loads(flat):
    """(areas, loads) of the load list of a plant-only project: the auxiliary services the person typed (monitoring, security, trackers). The plant generates; the load list only holds consumption (BACKLOG G5)."""
    v, _ = values_of(flat)
    load = {"id": "AUX-01", "description": "Plant auxiliary services / Servicios auxiliares de la planta", "area": "PV", "kind": "special",
            "power": {"value": v["aux_load_kw"], "unit": "kW"}, "phases": int(v["aux_phases"])}
    load["length"] = {"value": v["aux_length_m"], "unit": "m"}
    return [{"id": "PV", "name": "Planta fotovoltaica"}], [load]


def fetch_weather(flat):
    """The PVGIS file text for the site of the form (one call, the only network use of a PV project); raises `epc_pv.PvError` (English in `str`, Spanish in `.es`)."""
    import epc_pv.weather as W
    v, _ = values_of(flat)
    return json.dumps(W.fetch_tmy(v["latitude_deg"], v["longitude_deg"], v["utc_offset_h"]), ensure_ascii=False, indent=1)
