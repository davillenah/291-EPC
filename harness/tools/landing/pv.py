"""The photovoltaic project of the landing page: the form (latitude and longitude for PVGIS, plant data) and the inputs of the pipeline.

Nothing here calculates. The form values become the `pv` section of `engine_inputs` that stage 3 hands to `epc_pv` (see `stages/pv_stage.py`); the typical year comes from PVGIS
(`epc_pv.weather`, one call before the project is created) and is stored in the project as `inputs/weather/weather_pvgis.json`, so the run itself never touches the network.
The person gives the structure (roof planes or site) and the place; the harness fills it with modules and sizes strings, inverters and yield from what fits (the power is a result, `target_kwp` only a cap).
Module, inverter (`auto`), DC/AC ratio, time zone and the rest are advanced fields with proposals; auxiliaries are optional. Proposals (`pv_defaults.json`) are pending review. Two kinds of plant: `ground` (tables in a site, the layout and its four drawings) and `rooftop` (roof planes, yield, strings and the roof drawings; up to four planes in the form, more from a roof DXF).
"""
import json
from pathlib import Path

DEFAULTS = json.loads(Path(__file__).with_name("pv_defaults.json").read_text(encoding="utf-8"))
WEATHER_FILE = "weather/weather_pvgis.json"
MODES = ("ground", "rooftop")
ORIENTATIONS = ("portrait", "landscape")
ROOF_TYPES = ("flat", "pitched")
EXTRA_PLANES = (2, 3, 4)      # a pitched roof can have up to four planes: the first one is the `roof_*` fields, the others `roof2_*` to `roof4_*`
PLANE_FIELDS = ("width_m", "slope_m", "tilt_deg", "azimuth_deg")
NUMBERS = ("latitude_deg", "longitude_deg", "utc_offset_h", "target_kwp", "tilt_deg", "azimuth_deg", "dc_ac_ratio", "albedo", "design_t_min_c", "isc_max_input_a", "energy_price", "investment",
           "aux_load_kw", "aux_phases", "aux_length_m", "board_fp", "roof_width_m", "roof_slope_m", "roof_setback_m", "site_width_m", "site_length_m", "setback_m", "table_rows", "table_modules_per_row", "module_gap_m", "table_gap_m", "road_width_m") + tuple(f"roof{n}_{k}" for n in EXTRA_PLANES for k in PLANE_FIELDS)
GROUND_ONLY = ("site_width_m", "site_length_m", "setback_m", "table_rows", "table_modules_per_row", "table_orientation", "module_gap_m", "table_gap_m", "road_width_m")
REQUIRED = ("mode", "latitude_deg", "longitude_deg")
ADVANCED = ("structure_id", "currency", "utc_offset_h", "module", "inverter", "isc_max_input_a", "aux_load_kw", "aux_phases", "aux_length_m", "board_fp", "target_kwp", "tilt_deg", "azimuth_deg", "dc_ac_ratio", "albedo", "design_t_min_c",
            "roof_setback_m", "setback_m", "table_rows", "table_modules_per_row", "table_orientation", "module_gap_m", "table_gap_m", "road_width_m")
RANGES = {"energy_price": (0, 1e9), "investment": (0, 1e15), "target_kwp": (0.001, 1e6), "tilt_deg": (0, 90), "azimuth_deg": (0, 360), "latitude_deg": (-90, 90), "longitude_deg": (-180, 180), "utc_offset_h": (-14, 14),
          **{f"roof{n}_{k}": r for n in EXTRA_PLANES for k, r in (("tilt_deg", (0, 90)), ("azimuth_deg", (0, 360)), ("width_m", (0.001, 1e4)), ("slope_m", (0.001, 1e4)))}}


def catalogs():
    """({id: module record}, {id: inverter record}) of the extracted catalogs of the engine (pending review)."""
    from epc_pv import catalog
    return {r["id"]: r for r in catalog.module_records()}, {r["id"]: r for r in catalog.inverters()}


def structures():
    """{id: family} of the mounting structures of the engine (`epc_pv.equipment.structures`, pending review): ground ones feed a ground plant, roof ones a flat roof."""
    from epc_pv import equipment
    return {r["id"]: r["family"] for r in equipment.structures()}


