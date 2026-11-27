"""The PV calculation memorandum (ADR-0043): data, formula, substitution, result, criterion and verdict, with a transition paragraph between sections.

It is built from the result of `epc_pv` and the input document the engine received. It calculates nothing: every number is read from one of the two, a quantity the engine
does not return is written 'not available', and a calculation no engine does yet is listed as 'not verified'. A verdict is a comparison of two numbers the engine gave.
"""
from epc_report.core.blocks import table
from epc_report.core.numbers import localize
from epc_report.pv.texts import tr


def _calc(lang, ident, name_key, data, formula, subst, result, criterion, verdict):
    rows = [(tr(lang, "data"), data), (tr(lang, "formula"), formula), (tr(lang, "subst"), subst), (tr(lang, "result"), result), (tr(lang, "criterion"), criterion), (tr(lang, "check"), tr(lang, verdict))]
    return [{"type": "h", "text": f"[{ident}] {tr(lang, name_key)}"}, table([tr(lang, "col_calc"), ""], rows)]


def _series_substitution(lang, rng, inv):
    """The substitution of the series formula with the voltages and floors the engine returned; the text `not available` when the engine result or the inverter data are missing."""
    if not isinstance(inv, dict) or "voc_cold_v" not in rng or not all(k in inv for k in ("vdc_max_v", "mppt_v_max", "mppt_v_min")):
        return tr(lang, "not_returned")
    return (f"N_s,max = min(⌊{inv['vdc_max_v']} / {rng['voc_cold_v']}⌋, ⌊{inv['mppt_v_max']} / {rng['vmp_cold_v']}⌋) = min({rng['n_by_vdc_max']}, {rng['n_by_mppt_max']}) = {rng['s_max']};  "
            f"N_s,min = ⌈{inv['mppt_v_min']} / {rng['vmp_hot_v']}⌉ = {rng['s_min']}")


def _series(lang, array, spec):
    s = array["strings"]
    mod, inv = (spec or {}).get("module"), (spec or {}).get("inverter")
    if isinstance(mod, dict) and isinstance(inv, dict):
        data = f"Voc = {mod['voc_v']} V, Vmp = {mod['vmp_v']} V, βVoc = {mod['beta_voc_pct_c']} %/°C; Vdc,max = {inv['vdc_max_v']} V, MPPT {inv['mppt_v_min']}-{inv['mppt_v_max']} V"
    else:
        data = tr(lang, "n_a")                      # the array comes from a roof plane or a site fill: its module and inverter data are not in the input under this id
    rng = s["series_range"]
    ok = rng["s_min"] <= s["n_series"] <= rng["s_max"]
    return _calc(lang, "C-05 / C-07 / C-08", "c_series", data, "N_s,max = min(⌊Vdc,max / Voc(Tmin)⌋, ⌊Vmppt,max / Vmp(Tmin)⌋);  N_s,min = ⌈Vmppt,min / Vmp(Tc,max)⌉",
                 _series_substitution(lang, rng, inv), f"N_s,min = {rng['s_min']}; N_s,max = {rng['s_max']}; N_s = {s['n_series']}", f"{rng['s_min']} ≤ N_s ≤ {rng['s_max']}", "complies" if ok else "fails")


def _mppt_substitution(lang, s, spec):
    """The substitution of the current limit with the inverter and module data of the array and the limit the engine returned; `not available` without that data."""
    mod, inv = (spec or {}).get("module"), (spec or {}).get("inverter")
    if not (isinstance(mod, dict) and isinstance(inv, dict) and "imp_a" in mod and "i_max_input_a" in inv):
        return tr(lang, "not_returned")
    return f"N_p ≤ ⌊{inv['i_max_input_a']} / {mod['imp_a']}⌋ = {s['strings_per_mppt_limit']}" + ("" if inv.get("isc_max_input_a") is None else f" (Isc,max = {inv['isc_max_input_a']} A)")


def _mppt(lang, array, spec=None):
    s = array["strings"]
    return _calc(lang, "C-09", "c_mppt", f"strings/inverter = {s['strings_per_inverter']}", "N_p ≤ ⌊I_mppt,max / I_mp⌋  and  N_p ≤ ⌊Isc,max / (k·Isc)⌋", _mppt_substitution(lang, s, spec),
                 f"N_p = {s['strings_per_mppt']}", f"N_p ≤ {s['strings_per_mppt_limit']}", "complies" if s["strings_per_mppt"] <= s["strings_per_mppt_limit"] else "fails")


