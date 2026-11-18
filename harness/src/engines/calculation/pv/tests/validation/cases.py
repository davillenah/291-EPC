"""Reproducible synthetic projects for the validation against pvlib (no real site, module or inverter is named: the catalog is invented but realistic).

`project(n)` is a pure function of `n` (a seeded Mersenne Twister, portable across platforms): project n always has the same site, weather year and arrays.
The weather is built from the sun position, a clear-sky curve and a daily clearness; both the engine and the reference read the same arrays, so the comparison
isolates the calculation, not the weather.
"""
import math
import random
from typing import Any, Dict, List

from epc_pv import solar

YEAR_HOURS = 8760
START = "2023-01-01T00:00"
UTC_OFFSET_H = -3.0

MODULES = [
    {"pmax_w": 550.0, "voc_v": 49.9, "vmp_v": 41.8, "isc_a": 13.9, "imp_a": 13.16, "beta_voc_pct_c": -0.27, "gamma_pmax_pct_c": -0.34},
    {"pmax_w": 450.0, "voc_v": 41.3, "vmp_v": 34.5, "isc_a": 13.8, "imp_a": 13.05, "beta_voc_pct_c": -0.28, "gamma_pmax_pct_c": -0.35},
    {"pmax_w": 665.0, "voc_v": 46.0, "vmp_v": 38.2, "isc_a": 18.4, "imp_a": 17.4, "beta_voc_pct_c": -0.25, "gamma_pmax_pct_c": -0.29},
    {"pmax_w": 400.0, "voc_v": 37.4, "vmp_v": 31.4, "isc_a": 13.5, "imp_a": 12.74, "beta_voc_pct_c": -0.29, "gamma_pmax_pct_c": -0.36},
]
INVERTERS = [
    {"pac0_w": 100000.0, "mppt_v_min": 200.0, "mppt_v_max": 1000.0, "vdc_max_v": 1100.0, "n_mppt": 10, "i_max_input_a": 30.0, "isc_max_input_a": 45.0},
    {"pac0_w": 215000.0, "mppt_v_min": 500.0, "mppt_v_max": 1500.0, "vdc_max_v": 1500.0, "n_mppt": 12, "i_max_input_a": 40.0, "isc_max_input_a": 60.0},
    {"pac0_w": 2500000.0, "mppt_v_min": 850.0, "mppt_v_max": 1300.0, "vdc_max_v": 1500.0, "n_mppt": 1, "i_max_input_a": 3200.0, "isc_max_input_a": 4800.0},
    {"pac0_w": 50000.0, "mppt_v_min": 200.0, "mppt_v_max": 1000.0, "vdc_max_v": 1100.0, "n_mppt": 4, "i_max_input_a": 30.0, "isc_max_input_a": 45.0},
]


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def weather(rng: random.Random, lat: float, lon: float) -> Dict[str, Any]:
    """One year of hourly data: ghi, dni, dhi (W/m2), air temperature (C), wind (m/s)."""
    from datetime import datetime, timedelta
    start = datetime.fromisoformat(START)
    mean_t = 22.0 - 0.4 * (abs(lat) - 22.0)
    amp = 3.0 + 0.2 * (abs(lat) - 22.0)
    ghi: List[float] = []
    dni: List[float] = []
    dhi: List[float] = []
    temp: List[float] = []
    wind: List[float] = []
    kt_day = 0.6
    for h in range(YEAR_HOURS):
        local = start + timedelta(hours=h)
        if local.hour == 0:
            kt_day = 0.25 + 0.7 * rng.random() ** 0.7
        utc = local - timedelta(hours=UTC_OFFSET_H)
        zen, app, az = solar.position(utc.date(), utc.hour * 60 + utc.minute, lat, lon)
        cos_z = math.cos(math.radians(app))
        kt = _clip(kt_day * (0.85 + 0.3 * rng.random()), 0.05, 1.0)
        g = 1098.0 * cos_z * math.exp(-0.057 / cos_z) * kt if app < 89.0 and cos_z > 0.02 else 0.0
        frac = _clip(1.4 - 1.3 * kt, 0.1, 1.0)
        d = g * frac
        b = min(1100.0, (g - d) / cos_z) if g > 0 else 0.0
        doy = local.timetuple().tm_yday
        t = mean_t + amp * math.cos(2 * math.pi * (doy - 15) / 365.0) + (3.0 + 4.0 * kt) * math.cos(2 * math.pi * (local.hour - 15) / 24.0) + rng.uniform(-1.0, 1.0)
        ghi.append(round(g, 2))
        dhi.append(round(d, 2))
        dni.append(round(b, 2))
        temp.append(round(t, 2))
        wind.append(round(0.5 + 5.0 * rng.random() ** 1.5, 2))
    return {"start": START, "utc_offset_h": UTC_OFFSET_H, "step_minutes": 60, "ghi": ghi, "dni": dni, "dhi": dhi, "temp_air_c": temp, "wind_ms": wind}


def project(n: int) -> Dict[str, Any]:
    """The n-th project: a site of Argentina and one to three arrays of 1 MWp to 500 MWp."""
    rng = random.Random(291_000 + n)
    lat = rng.uniform(-55.0, -22.0)
    lon = rng.uniform(-72.0, -54.0)
    arrays = []
    for k in range(1 + rng.randrange(3)):
        n_modules = int(math.exp(rng.uniform(math.log(2000), math.log(800000))))
        big = n_modules > 60000
        inv = INVERTERS[2 if big and rng.random() < 0.5 else (1 if big else rng.choice((0, 3, 1)))]
        mod = MODULES[rng.randrange(len(MODULES))]
        east_west = rng.random() < 0.2
        arrays.append({"id": f"A{k + 1}", "name": f"Array {k + 1}", "tilt_deg": round(_clip(abs(lat) * 0.9 + rng.uniform(-10, 10), 0, 60), 1), "azimuth_deg": rng.choice((90.0, 270.0)) if east_west else round(rng.uniform(-15, 15) % 360, 1),
                       "n_modules": n_modules, "module": dict(mod), "inverter": dict(inv), "dc_ac_ratio": round(rng.uniform(1.1, 1.5), 2)})
    return {"site": {"latitude_deg": round(lat, 4), "longitude_deg": round(lon, 4), "albedo": round(rng.uniform(0.15, 0.3), 2), "design_t_min_c": round(8.0 - 0.45 * (abs(lat) - 22.0), 1)},
            "weather": weather(rng, lat, lon), "arrays": arrays}
