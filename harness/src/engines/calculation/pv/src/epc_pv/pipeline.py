"""run(): the hourly yield of every array of a document and its string layout.

Steps, in fixed order: validate the input, sun position of every instant (shared), plane-of-array irradiance and cell temperature of every array,
string layout (needs the hottest cell temperature), DC power, losses, inverter, and the totals. The result is a function of the input alone.
"""
import copy
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Union

from epc_pv import config, irradiance, power, solar, strings, thermal
from epc_pv.messages import bi, item
from epc_pv.model import Options, PvError, Result

WEATHER_SERIES = ("ghi", "dni", "dhi", "temp_air_c", "wind_ms")
MODULE_KEYS = ("pmax_w", "voc_v", "vmp_v", "isc_a", "imp_a", "beta_voc_pct_c", "gamma_pmax_pct_c")
INVERTER_KEYS = ("pac0_w", "mppt_v_min", "mppt_v_max", "vdc_max_v", "n_mppt", "i_max_input_a", "isc_max_input_a")


def _document(doc: Union[dict, str, bytes]) -> dict:
    if isinstance(doc, (str, bytes)):
        try:
            doc = json.loads(doc)
        except ValueError as e:
            raise PvError("err_json", detail=str(e)) from e
    if not isinstance(doc, dict):
        raise PvError("err_type", name=bi("the input", "la entrada"), kind=bi("a JSON object", "un objeto JSON"))
    missing = [k for k in ("site", "weather", "arrays") if k not in doc]
    if missing:
        raise PvError("err_missing", where=bi("the input", "la entrada"), names=", ".join(missing))
    if not isinstance(doc["arrays"], list) or not doc["arrays"]:
        raise PvError("err_type", name="arrays", kind=bi("a non-empty list", "una lista no vacía"))
    return doc


def _number(obj: Dict[str, Any], key: str, where: str, minimum: Optional[float] = None, maximum: Optional[float] = None, positive: bool = False) -> float:
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PvError("err_type", name=f"{where}.{key}", kind=bi("a number", "un número"))
    if (positive and value <= 0) or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        rule = bi("> 0", "> 0") if positive else bi(f"between {minimum} and {maximum}", f"entre {minimum} y {maximum}") if maximum is not None else bi(f">= {minimum}", f">= {minimum}")
        raise PvError("err_range", name=f"{where}.{key}", rule=rule, value=value)
    return float(value)


def _require(obj: Any, keys: Sequence[str], where: str) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise PvError("err_type", name=where, kind=bi("an object", "un objeto"))
    missing = [k for k in keys if k not in obj]
    if missing:
        raise PvError("err_missing", where=where, names=", ".join(missing))
    return obj


def _site(doc: dict) -> Dict[str, Any]:
    s = _require(doc["site"], ("latitude_deg", "longitude_deg", "albedo"), "site")
    return {"lat": _number(s, "latitude_deg", "site", -90, 90), "lon": _number(s, "longitude_deg", "site", -180, 180), "albedo": _number(s, "albedo", "site", 0, 1),
            "t_min_c": _number(s, "design_t_min_c", "site", -90, 60) if "design_t_min_c" in s else None}


def _weather(doc: dict) -> Dict[str, Any]:
    w = _require(doc["weather"], ("start", "utc_offset_h", "step_minutes") + WEATHER_SERIES, "weather")
    try:
        start = datetime.fromisoformat(str(w["start"]))
    except ValueError as e:
        raise PvError("err_range", name="weather.start", rule=bi("an ISO local time without offset, like 2023-01-01T00:00", "una hora local ISO sin desfase, como 2023-01-01T00:00"), value=w["start"]) from e
    series = {k: [float(v) for v in w[k]] for k in WEATHER_SERIES}
    n = len(series["ghi"])
    for k, values in series.items():
        if len(values) != n:
            raise PvError("err_length", name=k, n=len(values), expected=n)
    if n == 0:
        raise PvError("err_type", name="weather.ghi", kind=bi("a non-empty list", "una lista no vacía"))
    for k in ("ghi", "dni", "dhi", "wind_ms"):
        if min(series[k]) < 0:
            raise PvError("err_range", name=f"weather.{k}", rule=">= 0", value=min(series[k]))
    return {"start": start, "offset_h": _number(w, "utc_offset_h", "weather", -14, 14), "step_min": _number(w, "step_minutes", "weather", positive=True), "n": n, **series}