def _ratio(lang, array):
    return _calc(lang, "C-10", "c_ratio", f"N = {array['modules']}; N_inv = {array['inverters']} × {array['inverter_ac_kw']} kW", "P_dc = N_modules · Pmp;  R = P_dc / P_ac,total",
                 f"P_dc = {array['dc_kwp']} kWp; P_ac,total = {array['ac_kw']} kW", f"R = {array['dc_ac_ratio']}", tr(lang, "ratio_pending"), "not_verified")


def _energy(lang, array):
    return _calc(lang, "C-13", "c_energy", f"H_POA = {array['poa_kwh_m2']} kWh/m²", "E = Σ P_ac·Δt;  Y_f = E / P_dc;  PR = Y_f / H_POA;  FC = E / (P_ac·8760)", tr(lang, "not_returned"),
                 f"E = {array['ac_kwh']} kWh; Y_f = {array['specific_yield_kwh_kwp']} kWh/kWp; PR = {array['performance_ratio']}; FC = {array['capacity_factor']}", "-", "not_verified")


def _shading(lang, result, specs):
    from epc_report.pv.shading_section import shading_blocks      # imported here: the section reads `_calc` of this module
    return shading_blocks(lang, result, specs)


def verifications(lang, arrays):
    """The rows of the summary table: one per array and calculation, with the verdict the sections reached."""
    rows = []
    for a in arrays:
        s, rng = a["strings"], a["strings"]["series_range"]
        ok1 = rng["s_min"] <= s["n_series"] <= rng["s_max"]
        ok2 = s["strings_per_mppt"] <= s["strings_per_mppt_limit"]
        rows += [[f"{a['id']} C-08", "N_s", s["n_series"], f"{rng['s_min']}-{rng['s_max']}", tr(lang, "complies" if ok1 else "fails")],
                 [f"{a['id']} C-09", "N_p", s["strings_per_mppt"], f"≤ {s['strings_per_mppt_limit']}", tr(lang, "complies" if ok2 else "fails")],
                 [f"{a['id']} C-10", "R", a["dc_ac_ratio"], "-", tr(lang, "not_verified")]]
    return rows


def count_states(lang, arrays):
    """How many verifications comply, do not comply and are not verified (from the table rows, nothing else)."""
    states = [r[4] for r in verifications(lang, arrays)]
    return [states.count(tr(lang, k)) for k in ("complies", "fails", "not_verified")]


def pv_calc_memo(d, inputs, project, lang="en"):
    """The memorandum as a report structure. `d` is the document of `epc_pv` (`result`, `engine`); `inputs` the document the engine received (`site`, `arrays` with `module` and `inverter`)."""
    result, specs = d["result"], {str(s["id"]): s for s in inputs.get("arrays", [])}
    blocks = [{"type": "p", "text": tr(lang, "engine_line", name=d["engine"]["name"], version=d["engine"]["version"]) + " " + tr(lang, "edit_mode")},
              {"type": "h", "text": tr(lang, "h_input")}, {"type": "p", "text": tr(lang, "t_input")}, {"type": "h", "text": tr(lang, "h_strings")}, {"type": "p", "text": tr(lang, "l_strings")}]
    for a in result["arrays"]:
        blocks += _series(lang, a, specs.get(str(a["id"]))) + _mppt(lang, a, specs.get(str(a["id"])))
    blocks += [{"type": "p", "text": tr(lang, "t_strings")}, {"type": "h", "text": tr(lang, "h_power")}, {"type": "p", "text": tr(lang, "l_power")}]
    for a in result["arrays"]:
        blocks += _ratio(lang, a)
    blocks += [{"type": "p", "text": tr(lang, "t_power")}, {"type": "h", "text": tr(lang, "h_energy")}, {"type": "p", "text": tr(lang, "l_energy")}]
    for a in result["arrays"]:
        blocks += _energy(lang, a)
    blocks += [{"type": "p", "text": tr(lang, "t_energy")}] + _shading(lang, result, specs)
    blocks += [{"type": "h", "text": tr(lang, "h_pending")}, {"type": "p", "text": tr(lang, "pending_list")},
               {"type": "p", "text": tr(lang, "t_pending")}, {"type": "h", "text": tr(lang, "h_summary")},
               table([tr(lang, k) for k in ("col_calc", "col_mag", "col_val", "col_lim", "col_state")], verifications(lang, result["arrays"]))]
    totals = result["totals"]
    return localize({"title": tr(lang, "memo_title"), "subtitle": project, "footer": f"{tr(lang, 'memo_title')} - {project}", "blocks": blocks,
                     "facts": {"pv.dc_kwp": totals["dc_kwp"], "pv.ac_kw": totals["ac_kw"], "pv.ac_kwh": totals["ac_kwh"], "pv.modules": sum(a["modules"] for a in result["arrays"])}}, lang)