def form():
    """The form of the photovoltaic project (the page renders it; the model and inverter lists come from the catalogs, never typed by hand)."""
    modules, inverters = catalogs()
    num = lambda p, req=True: {"path": f"pv.{p}", "kind": "number", "required": req}      # noqa: E731
    sel = lambda p, options, req=True: {"path": f"pv.{p}", "kind": "select", "required": req, "options": options}      # noqa: E731
    out = {"id": "pv", "status": "available", "fields": [
        sel("mode", list(MODES)), sel("roof_type", list(ROOF_TYPES), False), num("latitude_deg"), num("longitude_deg"), num("energy_price", False), {"path": "pv.currency", "kind": "text", "required": False}, num("investment", False), num("utc_offset_h", False),
        sel("structure_id", ["auto"] + sorted(structures()), False),
        sel("module", ["auto"] + sorted(modules), False), sel("inverter", ["auto"] + sorted(inverters), False), num("isc_max_input_a", False),
        num("aux_load_kw", False), sel("aux_phases", ["1", "3"], False), num("aux_length_m", False), num("board_fp", False),
        num("target_kwp", False), num("tilt_deg", False), num("azimuth_deg", False), num("dc_ac_ratio", False), num("albedo", False), num("design_t_min_c", False),
        num("roof_width_m", False), num("roof_slope_m", False), num("roof_setback_m", False),
        *[num(f"roof{n}_{k}", False) for n in EXTRA_PLANES for k in PLANE_FIELDS],
        num("site_width_m", False), num("site_length_m", False), num("setback_m", False), num("table_rows", False), num("table_modules_per_row", False),
        sel("table_orientation", list(ORIENTATIONS), False), num("module_gap_m", False), num("table_gap_m", False), num("road_width_m", False)]}
    for f in out["fields"]:
        if f["path"] in proposals():
            f["value"] = proposals()[f["path"]]
        f["advanced"] = f["path"][3:] in ADVANCED
    return out


def proposals():
    """The form values the harness proposes (pending review): the Argentine offset, the albedo, the north azimuth and the usual layout distances."""
    d, lay = DEFAULTS, DEFAULTS["layout"]
    keys = ("setback_m", "table_rows", "table_modules_per_row", "table_orientation", "module_gap_m", "table_gap_m", "road_width_m")
    import house
    return {"pv.aux_load_kw": d["aux"]["load_kw"], "pv.aux_phases": str(d["aux"]["phases"]), "pv.aux_length_m": d["aux"]["length_m"], "pv.module": d["module"], "pv.inverter": d["inverter"], "pv.board_fp": house.DEFAULTS["board"]["fp_default"], "pv.albedo": d["albedo"], "pv.dc_ac_ratio": d["dc_ac_ratio"], "pv.roof_type": d["roof_type"], "pv.roof_setback_m": d["roof_setback_m"], **{f"pv.{k}": lay[k] for k in keys}}


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


def _equipment(v):
    """(module id, inverter id or `auto`): what the person chose or the proposal of the harness. With `auto` the module id is the placeholder whose data the stage replaces after trying them all."""
    module = v.get("module", DEFAULTS["module"])
    return (DEFAULTS["module_placeholder"] if module == DEFAULTS["module"] else module), v.get("inverter", DEFAULTS["inverter"])


def _module_auto(v):
    return v.get("module", DEFAULTS["module"]) == DEFAULTS["module"]


def utc_offset(v):
    """The UTC offset of the form: the typed one, or the standard offset of the place (`epc_pv.timezone`); None when the place has no zone."""
    if "utc_offset_h" in v:
        return v["utc_offset_h"]
    import epc_pv.timezone as tz
    return tz.standard_utc_offset_h(v["latitude_deg"], v["longitude_deg"])


def _catalog_problem(v):
    """The first problem with the equipment chosen (unknown ids), or None. A data sheet gap (no Isc) is not a problem: the stage assumes the maximum input current and says so."""
    modules, inverters = catalogs()
    module, inverter = _equipment(v)
    sid = v.get("structure_id", "auto")
    if sid != "auto" and structures().get(sid) != ("ground" if v.get("mode") == "ground" else "roof"):
        return {"code": "pv_range", "detail": "structure_id"}      # unknown, or a ground structure on a roof (or the other way round)
    if module not in modules or (inverter != DEFAULTS["inverter"] and inverter not in inverters):
        return {"code": "pv_range", "detail": "module / inverter"}
    return None


def _plane_groups(v):
    """The answers each roof plane typed needs: width and length of the planes 2 to 4 that have any answer."""
    return [tuple(f"roof{n}_{k}" for k in ("width_m", "slope_m")) for n in EXTRA_PLANES if any(f"roof{n}_{k}" in v for k in PLANE_FIELDS)]


def _missing(v, building):
    """The first group of answers that is still missing (the site of a ground plant or the plane of a roof), or None."""
    groups = []      # the auxiliaries have a proposal (a project needs at least one load), so none is asked
    groups.append(("site_width_m", "site_length_m") if v["mode"] == "ground" else ("roof_width_m", "roof_slope_m"))
    gap = next((g for g in groups + _plane_groups(v) if not all(k in v for k in g)), None)
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
    if not out and utc_offset(v) is None:
        out = {"code": "pv_missing", "detail": "utc_offset_h"}      # no zone for this point (open sea or no database): the person types it
    return out or _catalog_problem(v) or _missing(v, building)


