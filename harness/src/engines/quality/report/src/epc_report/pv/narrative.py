"""The PV descriptive reports (ADR-0043): the problem and the proposed solution in running text, technical and without invented figures. One for the plant, one for the saving and one for the economics (separate documents).

The text is a template with the values of the engine result filled in; a value that is not there is said to be missing, never guessed.
"""
from epc_report.pv.figures import abacus_figure, disk_figure
from epc_report.pv.economics import _frame, _facts, economic_of
from epc_report.pv.texts import tr


def _plant_text(lang, result):
    a, totals = result["arrays"][0], result["totals"]
    return tr(lang, "n_solution", kwp=totals["dc_kwp"], kw=totals["ac_kw"], modules=sum(x["modules"] for x in result["arrays"]), strings=a["strings"]["strings"],
              n_series=a["strings"]["n_series"], inverters=sum(x["inverters"] for x in result["arrays"]))


def _charts(lang, result):
    """The disk and the abacus of the engine result as figures (nothing when the result carries no charts)."""
    charts = result.get("charts") or {}
    return [disk_figure(lang, charts["disk"]), abacus_figure(lang, charts["abacus"])] if charts.get("disk") and (charts.get("abacus") or {}).get("cells") else []


def pv_descriptive_report(d, project, problem=None, lang="en"):
    """The descriptive report of the plant: problem, proposed solution, expected result and the limits of this version."""
    result, totals = d["result"], d["result"]["totals"]
    blocks = [{"type": "p", "text": tr(lang, "edit_mode")}, {"type": "h", "text": tr(lang, "h_problem")}, {"type": "p", "text": problem or tr(lang, "n_problem_none")},
              {"type": "h", "text": tr(lang, "h_solution")}, {"type": "p", "text": _plant_text(lang, result)},
              {"type": "h", "text": tr(lang, "h_result")}, {"type": "p", "text": tr(lang, "n_result", kwh=totals["ac_kwh"], yield_=totals["specific_yield_kwh_kwp"])},
              *_charts(lang, result), {"type": "h", "text": tr(lang, "h_limits")}, {"type": "p", "text": tr(lang, "n_limits")}]
    return _frame(lang, d, project, "desc_title", blocks, _facts(d))


def pv_savings_descriptive(d, project, problem=None, lang="en"):
    """The descriptive report of the saving: what the client wants to reduce, what the plant supplies and what that is worth."""
    eco = economic_of(d)
    need = tr(lang, "n_sav_problem", problem=problem) if problem else tr(lang, "n_problem_none")
    solution = tr(lang, "n_sav_none") if eco is None else tr(lang, "n_sav_solution", kwh=eco["energy_kwh_year"], price=eco["energy_price"], cur=eco["currency"], saving=eco["saving_year"])
    blocks = [{"type": "p", "text": tr(lang, "edit_mode")}, {"type": "h", "text": tr(lang, "h_problem")}, {"type": "p", "text": need},
              {"type": "h", "text": tr(lang, "h_solution")}, {"type": "p", "text": _plant_text(lang, d["result"])}, {"type": "p", "text": solution},
              {"type": "h", "text": tr(lang, "h_limits")}, {"type": "p", "text": tr(lang, "n_sav_limits")}]
    return _frame(lang, d, project, "sav_desc_title", blocks, _facts(d))


def pv_economic_descriptive(d, project, problem=None, lang="en"):
    """The descriptive report of the economics: the investment against the saving and the simple payback."""
    eco = economic_of(d)
    need = tr(lang, "n_eco_problem", problem=problem) if problem else tr(lang, "n_problem_none")
    ready = eco is not None and "investment" in eco
    solution = tr(lang, "n_eco_solution", invest=eco["investment"], cur=eco["currency"], saving=eco["saving_year"], payback=eco["simple_payback_years"]) if ready else tr(lang, "n_eco_none")
    blocks = [{"type": "p", "text": tr(lang, "edit_mode")}, {"type": "h", "text": tr(lang, "h_problem")}, {"type": "p", "text": need},
              {"type": "h", "text": tr(lang, "h_solution")}, {"type": "p", "text": _plant_text(lang, d["result"])}, {"type": "p", "text": solution},
              {"type": "h", "text": tr(lang, "h_limits")}, {"type": "p", "text": tr(lang, "n_eco_limits")}]
    return _frame(lang, d, project, "eco_desc_title", blocks, _facts(d))
