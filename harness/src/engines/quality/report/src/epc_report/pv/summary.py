"""The PV project summary (ADR-0043): one page, data without explanation, at most three observations. Built from the result of `epc_pv` and its input; nothing is calculated.

What no engine gives yet (cables, protections, earthing) is written 'not available'; it is never filled in by hand."""
from epc_report.core.blocks import table
from epc_report.pv.calc_memo import count_states
from epc_report.pv.texts import tr

MAX_OBSERVATIONS = 3


def _first_array(result, inputs):
    a = result["arrays"][0]
    spec = next(s for s in inputs["arrays"] if str(s["id"]) == str(a["id"]))
    return a, spec


def pv_summary(d, inputs, project, problem, lang="en"):
    """The summary as a report structure. `problem` is the one-line text the owner gave (consumption, tariff); `d` and `inputs` as in the memorandum."""
    result = d["result"]
    totals = result["totals"]
    a, spec = _first_array(result, inputs)
    na = tr(lang, "n_a")
    ok, no, nv = count_states(lang, result["arrays"])
    site = inputs["site"]
    rows = [[tr(lang, "problem"), problem],
            [tr(lang, "solution"), tr(lang, "plant", kwp=totals["dc_kwp"], kw=totals["ac_kw"])],
            [tr(lang, "location"), f"{site['latitude_deg']}, {site['longitude_deg']}"],
            [tr(lang, "modules"), f"{sum(x['modules'] for x in result['arrays'])} × {spec['module'].get('model', na)} ({spec['module']['pmax_w']} Wp)"],
            [tr(lang, "strings"), tr(lang, "strings_line", strings=a["strings"]["strings"], n_series=a["strings"]["n_series"], mppt=a["strings"]["strings_per_mppt"], limit=a["strings"]["strings_per_mppt_limit"])],
            [tr(lang, "inverters"), f"{sum(x['inverters'] for x in result['arrays'])} × {spec['inverter'].get('model', na)} ({a['inverter_ac_kw']} kW); {tr(lang, 'c_ratio')} {a['dc_ac_ratio']}"],
            [tr(lang, "dc_cable"), na], [tr(lang, "ac_cable"), na], [tr(lang, "protections"), na], [tr(lang, "earthing"), na],
            [tr(lang, "energy"), tr(lang, "energy_line", kwh=totals["ac_kwh"], yield_=totals["specific_yield_kwh_kwp"])],
            [tr(lang, "compliance"), tr(lang, "compl_line", ok=ok, no=no, nv=nv)]]
    warns = [w[lang] for w in result.get("warnings", [])][:MAX_OBSERVATIONS]
    blocks = [{"type": "p", "text": tr(lang, "edit_mode")}, table([tr(lang, "req"), tr(lang, "tech")], rows)]
    if warns:
        blocks += [{"type": "h", "text": tr(lang, "obs")}, {"type": "bullets", "items": warns}]
    return {"title": tr(lang, "summary_title"), "subtitle": project, "footer": f"{tr(lang, 'summary_title')} - {project}", "blocks": blocks,
            "facts": {"pv.dc_kwp": totals["dc_kwp"], "pv.ac_kw": totals["ac_kw"], "pv.ac_kwh": totals["ac_kwh"], "pv.modules": sum(x["modules"] for x in result["arrays"])}}