def _template(v, modules, inverters):
    """The module and inverter of the plant and the DC/AC ratio: what every array shares. `auto` leaves the inverter to the stage (it needs the modules that fit); a data sheet gap in Isc is
    filled only by what the person typed, otherwise the stage assumes and states it."""
    module_id, inverter_id = _equipment(v)
    ratio = v.get("dc_ac_ratio", DEFAULTS["dc_ac_ratio"])
    if inverter_id == DEFAULTS["inverter"]:
        inverter = DEFAULTS["inverter"]
    else:
        inverter = dict(inverters[inverter_id]["inverter"], id=inverter_id, model=inverters[inverter_id]["model"])
        if inverter.get("isc_max_input_a") is None and "isc_max_input_a" in v:
            inverter["isc_max_input_a"] = v["isc_max_input_a"]
    return {"module": dict(modules[module_id]["module"], **({"auto": True} if _module_auto(v) else {})), "inverter": inverter, "dc_ac_ratio": ratio}


def _n_modules(v, modules):
    """The modules of the power cap, or None when no power was asked (the structure is filled)."""
    if "target_kwp" not in v:
        return None
    import epc_pv.orient
    return epc_pv.orient.modules_for_kwp(v["target_kwp"], modules[_equipment(v)[0]]["module"]["pmax_w"])


def _array(v, modules, inverters):
    """The array of a ground plant; tilt and azimuth only when the person gave them (otherwise the engine chooses them). Without a power or a tilt the site is filled (`layout.fill`): the one module here is a placeholder."""
    given = {k: v[k] for k in ("tilt_deg", "azimuth_deg") if k in v}
    return {"id": "A1", "name": "A1", "n_modules": _n_modules(v, modules) or 1, **given, **_template(v, modules, inverters)}


def _flat_roof(v, modules, inverters):
    """Nothing is known about the roof (no pitch typed): it is assumed flat and the engine proposes the frames (`epc_pv.flatroof`)."""
    flat, lay = DEFAULTS["flat_roof"], DEFAULTS["layout"]
    return {"width_m": v["roof_width_m"], "length_m": v["roof_slope_m"], "setback_m": v.get("roof_setback_m", DEFAULTS["roof_setback_m"]), "walkway_m": flat["walkway_m"],
            "module_dimensions_mm": list(modules[_equipment(v)[0]]["dimensions_mm"][:2]), "module_gap_m": v.get("module_gap_m", lay["module_gap_m"]), "table": dict(flat["table"]),
            "table_gap_m": flat["table_gap_m"], "front_clearance_m": flat["front_clearance_m"], "station": dict(flat["station"]), "inverter_pad": dict(lay["inverter_pad"]),
            "array": _template(v, modules, inverters), **_structure(v), **_cap(v, modules)}


def _cap(v, modules):
    """The power cap only when typed (otherwise the structure is filled): `target_modules` for a fixed module, `target_kwp` when the stage still chooses the module."""
    if "target_kwp" not in v:
        return {}
    return {"target_kwp": v["target_kwp"]} if _module_auto(v) else {"target_modules": _n_modules(v, modules)}


def _more_planes(v):
    """The planes 2 to 4 typed in the form (each with its own orientation, never mixed with another on one MPPT: one plane is one array)."""
    out = []
    for n in EXTRA_PLANES:
        if f"roof{n}_width_m" in v:
            plane = {"id": f"R{n}", "width_m": v[f"roof{n}_width_m"], "slope_m": v[f"roof{n}_slope_m"], "setback_m": v.get("roof_setback_m", DEFAULTS["roof_setback_m"])}
            plane.update({k: v[f"roof{n}_{k}"] for k in ("tilt_deg", "azimuth_deg") if f"roof{n}_{k}" in v})
            out.append(plane)
    return out


def _roof(v, modules, inverters):
    """One roof plane typed in the form; the modules are placed by `epc_pv.plan_roof` and the orientation is the roof's or, when not given, the engine's."""
    plane = {"id": "R1", "width_m": v["roof_width_m"], "slope_m": v["roof_slope_m"], "setback_m": v.get("roof_setback_m", DEFAULTS["roof_setback_m"])}
    plane.update({k: v[k] for k in ("tilt_deg", "azimuth_deg") if k in v})
    return {"planes": [plane] + _more_planes(v), "module_dimensions_mm": list(modules[_equipment(v)[0]]["dimensions_mm"][:2]), "module_gap_m": v.get("module_gap_m", DEFAULTS["layout"]["module_gap_m"]),
            "array": _template(v, modules, inverters), **_cap(v, modules)}


