"""Developer tool (NOT part of the product or the gate): computes the pvlib reference of the validation projects and writes `reference.json`.

    python make_reference.py --from 1 --to 1000 --out reference.json          needs pvlib, numpy and pandas (pip install pvlib)

pvlib is used with the same models as the engine (NREL SPA sun position, Spencer extraterrestrial irradiance, Hay-Davies transposition, ASHRAE IAM, Faiman cell
temperature, PVWatts DC and inverter). The string layout is not a pvlib function: the layout code of `epc_pv.strings` is called with pvlib's hottest cell
temperature, and the strings are checked by invariants in the tests. Once written, `reference.json` is never edited by hand (golden file).
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "src")]

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pvlib  # noqa: E402

import cases  # noqa: E402
from epc_pv import config, strings  # noqa: E402

TRANSPOSITION = "haydavies"


def reference(doc: dict) -> dict:
    p = config.params()
    w, site = doc["weather"], doc["site"]
    index = pd.date_range(w["start"], periods=len(w["ghi"]), freq="h", tz=f"Etc/GMT{int(-w['utc_offset_h']):+d}")
    loc = pvlib.location.Location(site["latitude_deg"], site["longitude_deg"])
    sp = loc.get_solarposition(index, method="nrel_numpy")
    extra = pvlib.irradiance.get_extra_radiation(index, solar_constant=p["solar_constant_w_m2"], method="spencer")
    ghi, dni, dhi = (pd.Series(w[k], index=index) for k in ("ghi", "dni", "dhi"))
    temp, wind = pd.Series(w["temp_air_c"], index=index), pd.Series(w["wind_ms"], index=index)
    loss = config.losses_total_pct(p["losses_pct"])
    out = []
    for spec in doc["arrays"]:
        tilt, az = spec["tilt_deg"], spec["azimuth_deg"]
        tot = pvlib.irradiance.get_total_irradiance(tilt, az, sp.apparent_zenith, sp.azimuth, dni, ghi, dhi, dni_extra=extra, model=TRANSPOSITION, albedo=site["albedo"])
        aoi = pvlib.irradiance.aoi(tilt, az, sp.apparent_zenith, sp.azimuth)
        iam = pvlib.iam.ashrae(aoi, b=p["iam_ashrae_b0"])
        eff = tot.poa_direct * iam + tot.poa_sky_diffuse + tot.poa_ground_diffuse
        cell = pvlib.temperature.faiman(tot.poa_global, temp, wind, u0=p["faiman"]["u0"], u1=p["faiman"]["u1"])
        lay = strings.layout(spec, site["design_t_min_c"], float(cell.max()), p["strings"])
        mod, inv = spec["module"], spec["inverter"]
        pdc = pvlib.pvsystem.pvwatts_dc(eff, cell, lay["modules"] * mod["pmax_w"], mod["gamma_pmax_pct_c"] / 100.0, temp_ref=25.0) * (1 - loss / 100.0)
        n = lay["inverters"]
        pac_one = pvlib.inverter.pvwatts(pdc / n, inv["pac0_w"] / p["inverter"]["eta_nom"], eta_inv_nom=p["inverter"]["eta_nom"], eta_inv_ref=p["inverter"]["eta_ref"])
        pac = np.maximum(pac_one, 0.0) * n
        monthly = (pac.groupby(pac.index.month).sum() / 1000.0).reindex(range(1, 13), fill_value=0.0)
        out.append({"id": spec["id"], "modules": lay["modules"], "inverters": n, "n_series": lay["n_series"], "dc_kwh": float(pdc.sum() / 1000.0), "ac_kwh": float(pac.sum() / 1000.0),
                    "poa_kwh_m2": float(tot.poa_global.sum() / 1000.0), "monthly_ac_kwh": [float(m) for m in monthly]})
    return {"arrays": out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="lo", type=int, default=1)
    ap.add_argument("--to", dest="hi", type=int, default=1000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    data = {"pvlib_version": pvlib.__version__, "model": TRANSPOSITION, "projects": {}}
    for n in range(a.lo, a.hi + 1):
        data["projects"][str(n)] = reference(cases.project(n))
    Path(a.out).write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