def _instants(site: Dict[str, Any], w: Dict[str, Any], solar_constant: float) -> List[Dict[str, Any]]:
    """Sun position and extraterrestrial irradiance of every instant of the weather file."""
    out = []
    for k in range(w["n"]):
        local = w["start"] + timedelta(minutes=w["step_min"] * k)
        utc = local - timedelta(hours=w["offset_h"])
        zen, app, az = solar.position(utc.date(), utc.hour * 60 + utc.minute + utc.second / 60.0, site["lat"], site["lon"])
        out.append({"month": local.month, "zenith": zen, "apparent": app, "azimuth": az, "extra": solar.extra_radiation_w_m2(local.timetuple().tm_yday, solar_constant)})
    return out


def _assumptions(doc: dict) -> Dict[str, Any]:
    """The typical parameters, overridden by the `assumptions` the document gives (a whole block per key)."""
    p = copy.deepcopy(config.params())
    given = doc.get("assumptions") or {}
    for key in ("iam_ashrae_b0", "faiman", "losses_pct", "inverter", "strings", "solar_constant_w_m2"):
        if key in given:
            p[key] = given[key]
    return p


def _array_spec(spec: Any, index: int) -> Dict[str, Any]:
    s = _require(spec, ("id", "tilt_deg", "azimuth_deg", "n_modules", "module", "inverter"), f"arrays[{index}]")
    _require(s["module"], MODULE_KEYS, f"arrays[{index}].module")
    _require(s["inverter"], INVERTER_KEYS, f"arrays[{index}].inverter")
    _number(s, "tilt_deg", f"arrays[{index}]", 0, 90)
    _number(s, "azimuth_deg", f"arrays[{index}]", 0, 360)
    _number(s, "n_modules", f"arrays[{index}]", positive=True)
    for k in ("pmax_w", "voc_v", "vmp_v", "isc_a", "imp_a"):
        _number(s["module"], k, f"arrays[{index}].module", positive=True)
    for k in INVERTER_KEYS:
        _number(s["inverter"], k, f"arrays[{index}].inverter", positive=True)
    return s


def _plane_series(spec: Dict[str, Any], w: Dict[str, Any], inst: List[Dict[str, Any]], site: Dict[str, Any], model: str, p: Dict[str, Any]) -> Dict[str, List[float]]:
    """Plane-of-array global and effective irradiance and the cell temperature of every instant."""
    surface = {"tilt_deg": float(spec["tilt_deg"]), "azimuth_deg": float(spec["azimuth_deg"])}
    out: Dict[str, List[float]] = {"global": [], "effective": [], "cell": []}
    for k in range(w["n"]):
        i = inst[k]
        sky = {"ghi": w["ghi"][k], "dni": w["dni"][k], "dhi": w["dhi"][k]}
        sun = {"zenith_deg": i["apparent"], "azimuth_deg": i["azimuth"], "dni_extra": i["extra"]}
        poa = irradiance.plane_of_array(model, surface, sun, sky, site["albedo"], p["iam_ashrae_b0"])
        out["global"].append(poa["global"])
        out["effective"].append(poa["effective"])
        out["cell"].append(thermal.faiman_cell_c(poa["global"], w["temp_air_c"][k], w["wind_ms"][k], p["faiman"]["u0"], p["faiman"]["u1"]))
    return out


def _energy(spec: Dict[str, Any], lay: Dict[str, Any], series: Dict[str, List[float]], w: Dict[str, Any], inst: List[Dict[str, Any]], p: Dict[str, Any]) -> Dict[str, Any]:
    """DC after losses, AC, clipping and the monthly energy of an array (kWh)."""
    mod, inv = spec["module"], spec["inverter"]
    p_stc = lay["modules"] * float(mod["pmax_w"])
    gamma = float(mod["gamma_pmax_pct_c"]) / 100.0
    keep = 1.0 - config.losses_total_pct(p["losses_pct"]) / 100.0
    n_inv, pac0 = lay["inverters"], float(inv["pac0_w"])
    eta_nom, eta_ref = p["inverter"]["eta_nom"], p["inverter"]["eta_ref"]
    hours = w["step_min"] / 60.0
    dc = ac = clip = peak = 0.0
    monthly = [0.0] * 12
    for k in range(w["n"]):
        pdc = power.dc_power_w(p_stc, series["effective"][k], series["cell"][k], gamma) * keep
        curve = power.inverter_curve_w(pdc / n_inv, pac0, eta_nom, eta_ref)
        pac = min(pac0, curve) * n_inv
        dc += pdc
        ac += pac
        clip += (curve * n_inv - pac)
        peak = max(peak, pac)
        monthly[inst[k]["month"] - 1] += pac
    kwh = hours / 1000.0
    return {"dc_kwh": dc * kwh, "ac_kwh": ac * kwh, "clipping_kwh": clip * kwh, "peak_ac_kw": peak / 1000.0, "monthly_ac_kwh": [m * kwh for m in monthly]}