def _layout(v, module):
    lay = DEFAULTS["layout"]
    pick = lambda k: v.get(k, lay[k])      # noqa: E731
    return {"site": {"width_m": v["site_width_m"], "length_m": v["site_length_m"], "setback_m": pick("setback_m")}, "module_dimensions_mm": list(module["dimensions_mm"][:2]),
            "module_gap_m": pick("module_gap_m"), "table": {"rows": int(pick("table_rows")), "modules_per_row": int(pick("table_modules_per_row")), "orientation": v.get("table_orientation", lay["table_orientation"])},
            "table_gap_m": pick("table_gap_m"), "road_width_m": pick("road_width_m"), "station": dict(lay["station"]), "inverter_pad": dict(lay["inverter_pad"])}


def _structure(v):
    """`structure_id` of the mounting structure when the person chose one (`auto` leaves it out: no foundation is assumed)."""
    return {"structure_id": v["structure_id"]} if v.get("structure_id", "auto") != "auto" else {}


def _ground_layout(v, modules):
    """The plant layout of a ground site; with no power cap and no tilt asked, `fill` tells the stage to fill the site with tables (a typed tilt fixes the fill's tilt too, see the stage)."""
    out = _layout(v, modules[_equipment(v)[0]])
    return dict(out, fill=True, front_clearance_m=DEFAULTS["layout"]["front_clearance_m"], **_structure(v), **_cap(v, modules))


def economics(v):
    """The client's own price (and cost) as the `economics` key of the section, or {} when no price was typed."""
    if "energy_price" not in v:
        return {}
    return {"economics": {"energy_price": v["energy_price"], "currency": v.get("currency", ""), **({"investment": v["investment"]} if "investment" in v else {})}}


def section(flat):
    """The `pv` section of `engine_inputs` from checked answers: the document without weather (it comes from the PVGIS file) and, for a ground plant, its layout."""
    v, _ = values_of(flat)
    modules, inverters = catalogs()
    site = {"latitude_deg": v["latitude_deg"], "longitude_deg": v["longitude_deg"], "albedo": v.get("albedo", DEFAULTS["albedo"])}
    if "design_t_min_c" in v:
        site["design_t_min_c"] = v["design_t_min_c"]
    return {**_plant(v, modules, inverters, site), **economics(v)}


def _plant(v, modules, inverters, site):
    """The plant part of the section (roof, flat roof or ground layout)."""
    if v["mode"] == "rooftop" and (v.get("roof_type", DEFAULTS["roof_type"]) == "pitched" or _more_planes(v)):      # more planes typed: the roof is not flat
        return {"document": {"site": site}, "weather_file": WEATHER_FILE, "roof": _roof(v, modules, inverters)}
    if v["mode"] == "rooftop":
        return {"document": {"site": site}, "weather_file": WEATHER_FILE, "flat_roof": _flat_roof(v, modules, inverters)}
    return {"document": {"site": site, "arrays": [_array(v, modules, inverters)]}, "weather_file": WEATHER_FILE, "layout": _ground_layout(v, modules)}


def board_of(flat):
    """The `board` section of `engine_inputs` of a plant-only project: its name and the power factor (the person's or the harness proposal, pending review)."""
    import house
    v, _ = values_of(flat)
    return {"name": house.DEFAULTS["board"]["name"], "fp_default": v.get("board_fp", house.DEFAULTS["board"]["fp_default"])}


def aux_loads(flat):
    """(areas, loads) of the load list of a plant-only project: the auxiliary services the person typed (monitoring, security, trackers). The plant generates; the load list only holds consumption (BACKLOG G5)."""
    v, _ = values_of(flat)
    aux = DEFAULTS["aux"]
    v = {"aux_load_kw": aux["load_kw"], "aux_phases": aux["phases"], "aux_length_m": aux["length_m"], **v}      # typical placeholder (pending review) unless typed
    load = {"id": "AUX-01", "description": "Plant auxiliary services / Servicios auxiliares de la planta", "area": "PV", "kind": "special",
            "power": {"value": v["aux_load_kw"], "unit": "kW"}, "phases": int(v["aux_phases"])}
    load["length"] = {"value": v["aux_length_m"], "unit": "m"}
    return [{"id": "PV", "name": "Planta fotovoltaica"}], [load]


def fetch_weather(flat):
    """The PVGIS file text for the site of the form (one call, the only network use of a PV project); raises `epc_pv.PvError` (English in `str`, Spanish in `.es`)."""
    import epc_pv.weather as W
    v, _ = values_of(flat)
    return json.dumps(W.fetch_tmy(v["latitude_deg"], v["longitude_deg"], utc_offset(v)), ensure_ascii=False, indent=1)
