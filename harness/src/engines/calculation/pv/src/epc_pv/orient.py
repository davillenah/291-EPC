"""Orientation chosen by the engine: the tilt and azimuth of a fixed plane that give the most energy over the weather year of the site.

The person does not have to know them. Azimuth faces the equator (0 in the southern hemisphere, 180 in the northern one; azimuth is measured from north, clockwise). The tilt is found by running the yield
engine itself over the weather year (coarse steps, then a fine search around the best), so the answer already includes the site's sun, diffuse light and temperature. It is a fixed-plane optimum for
annual energy, not for a month or a tariff. Typical values stay `pending review` (the yield parameters are in `data/params.json`).
"""
import copy
import math
from typing import Any, Dict

from epc_pv.model import Options
from epc_pv.pipeline import run

COARSE_STEP_DEG, FINE_RANGE_DEG, MAX_TILT_DEG = 10, 4, 60
PROBE_MODULES = 120


def equator_azimuth_deg(latitude_deg: float) -> float:
    return 0.0 if latitude_deg < 0 else 180.0


def modules_for_kwp(kwp: float, pmax_w: float) -> int:
    """Whole modules that reach at least `kwp` kWp with modules of `pmax_w` W."""
    return max(1, math.ceil(kwp * 1000.0 / pmax_w - 1e-9))


def _yield(document: Dict[str, Any], tilt: float, azimuth: float) -> float:
    probe = copy.deepcopy(document)
    probe["arrays"] = [dict(copy.deepcopy(document["arrays"][0]), id="PROBE", tilt_deg=tilt, azimuth_deg=azimuth, n_modules=PROBE_MODULES, dc_ac_ratio=1.0)]
    probe["arrays"][0].pop("n_inverters", None)
    return run(probe, Options()).totals["specific_yield_kwh_kwp"]


def optimal(document: Dict[str, Any]) -> Dict[str, Any]:
    """{tilt_deg, azimuth_deg, specific_yield_kwh_kwp, method} for `document` (its first array gives the module and inverter; its tilt and azimuth are ignored)."""
    azimuth = equator_azimuth_deg(float(document["site"]["latitude_deg"]))
    scores: Dict[float, float] = {}
    for tilt in range(0, MAX_TILT_DEG + 1, COARSE_STEP_DEG):
        scores[tilt] = _yield(document, tilt, azimuth)
    center = max(scores, key=scores.get)
    for tilt in range(max(0, int(center) - FINE_RANGE_DEG), min(MAX_TILT_DEG, int(center) + FINE_RANGE_DEG) + 1):
        scores.setdefault(tilt, _yield(document, tilt, azimuth))
    best = max(scores, key=scores.get)
    return {"tilt_deg": float(best), "azimuth_deg": azimuth, "specific_yield_kwh_kwp": scores[best], "method": "fixed plane facing the equator, tilt searched on the weather year"}
