"""The PV savings and economic calculation memorandums (ADR-0043), two separate documents: the first states the saving, the second compares it with the investment.

They read the `economic` block of the stage (`technical_feasibility.economic`, computed outside this engine) and the energy of the engine result; they calculate nothing. A quantity that was
not given (the client's price, the investment) is written 'not verified', never assumed.
"""
from epc_report.core.blocks import table
from epc_report.pv.calc_memo import _calc
from epc_report.pv.texts import tr

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def economic_of(d):
    """The economic block of the document, or None when the client's price was not given (the block is then a text with `en` and `es`)."""
    eco = (d["result"].get("technical_feasibility") or {}).get("economic")
    return eco if eco and "saving_year" in eco else None


def _facts(d):
    totals = d["result"]["totals"]
    return {"pv.dc_kwp": totals["dc_kwp"], "pv.ac_kw": totals["ac_kw"], "pv.ac_kwh": totals["ac_kwh"]}


def _frame(lang, d, project, title, blocks, facts):
    return {"title": tr(lang, title), "subtitle": project, "footer": f"{tr(lang, title)} - {project}", "blocks": blocks, "facts": facts}


def pv_savings_memo(d, project, lang="en"):
    """The savings memorandum: yearly saving = yearly energy x the client's price, and its monthly distribution."""
    eco, facts = economic_of(d), _facts(d)
    blocks = [{"type": "p", "text": tr(lang, "engine_line", name=d["engine"]["name"], version=d["engine"]["version"]) + " " + tr(lang, "edit_mode")},
              {"type": "h", "text": tr(lang, "h_sav_data")}]
    if eco is None:
        blocks += [{"type": "p", "text": tr(lang, "no_price")}]
        return _frame(lang, d, project, "sav_title", blocks, facts)
    cur = eco["currency"]
    blocks += [table([tr(lang, "col_calc"), tr(lang, "col_val")], [[tr(lang, "d_energy"), f"{eco['energy_kwh_year']} kWh/year"], [tr(lang, "d_price"), f"{eco['energy_price']} {cur}/kWh"],
                                                                    [tr(lang, "assumes"), eco["assumes"][lang]]]),
               {"type": "p", "text": tr(lang, "t_sav_data")}, {"type": "h", "text": tr(lang, "h_sav_year")}, {"type": "p", "text": tr(lang, "l_sav_year")}]
    blocks += _calc(lang, "S-01", "c_saving", f"E = {eco['energy_kwh_year']} kWh/year; p = {eco['energy_price']} {cur}/kWh", "A = E · p",
                    f"A = {eco['energy_kwh_year']} kWh × {eco['energy_price']} {cur}/kWh", f"A = {eco['saving_year']} {cur}/year", "-", "not_verified")
    months = d["result"]["totals"]["monthly_ac_kwh"]
    rows = [[m, e, s] for m, e, s in zip(MONTHS, months, eco["saving_month"])]
    blocks += [{"type": "p", "text": tr(lang, "t_sav_year")}, {"type": "h", "text": tr(lang, "h_sav_month")}, table([tr(lang, "month"), tr(lang, "kwh"), f"{tr(lang, 'saving')} ({cur})"], rows),
               {"type": "p", "text": tr(lang, "t_sav_month")}]
    return _frame(lang, d, project, "sav_title", blocks, dict(facts, **{"pv.saving_year": eco["saving_year"]}))


def pv_economic_memo(d, project, lang="en"):
    """The economic memorandum: simple payback = investment / yearly saving; the other indicators are listed as not verified."""
    eco, facts = economic_of(d), _facts(d)
    blocks = [{"type": "p", "text": tr(lang, "engine_line", name=d["engine"]["name"], version=d["engine"]["version"]) + " " + tr(lang, "edit_mode")},
              {"type": "h", "text": tr(lang, "h_eco_data")}]
    if eco is None or "investment" not in eco:
        blocks += [{"type": "p", "text": tr(lang, "no_price" if eco is None else "no_invest")}]
        return _frame(lang, d, project, "eco_title", blocks, facts)
    cur = eco["currency"]
    blocks += [table([tr(lang, "col_calc"), tr(lang, "col_val")], [[tr(lang, "d_invest"), f"{eco['investment']} {cur}"], [tr(lang, "sav_year"), f"{eco['saving_year']} {cur}/year"]]),
               {"type": "p", "text": tr(lang, "t_eco_data")}, {"type": "h", "text": tr(lang, "h_eco_pay")}, {"type": "p", "text": tr(lang, "l_eco_pay")}]
    blocks += _calc(lang, "E-01", "c_payback", f"I = {eco['investment']} {cur}; A = {eco['saving_year']} {cur}/year", "T = I / A", f"T = {eco['investment']} / {eco['saving_year']}",
                    f"T = {eco['simple_payback_years']}", "-", "not_verified")
    blocks += [{"type": "p", "text": tr(lang, "t_eco_pay")}, {"type": "h", "text": tr(lang, "h_eco_more")}, {"type": "p", "text": tr(lang, "eco_more_list") + " " + tr(lang, "pending_engine", item="PV-10")}]
    return _frame(lang, d, project, "eco_title", blocks, dict(facts, **{"pv.saving_year": eco["saving_year"]}))
