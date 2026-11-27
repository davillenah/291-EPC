"""The PV yield study as a report (blocks): arrays, monthly energy, equipment, alternatives compared, plant layout and roof structure.

Moved from `disciplines/electrical_lv/stages/rendering.py` with the same output. The report receives the result of `epc_pv` and, when it has it, the weight of one module; it reads
nothing and calls no engine (ADR-0043).
"""
from epc_report.core.blocks import PAGE_LABEL, notes, table

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def array_rows(arrays):
    """One row per array and a total row: modules, strings, modules per string, inverters, strings per inverter."""
    rows = [[a["id"], a["modules"], a["strings"]["strings"], a["strings"]["n_series"], a["inverters"], a["strings"]["strings_per_inverter"]] for a in arrays]
    return rows + [["total", sum(a["modules"] for a in arrays), sum(a["strings"]["strings"] for a in arrays), "", sum(a["inverters"] for a in arrays), ""]]


def inverter_blocks(result):
    placed = [i for i in (result.get("layout") or {}).get("inverters", []) if i.get("x") is not None]
    rows = [[i["id"], i.get("catalog_id") or "", round(i["x"], 2), round(i["y"], 2)] for i in placed]
    return [{"type": "h", "text": "Inverters (position in the layout)"}, table(["inverter", "model", "x_m", "y_m"], rows)] if rows else []


def fill_blocks(result):
    """The alternatives the harness compared for a ground plant filled to its site: the tilts tried and the structures tried on the same site (relative energy: modules x kWh/kWp). Cost is not compared."""
    fill = result.get("site_fill")
    if not fill:
        return []
    blocks = [{"type": "h", "text": "Alternatives compared (ground plant)"},
              {"type": "p", "text": f"Chosen: tilt {fill['tilt_deg']:g} deg, azimuth {fill['azimuth_deg']:g} deg, {fill['modules']} module(s) in {fill['structure']['frames']} table(s)."},
              table(["tilt_deg", "modules", "kwh_per_kwp"], [[o["tilt_deg"], o["modules"], o["specific_yield_kwh_kwp"]] for o in fill["options"]])]
    rows = fill.get("structure_options") or []
    if rows:
        blocks += [{"type": "p", "text": "Structures tried on the same site (best first; the structure of the project is the one the person gave, and the foundation and cost of each are not compared):"},
                   table(["structure", "tilt_deg", "modules", "kwh_per_kwp", "energy_index"], [[r["structure_id"], r["tilt_deg"], r["modules"], r["specific_yield_kwh_kwp"], r["energy_index"]] for r in rows])]
    return blocks


def weight_blocks(result, module_weight_kg=None):
    """The weight of the modules when the caller gives the weight of one (`module_weight_kg`, from the module format record): each and in total. A load figure for the structure designer, not a structural check."""
    each = module_weight_kg
    if each is None:
        return []
    total = each * sum(a["modules"] for a in result["arrays"])
    return [{"type": "p", "text": f"Module weight (record of the module format): {each:g} kg each, {total / 1000.0:.1f} t in total. Loads on the structure and the roof are not checked."}]


def equipment_blocks(result, module_weight_kg=None):
    """The equipment the plant needs, as the engine counted it (nothing is added): modules, strings and inverters per array with the totals, and one line per inverter of the layout (its model and position)."""
    head = [{"type": "h", "text": "Equipment of the plant"}, table(["array", "modules", "strings", "modules_per_string", "inverters", "strings_per_inverter"], array_rows(result["arrays"]))]
    return head + inverter_blocks(result) + weight_blocks(result, module_weight_kg)


def pv_yield_report(d, project, module_weight_kg=None):
    result = d["result"]
    layout_rows = [[a["id"], a["modules"], a["inverters"], a["dc_kwp"], a["ac_kw"], a["dc_ac_ratio"], a["strings"]["n_series"], a["strings"]["strings"]] for a in result["arrays"]]
    yield_rows = [[a["id"], a["poa_kwh_m2"], a["ac_kwh"], a["specific_yield_kwh_kwp"], a["performance_ratio"], a["capacity_factor"]] for a in result["arrays"]]
    totals = result["totals"]
    months = [[m, round(a, 1)] for m, a in zip(MONTHS, totals["monthly_ac_kwh"])]
    warnings = [f"{w['en']} / {w['es']}" for w in result["warnings"]]
    counts = result["counts"]
    blocks = [{"type": "p", "text": f"Arrays: {counts['arrays']}; inverters: {counts['inverters']}; modules: {counts['modules']}; hours simulated: {counts['hours']}. Engine {d['engine']['name']} {d['engine']['version']}."},
              table(["array", "modules", "inverters", "dc_kwp", "ac_kw", "dc_ac_ratio", "modules_in_series", "strings"], layout_rows),
              table(["array", "poa_kwh_m2", "ac_kwh", "kwh_per_kwp", "pr", "cf"], yield_rows),
              {"type": "h", "text": "Monthly AC energy (kWh)"}, table(["month", "ac_kwh"], months),
              {"type": "p", "text": f"Total: DC {totals['dc_kwp']} kWp, AC {totals['ac_kw']} kW, {totals['ac_kwh']} kWh per year, specific yield {totals['specific_yield_kwh_kwp']} kWh/kWp, clipping {totals['clipping_kwh']} kWh."}]
    blocks += equipment_blocks(result, module_weight_kg) + fill_blocks(result)
    plan = result.get("layout")
    if plan:
        blocks += [{"type": "h", "text": "Plant layout"},
                   {"type": "p", "text": f"Tables: {plan['counts']['tables']} in {plan['counts']['rows']} row(s); row pitch {', '.join(str(p) for p in plan['pitch_m'])} m; solar altitude at the design hour {plan['solar_altitude_deg']} deg; "
                                         f"site {plan['site']['width_m']} x {plan['site']['length_m']} m; all tables inside the site: {'yes' if plan['fits'] else 'no'}."}]
    flat = result.get("flat_roof")
    if flat:
        st = flat["structure"]
        blocks += [{"type": "h", "text": "Roof structure (assumed flat roof)"},
                   {"type": "p", "text": f"No roof information was given: the roof is assumed flat and the modules go on tilted frames facing the equator. Tilt {flat['tilt_deg']:g} deg, azimuth {flat['azimuth_deg']:g} deg "
                                         f"(from north), chosen as the most energy from the roof. {st['frames']} frame(s) of {st['modules_per_frame']} module(s), frame {st['frame_width_m']} x {st['frame_slope_m']} m, "
                                         f"front height {st['front_height_m']} m, rear height {st['rear_height_m']} m, row pitch {st['row_pitch_m']} m. "
                                         f"Not calculated: {st['not_calculated']['en']}. / No calculado: {st['not_calculated']['es']}."},
                   table(["tilt_deg", "modules", "kwh_per_kwp"], [[o["tilt_deg"], o["modules"], o["specific_yield_kwh_kwp"]] for o in flat["options"]])]
    return {"title": "PV yield study", "subtitle": project, "footer": f"PV yield study - {project}", "page_label": PAGE_LABEL, "blocks": blocks + notes({"issues": warnings})}
