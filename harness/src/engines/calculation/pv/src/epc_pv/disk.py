"""The irradiation disk: the annual irradiation on every fixed plane (tilt and orientation) of a site, as a percentage of the best plane.

It is the graphic method of the solar resource studies: a polar chart whose radius is the tilt and whose angle is the orientation (azimuth from north, clockwise). Each cell is the sum over the weather
year of the plane-of-array global irradiance (the same transposition the yield uses), divided by the largest cell. A pure function of the input: same input, same numbers.
"""
import json
from typing import Any, Dict, List, Optional, Union

from epc_pv import irradiance, pipeline
from epc_pv.messages import bi
from epc_pv.model import Options, PvError

DEFAULT_TILT_STEP_DEG, DEFAULT_AZIMUTH_STEP_DEG = 10, 15


def _steps(tilt_step_deg: float, azimuth_step_deg: float) -> None:
    for name, value, top in (("tilt_step_deg", tilt_step_deg, 90), ("azimuth_step_deg", azimuth_step_deg, 180)):
        if not 0 < value <= top or (top % value) != 0:
            raise PvError("err_range", name=name, rule=bi(f"a divisor of {top} and greater than 0", f"un divisor de {top} y mayor que 0"), value=value)


def _daylight(inst: List[Dict[str, Any]], w: Dict[str, Any]) -> List[int]:
    return [k for k in range(w["n"]) if inst[k]["apparent"] < 90.0 and (w["ghi"][k] > 0.0 or w["dni"][k] > 0.0)]


def compute(doc: Union[dict, str, bytes], options: Optional[Options] = None, tilt_step_deg: float = DEFAULT_TILT_STEP_DEG, azimuth_step_deg: float = DEFAULT_AZIMUTH_STEP_DEG) -> Dict[str, Any]:
    """{"tilt_deg": [...], "azimuth_deg": [...], "kwh_m2": [[...]], "pct": [[...]], "best": {...}, "hours": n}: `kwh_m2[i][j]` is the annual irradiation on tilt `i` and azimuth `j`.

    The document needs `site` and `weather` (see `schema/input.schema.json`); arrays are not needed."""
    opts = options or Options()
    _steps(tilt_step_deg, azimuth_step_deg)
    if isinstance(doc, (str, bytes)):
        try:
            doc = json.loads(doc)
        except ValueError as e:
            raise PvError("err_json", detail=str(e)) from e
    if isinstance(doc, dict) and "arrays" not in doc:
        doc = dict(doc, arrays=[{}])
    site, w, p = pipeline.sky_context(doc)
    inst = pipeline.instants(site, w, p)
    hours = _daylight(inst, w)
    tilts = [float(t) for t in range(0, 91, int(tilt_step_deg))]
    azimuths = [float(a) for a in range(0, 360, int(azimuth_step_deg))]
    step_h = w["step_min"] / 60.0
    energy: List[List[float]] = []
    for tilt in tilts:
        row = []
        for az in (azimuths if tilt > 0 else [0.0] * len(azimuths)):
            surface, total = {"tilt_deg": tilt, "azimuth_deg": az}, 0.0
            for k in hours:
                i = inst[k]
                sun = {"zenith_deg": i["apparent"], "azimuth_deg": i["azimuth"], "dni_extra": i["extra"]}
                sky = {"ghi": w["ghi"][k], "dni": w["dni"][k], "dhi": w["dhi"][k]}
                total += irradiance.plane_of_array(opts.transposition, surface, sun, sky, site["albedo"], p["iam_ashrae_b0"])["global"]
            row.append(round(total * step_h / 1000.0, 3))
        energy.append(row)
    top = max(max(r) for r in energy)
    if top <= 0.0:
        raise PvError("err_range", name="weather.ghi", rule="> 0", value=0)
    pct = [[round(100.0 * v / top, 2) for v in r] for r in energy]
    bi_, bj = max(((i, j) for i in range(len(tilts)) for j in range(len(azimuths))), key=lambda ij: energy[ij[0]][ij[1]])
    return {"tilt_deg": tilts, "azimuth_deg": azimuths, "kwh_m2": energy, "pct": pct, "hours": w["n"],
            "best": {"tilt_deg": tilts[bi_], "azimuth_deg": azimuths[bj], "kwh_m2": energy[bi_][bj]}}


def pct_at(disk: Dict[str, Any], tilt_deg: float, azimuth_deg: float) -> float:
    """The percentage of the best plane for any tilt and azimuth, by bilinear interpolation between the cells (azimuth wraps around the circle)."""
    tilts, azs = disk["tilt_deg"], disk["azimuth_deg"]
    t = min(max(tilt_deg, tilts[0]), tilts[-1])
    i = min(int((t - tilts[0]) // (tilts[1] - tilts[0])), len(tilts) - 2)
    ft = (t - tilts[i]) / (tilts[i + 1] - tilts[i])
    step = azs[1] - azs[0]
    a = azimuth_deg % 360.0
    j = int(a // step)
    fa = (a - azs[j]) / step
    j2 = (j + 1) % len(azs)
    row = lambda r: disk["pct"][r][j] * (1 - fa) + disk["pct"][r][j2] * fa
    return round(row(i) * (1 - ft) + row(i + 1) * ft, 2)


def refine(disk: Dict[str, Any], tilt_step_deg: float = 5, azimuth_step_deg: float = 5) -> Dict[str, Any]:
    """The same disk on a finer grid (bilinear between the cells), for a smooth drawing; `kwh_m2` is not carried (only `pct` and the best plane are)."""
    _steps(tilt_step_deg, azimuth_step_deg)
    tilts = [float(t) for t in range(0, 91, int(tilt_step_deg))]
    azimuths = [float(a) for a in range(0, 360, int(azimuth_step_deg))]
    pct = [[pct_at(disk, t, a) for a in azimuths] for t in tilts]
    return {"tilt_deg": tilts, "azimuth_deg": azimuths, "pct": pct, "best": disk["best"], "hours": disk["hours"]}
