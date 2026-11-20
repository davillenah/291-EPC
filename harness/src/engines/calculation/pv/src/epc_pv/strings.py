"""String layout of an array against the limits of the inverter.

    V_oc,cold = V_oc (1 + beta (T_min - 25))        n_series <= V_dc,max / V_oc,cold   and   n_series <= V_mppt,max / V_mp,cold
    V_mp,hot  = V_mp (1 + beta (T_cell,max - 25))    n_series >= V_mppt,min / V_mp,hot
    strings per MPPT input <= min( I_max / I_mp , I_sc,max / (I_sc k) )                  k: short-circuit factor (data); without I_sc,max only the first term is checked (warning `isc_not_checked`)
beta is the temperature coefficient of the voltage (fraction per degree C). The layout is whole strings: modules = strings x n_series.
"""
import math
from typing import Any, Dict, List

from epc_pv.messages import bi, item
from epc_pv.model import PvError


def half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def series_range(module: Dict[str, float], inverter: Dict[str, float], t_min_c: float, t_cell_max_c: float) -> Dict[str, int]:
    """Smallest and largest number of modules in series the inverter accepts (s_min can exceed s_max: no layout)."""
    beta = module["beta_voc_pct_c"] / 100.0
    voc_cold = module["voc_v"] * (1.0 + beta * (t_min_c - 25.0))
    vmp_cold = module["vmp_v"] * (1.0 + beta * (t_min_c - 25.0))
    vmp_hot = module["vmp_v"] * (1.0 + beta * (t_cell_max_c - 25.0))
    s_max = min(math.floor(inverter["vdc_max_v"] / voc_cold), math.floor(inverter["mppt_v_max"] / vmp_cold))
    s_min = max(1, math.ceil(inverter["mppt_v_min"] / vmp_hot))
    return {"s_min": int(s_min), "s_max": int(s_max)}


def choose_series(rng: Dict[str, int], module: Dict[str, float], inverter: Dict[str, float], policy: str, given, array_id: str) -> int:
    """The number of modules in series: the given one if it is allowed, else by the policy (`mid_mppt`: Vmp at STC closest to the middle of the MPPT window)."""
    if rng["s_min"] > rng["s_max"]:
        raise PvError("err_no_series", array=array_id, **rng)
    if given is not None:
        if not rng["s_min"] <= int(given) <= rng["s_max"]:
            raise PvError("err_series_fixed", array=array_id, n_series=given, **rng)
        return int(given)
    if policy == "max_voltage":
        return rng["s_max"]
    middle = 0.5 * (inverter["mppt_v_min"] + inverter["mppt_v_max"])
    return max(rng["s_min"], min(rng["s_max"], half_up(middle / module["vmp_v"])))


def inverter_count(spec: Dict[str, Any], dc_w: float, pac0_w: float, array_id: str) -> int:
    """The inverters of the array: the given count, or the one that gives the requested DC/AC ratio."""
    if spec.get("n_inverters") is not None:
        return int(spec["n_inverters"])
    if spec.get("dc_ac_ratio") is None:
        raise PvError("err_missing", where=bi(f"array {array_id}", f"el arreglo {array_id}"), names=bi("n_inverters or dc_ac_ratio", "n_inverters o dc_ac_ratio"))
    return max(1, half_up(dc_w / (float(spec["dc_ac_ratio"]) * pac0_w)))


def layout(spec: Dict[str, Any], t_min_c: float, t_cell_max_c: float, rules: Dict[str, Any]) -> Dict[str, Any]:
    """The layout of one array: strings, modules, inverters and the checks of the input current. Returns the numbers and the warnings."""
    module, inverter, array_id = spec["module"], spec["inverter"], str(spec["id"])
    rng = series_range(module, inverter, t_min_c, t_cell_max_c)
    n_series = choose_series(rng, module, inverter, rules["policy"], spec.get("n_series"), array_id)
    strings = max(1, math.ceil(int(spec["n_modules"]) / n_series))
    modules = strings * n_series
    dc_w = modules * module["pmax_w"]
    n_inv = inverter_count(spec, dc_w, inverter["pac0_w"], array_id)
    per_inverter = math.ceil(strings / n_inv)
    per_mppt = math.ceil(per_inverter / int(inverter["n_mppt"]))
    limit = math.floor(inverter["i_max_input_a"] / module["imp_a"])
    warnings: List[Dict[str, str]] = []
    if inverter.get("isc_max_input_a") is None:
        warnings.append(item("isc_not_checked", array=array_id))
    else:
        limit = min(limit, math.floor(inverter["isc_max_input_a"] / (module["isc_a"] * rules["isc_factor"])))
    if per_mppt > limit:
        warnings.append(item("warn_current", array=array_id, strings=per_mppt, limit=limit))
    return {"n_series": n_series, "series_range": rng, "strings": strings, "modules": modules, "dc_kwp": dc_w / 1000.0, "inverters": n_inv, "strings_per_inverter": per_inverter,
            "strings_per_mppt": per_mppt, "strings_per_mppt_limit": int(limit), "warnings": warnings}
