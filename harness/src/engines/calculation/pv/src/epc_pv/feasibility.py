"""The feasibility of a plant from the result of `run`, and the inverter count that respects the input current (called functions: all data in, the answer out).

Moved from the discipline stage (`disciplines/electrical_lv/stages/pv_stage.py`) so that every PV calculation lives in this engine; the numbers are the same.
  saving = yearly kWh x the client's price      simple payback = investment / saving      (the client's own figures; nothing is recorded or assumed)
  inverters = ceil( strings / (MPPT inputs x strings per input the data sheet allows) )   when the ratio alone leaves more strings per input than the limit
"""
from epc_pv.messages import item
from epc_pv.model import Options
from epc_pv.pipeline import run


def _rerun(section):
    """The engine run of a section `{"document": ..., "options": {...}}` as a dict."""
    return run(section["document"], Options(**(section.get("options") or {}))).as_dict()


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


def add_inverters_for_current(section, result):
    """(section, result) where an `auto` inverter count also respects the input current of its MPPT inputs: the ratio alone can leave more strings per input than the data sheet allows, so inverters are added."""
    arrays, raised = [], []
    for spec, res in zip(section["document"]["arrays"], result["arrays"]):
        st, inv = res["strings"], spec["inverter"]
        if inv.get("auto") and st["strings_per_mppt"] > st["strings_per_mppt_limit"] and st["strings_per_mppt_limit"] > 0:
            count = -(-st["strings"] // (int(inv["n_mppt"]) * st["strings_per_mppt_limit"]))
            raised.append(item("inverters_raised", array=str(spec["id"]), before=res["inverters"], after=count, ratio=round(res["dc_kwp"] * 1000.0 / (count * float(inv["pac0_w"])), 2)))
            spec = dict(spec, n_inverters=count)
        arrays.append(spec)
    if not raised:
        return section, result
    section = dict(section, document=dict(section["document"], arrays=arrays))
    new = _rerun(section)
    return section, dict(new, warnings=list(new["warnings"]) + raised)      # the `inverter_auto` note states the count of the ratio alone: this one states what is installed
