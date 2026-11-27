"""The PV yield study as a report (blocks): arrays, monthly energy, equipment, alternatives compared, plant layout and roof structure.

Moved from `disciplines/electrical_lv/stages/rendering.py` with the same output. The report receives the result of `epc_pv` and, when it has it, the weight of one module; it reads
nothing and calls no engine (ADR-0043).
"""
from epc_report.core.blocks import PAGE_LABEL, notes, table
from epc_report.core.numbers import localize

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MONTHS_ES = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
ES_PAGE = "Página {n} de {total}"
# The words of the yield study in Spanish; English is the source text of the blocks below. A column that is not here keeps the generic Spanish heading the platform gives it.
ES = {"PV yield study": "Estudio de producción fotovoltaica", "Monthly AC energy (kWh)": "Energía mensual en alterna (kWh)", "Inverters (position in the layout)": "Inversores (posición en el layout)",
      "Alternatives compared (ground plant)": "Alternativas comparadas (planta en suelo)", "Equipment of the plant": "Equipo de la planta", "Plant layout": "Layout de la planta",
      "Roof structure (assumed flat roof)": "Estructura del techo (techo plano supuesto)", "Assumptions": "Supuestos", "Open issues": "Pendientes", "total": "total",
      "inverter": "inversor", "model": "modelo", "x_m": "x (m)", "y_m": "y (m)", "tilt_deg": "inclinación (°)", "structure": "estructura", "energy_index": "índice de energía", "dc_kwp": "CC (kWp)",
      "ac_kw": "CA (kW)", "dc_ac_ratio": "relación CC/CA", "poa_kwh_m2": "irradiación en el plano (kWh/m²)", "modules_per_string": "módulos por string", "strings_per_inverter": "strings por inversor",
      "x": "x", "name": "nombre", "month": "mes", "array": "arreglo", "modules": "módulos", "inverters": "inversores", "modules_in_series": "módulos en serie", "strings": "strings",
      "ac_kwh": "energía CA (kWh)", "kwh_per_kwp": "kWh/kWp", "pr": "PR", "cf": "factor de capacidad"}


def _words(lang, text):
    return ES.get(text, text) if lang == "es" else text


SENTENCES = {
    "counts": ("Arrays: {arrays}; inverters: {inverters}; modules: {modules}; hours simulated: {hours}. Engine {engine} {version}.",
               "Arreglos: {arrays}; inversores: {inverters}; módulos: {modules}; horas simuladas: {hours}. Motor {engine} {version}."),
    "total": ("Total: DC {dc} kWp, AC {ac} kW, {kwh} kWh per year, specific yield {sy} kWh/kWp, clipping {clip} kWh.",
              "Total: CC {dc} kWp, CA {ac} kW, {kwh} kWh por año, rendimiento específico {sy} kWh/kWp, recorte {clip} kWh."),
    "weight": ("Module weight (record of the module format): {each:g} kg each, {t:.1f} t in total. Loads on the structure and the roof are not checked.",
               "Peso de los módulos (registro del formato de módulo): {each:g} kg cada uno, {t:.1f} t en total. No se verifican las cargas sobre la estructura ni el techo."),
    "chosen": ("Chosen: tilt {tilt:g} deg, azimuth {az:g} deg, {modules} module(s) in {frames} table(s).", "Elegido: inclinación {tilt:g} °, azimut {az:g} °, {modules} módulo(s) en {frames} mesa(s)."),
    "structures": ("Structures tried on the same site (best first; the structure of the project is the one the person gave, and the foundation and cost of each are not compared):",
                   "Estructuras probadas en el mismo predio (la mejor primero; la estructura del proyecto es la que dio la persona, y no se comparan la fundación ni el costo de cada una):"),
    "layout": ("Tables: {tables} in {rows} row(s); row pitch {pitch} m; solar altitude at the design hour {alt} deg; site {w} x {l} m; all tables inside the site: {fits}.",
               "Mesas: {tables} en {rows} fila(s); paso entre filas {pitch} m; altura solar a la hora de diseño {alt} °; predio {w} x {l} m; todas las mesas dentro del predio: {fits}."),
    "yes": ("yes", "sí"), "no": ("no", "no"),
    "flat": ("No roof information was given: the roof is assumed flat and the modules go on tilted frames facing the equator. Tilt {tilt:g} deg, azimuth {az:g} deg (from north), chosen as the most energy from the roof. "
             "{frames} frame(s) of {per} module(s), frame {fw} x {fs} m, front height {fh} m, rear height {rh} m, row pitch {rp} m. Not calculated: {nc}.",
             "No se dio información del techo: se supone plano y los módulos van en bastidores inclinados mirando al ecuador. Inclinación {tilt:g} °, azimut {az:g} ° (desde el norte), elegidos por dar la mayor energía del techo. "
             "{frames} bastidor(es) de {per} módulo(s), bastidor {fw} x {fs} m, altura delantera {fh} m, altura trasera {rh} m, paso entre filas {rp} m. No calculado: {nc}."),
}


