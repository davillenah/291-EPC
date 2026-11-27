"""The PV project summary (ADR-0043): one page, data without explanation, at most three observations. Built from the result of `epc_pv` and its input; nothing is calculated.

What no engine gives yet (cables, protections, earthing) is written 'not available'; it is never filled in by hand."""
from epc_report.core.blocks import table
from epc_report.pv.calc_memo import count_states
from epc_report.pv.texts import tr

MAX_OBSERVATIONS = 3


def _first_array(result, inputs):
    a = result["arrays"][0]
    spec = next((s for s in inputs.get("arrays", []) if str(s["id"]) == str(a["id"])), None) or (inputs.get("arrays") or [{}])[0]
    return a, spec


def _location(site, na):
    return f"{site['latitude_deg']}, {site['longitude_deg']}" if "latitude_deg" in site else na


def _rows(lang, d, inputs, problem):
    """The requirement | technical data rows: every value from the engine result or its input, 'not available' where neither has it."""
    result = d["result"]
    a, spec = _first_array(result, inputs)
    ok, no, nv = count_states(lang, result["arrays"])
    totals, na = result["totals"], tr(lang, "n_a")
    module, inverter, strings = spec.get("module") or {}, spec.get("inverter") or {}, a["strings"]
    return [[tr(lang, "problem"), problem],
            [tr(lang, "solution"), tr(lang, "plant", kwp=totals["dc_kwp"], kw=totals["ac_kw"])],
            [tr(lang, "location"), _location(inputs.get("site") or {}, na)],
            [tr(lang, "modules"), f"{sum(x['modules'] for x in result['arrays'])} × {module.get('model', na)} ({module.get('pmax_w', na)} Wp)"],
            [tr(lang, "strings"), tr(lang, "strings_line", strings=strings["strings"], n_series=strings["n_series"], mppt=strings["strings_per_mppt"], limit=strings["strings_per_mppt_limit"])],
            [tr(lang, "inverters"), f"{sum(x['inverters'] for x in result['arrays'])} × {inverter.get('model', na)} ({a['inverter_ac_kw']} kW); {tr(lang, 'c_ratio')} {a['dc_ac_ratio']}"],
            [tr(lang, "dc_cable"), na], [tr(lang, "ac_cable"), na], [tr(lang, "protections"), na], [tr(lang, "earthing"), na],
            [tr(lang, "energy"), tr(lang, "energy_line", kwh=totals["ac_kwh"], yield_=totals["specific_yield_kwh_kwp"])],
            [tr(lang, "compliance"), tr(lang, "compl_line", ok=ok, no=no, nv=nv)]]


def pv_summary(d, inputs, project, problem, lang="en"):
    """The summary as a report structure. `problem` is the one-line text the owner gave (consumption, tariff); `d` and `inputs` as in the memorandum."""
    result = d["result"]
    totals = result["totals"]
    warns = [w[lang] for w in result.get("warnings", [])][:MAX_OBSERVATIONS]
    blocks = [{"type": "p", "text": tr(lang, "edit_mode")}, table([tr(lang, "req"), tr(lang, "tech")], _rows(lang, d, inputs, problem))]
    if warns:
        blocks += [{"type": "h", "text": tr(lang, "obs")}, {"type": "bullets", "items": warns}]
    return {"title": tr(lang, "summary_title"), "subtitle": project, "footer": f"{tr(lang, 'summary_title')} - {project}", "blocks": blocks,
            "facts": {"pv.dc_kwp": totals["dc_kwp"], "pv.ac_kw": totals["ac_kw"], "pv.ac_kwh": totals["ac_kwh"], "pv.modules": sum(x["modules"] for x in result["arrays"])}}