def _array_result(spec: Dict[str, Any], lay: Dict[str, Any], e: Dict[str, Any], series: Dict[str, List[float]], w: Dict[str, Any]) -> Dict[str, Any]:
    hours = w["step_min"] / 60.0
    poa_kwh = sum(series["global"]) * hours / 1000.0
    kwp = lay["dc_kwp"]
    ac_rated_kw = lay["inverters"] * float(spec["inverter"]["pac0_w"]) / 1000.0
    total_hours = w["n"] * hours
    return {"id": str(spec["id"]), "name": str(spec.get("name", spec["id"])), "modules": lay["modules"], "inverters": lay["inverters"], "dc_kwp": round(kwp, 3), "ac_kw": round(ac_rated_kw, 3),
            "dc_ac_ratio": round(kwp / ac_rated_kw, 4), "strings": {k: lay[k] for k in ("n_series", "series_range", "strings", "strings_per_inverter", "strings_per_mppt", "strings_per_mppt_limit")},
            "poa_kwh_m2": round(poa_kwh, 3), "dc_kwh": round(e["dc_kwh"], 3), "ac_kwh": round(e["ac_kwh"], 3), "clipping_kwh": round(e["clipping_kwh"], 3), "peak_ac_kw": round(e["peak_ac_kw"], 3),
            "specific_yield_kwh_kwp": round(e["ac_kwh"] / kwp, 3), "performance_ratio": round(e["ac_kwh"] / (kwp * poa_kwh), 5) if poa_kwh > 0 else 0.0,
            "capacity_factor": round(e["ac_kwh"] / (ac_rated_kw * total_hours), 5), "monthly_ac_kwh": [round(m, 3) for m in e["monthly_ac_kwh"]]}


def _totals(arrays: List[Dict[str, Any]]) -> Dict[str, Any]:
    kwp = sum(a["dc_kwp"] for a in arrays)
    ac = sum(a["ac_kw"] for a in arrays)
    e = sum(a["ac_kwh"] for a in arrays)
    return {"dc_kwp": round(kwp, 3), "ac_kw": round(ac, 3), "dc_kwh": round(sum(a["dc_kwh"] for a in arrays), 3), "ac_kwh": round(e, 3), "clipping_kwh": round(sum(a["clipping_kwh"] for a in arrays), 3),
            "specific_yield_kwh_kwp": round(e / kwp, 3), "monthly_ac_kwh": [round(sum(a["monthly_ac_kwh"][m] for a in arrays), 3) for m in range(12)]}


def run(doc: Union[dict, str, bytes], options: Optional[Options] = None) -> Result:
    """The yield and the layout of every array of the document (see `schema/input.schema.json`)."""
    opts = options or Options()
    document = _document(doc)
    site, w, p = _site(document), _weather(document), _assumptions(document)
    specs = [_array_spec(s, i) for i, s in enumerate(document["arrays"])]
    t_min = site["t_min_c"] if site["t_min_c"] is not None else min(w["temp_air_c"])
    warnings = [item("typical_values"), item("wind_proxy")]
    if site["t_min_c"] is None:
        warnings.append(item("t_min_from_weather", t_min_c=round(t_min, 1)))
    inst = _instants(site, w, p["solar_constant_w_m2"])
    arrays: List[Dict[str, Any]] = []
    for spec in specs:
        series = _plane_series(spec, w, inst, site, opts.transposition, p)
        lay = strings.layout(spec, t_min, max(series["cell"]), p["strings"])
        warnings.extend(lay["warnings"])
        arrays.append(_array_result(spec, lay, _energy(spec, lay, series, w, inst, p), series, w))
    return Result(arrays=arrays, totals=_totals(arrays), warnings=warnings, hours=w["n"])