def _t(lang, key, **fmt):
    return SENTENCES[key][1 if lang == "es" else 0].format(**fmt)


def _heads(lang, columns):
    return [_words(lang, c) for c in columns]


def array_rows(arrays):
    """One row per array and a total row: modules, strings, modules per string, inverters, strings per inverter."""
    rows = [[a["id"], a["modules"], a["strings"]["strings"], a["strings"]["n_series"], a["inverters"], a["strings"]["strings_per_inverter"]] for a in arrays]
    return rows + [["total", sum(a["modules"] for a in arrays), sum(a["strings"]["strings"] for a in arrays), "", sum(a["inverters"] for a in arrays), ""]]


def inverter_blocks(result, lang="en"):
    placed = [i for i in (result.get("layout") or {}).get("inverters", []) if i.get("x") is not None]
    rows = [[i["id"], i.get("catalog_id") or "", round(i["x"], 2), round(i["y"], 2)] for i in placed]
    return [{"type": "h", "text": _words(lang, "Inverters (position in the layout)")}, table(_heads(lang, ["inverter", "model", "x_m", "y_m"]), rows)] if rows else []


def fill_blocks(result, lang="en"):
    """The alternatives the harness compared for a ground plant filled to its site: the tilts tried and the structures tried on the same site (relative energy: modules x kWh/kWp). Cost is not compared."""
    fill = result.get("site_fill")
    if not fill:
        return []
    blocks = [{"type": "h", "text": _words(lang, "Alternatives compared (ground plant)")},
              {"type": "p", "text": _t(lang, "chosen", tilt=fill["tilt_deg"], az=fill["azimuth_deg"], modules=fill["modules"], frames=fill["structure"]["frames"])},
              table(_heads(lang, ["tilt_deg", "modules", "kwh_per_kwp"]), [[o["tilt_deg"], o["modules"], o["specific_yield_kwh_kwp"]] for o in fill["options"]])]
    rows = fill.get("structure_options") or []
    if rows:
        blocks += [{"type": "p", "text": _t(lang, "structures")},
                   table(_heads(lang, ["structure", "tilt_deg", "modules", "kwh_per_kwp", "energy_index"]), [[r["structure_id"], r["tilt_deg"], r["modules"], r["specific_yield_kwh_kwp"], r["energy_index"]] for r in rows])]
    return blocks


def weight_blocks(result, module_weight_kg=None, lang="en"):
    """The weight of the modules when the caller gives the weight of one (`module_weight_kg`, from the module format record): each and in total. A load figure for the structure designer, not a structural check."""
    each = module_weight_kg
    if each is None:
        return []
    total = each * sum(a["modules"] for a in result["arrays"])
    return [{"type": "p", "text": _t(lang, "weight", each=each, t=total / 1000.0)}]


def equipment_blocks(result, module_weight_kg=None, lang="en"):
    """The equipment the plant needs, as the engine counted it (nothing is added): modules, strings and inverters per array with the totals, and one line per inverter of the layout (its model and position)."""
    columns = _heads(lang, ["array", "modules", "strings", "modules_per_string", "inverters", "strings_per_inverter"])
    head = [{"type": "h", "text": _words(lang, "Equipment of the plant")}, table(columns, [[_words(lang, c) if c == "total" else c for c in row] for row in array_rows(result["arrays"])])]
    return head + inverter_blocks(result, lang) + weight_blocks(result, module_weight_kg, lang)


def _notes(lang, warnings):
    """The open issues in the language of the report (the engine gives each warning in English and Spanish)."""
    key = "es" if lang == "es" else "en"
    return notes({"issues": [w[key] for w in warnings]}) if not lang == "es" else [dict(b, text=_words(lang, b["text"])) if b["type"] == "h" else b for b in notes({"issues": [w[key] for w in warnings]})]


def _flat_blocks(result, lang):
    flat = result.get("flat_roof")
    if not flat:
        return []
    st = flat["structure"]
    text = _t(lang, "flat", tilt=flat["tilt_deg"], az=flat["azimuth_deg"], frames=st["frames"], per=st["modules_per_frame"], fw=st["frame_width_m"], fs=st["frame_slope_m"], fh=st["front_height_m"],
              rh=st["rear_height_m"], rp=st["row_pitch_m"], nc=st["not_calculated"]["es" if lang == "es" else "en"])
    return [{"type": "h", "text": _words(lang, "Roof structure (assumed flat roof)")}, {"type": "p", "text": text},
            table(_heads(lang, ["tilt_deg", "modules", "kwh_per_kwp"]), [[o["tilt_deg"], o["modules"], o["specific_yield_kwh_kwp"]] for o in flat["options"]])]


def _layout_blocks(result, lang):
    plan = result.get("layout")
    if not plan:
        return []
    fits = _t(lang, "yes" if plan["fits"] else "no")
    return [{"type": "h", "text": _words(lang, "Plant layout")},
            {"type": "p", "text": _t(lang, "layout", tables=plan["counts"]["tables"], rows=plan["counts"]["rows"], pitch=", ".join(str(p) for p in plan["pitch_m"]), alt=plan["solar_altitude_deg"],
                                     w=plan["site"]["width_m"], l=plan["site"]["length_m"], fits=fits)}]


def pv_yield_report(d, project, module_weight_kg=None, lang="en"):
    """The yield study in `lang` (`en` or `es`): every heading, sentence, column and month is written in that language and the numbers follow its separators."""
    result = d["result"]
    layout_rows = [[a["id"], a["modules"], a["inverters"], a["dc_kwp"], a["ac_kw"], a["dc_ac_ratio"], a["strings"]["n_series"], a["strings"]["strings"]] for a in result["arrays"]]
    yield_rows = [[a["id"], a["poa_kwh_m2"], a["ac_kwh"], a["specific_yield_kwh_kwp"], a["performance_ratio"], a["capacity_factor"]] for a in result["arrays"]]
    totals, counts = result["totals"], result["counts"]
    months = [[m, round(a, 1)] for m, a in zip(MONTHS_ES if lang == "es" else MONTHS, totals["monthly_ac_kwh"])]
    en = lang != "es"
    blocks = [{"type": "p", "text": _t(lang, "counts", arrays=counts["arrays"], inverters=counts["inverters"], modules=counts["modules"], hours=counts["hours"], engine=d["engine"]["name"], version=d["engine"]["version"])},
              table(_heads(lang, ["array", "modules", "inverters", "dc_kwp", "ac_kw", "dc_ac_ratio", "modules_in_series", "strings"]), layout_rows),
              table(_heads(lang, ["array", "poa_kwh_m2", "ac_kwh", "kwh_per_kwp", "pr", "cf"]), yield_rows),
              {"type": "h", "text": _words(lang, "Monthly AC energy (kWh)")}, table(_heads(lang, ["month", "ac_kwh"]), months),
              {"type": "p", "text": _t(lang, "total", dc=totals["dc_kwp"], ac=totals["ac_kw"], kwh=totals["ac_kwh"], sy=totals["specific_yield_kwh_kwp"], clip=totals["clipping_kwh"])}]
    blocks += equipment_blocks(result, module_weight_kg, lang) + fill_blocks(result, lang) + _layout_blocks(result, lang) + _flat_blocks(result, lang)
    title = _words(lang, "PV yield study")
    report = {"title": title, "subtitle": project, "footer": f"{title} - {project}", "page_label": PAGE_LABEL if en else ES_PAGE, "blocks": blocks + _notes(lang, result["warnings"])}
    return report if en else localize(report, "es")
