"""The shading abacus (ábaco de asoleamiento): the sun paths of the year on a chart of azimuth against elevation, cut into the standard cells A1 to D14, each with its share of the annual irradiation.

The standard layout (graphic method of the solar resource studies): the yearly band of the sun is cut into four bands of equal declination, A (lowest sun) to D (highest), and into the solar hours counted from
noon, seven on each side; the number of a cell is 2 (hour - 1) + 1 on the afternoon side and 2 (hour - 1) + 2 on the morning side, so A1 and A2 are the lowest cells at noon. The weight of a cell is the share of the
annual plane-of-array irradiation that falls while the sun is inside it (the engine transposition, so it depends on the tilt and orientation of the plane, as the reference tables do). An obstacle profile
(elevation against azimuth) hides part of some cells; the loss is the sum of weight times the hidden part of every cell. The abacus is a visual check of the ray-cast shading, not a second source of truth.
"""
import math
from datetime import timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from epc_pv import irradiance, pipeline, shading, solar
from epc_pv.model import Options, PvError

OBLIQUITY_DEG = 23.44
BANDS = "ABCD"
HOURS_EACH_SIDE = 7
SAMPLES = 5
CUT_STEPS = 6
COVER_STEPS = (0.0, 0.25, 0.5, 0.75, 1.0)


def _edges(latitude_deg: float) -> List[float]:
    """The five declinations that cut the year into the bands, from the lowest sun path (A) to the highest."""
    start = -OBLIQUITY_DEG if latitude_deg >= 0 else OBLIQUITY_DEG
    step = -start / 2.0
    return [start + step * k for k in range(len(BANDS) + 1)]


def cell_id(band: int, hour: int, afternoon: bool) -> str:
    """`A1`: band letter and number (hour 1 to 7 from noon; afternoon gives the odd number, morning the even one)."""
    return f"{BANDS[band]}{2 * (hour - 1) + (1 if afternoon else 2)}"


def sun_xy(latitude_deg: float, declination_deg: float, hour_angle_deg: float) -> Tuple[float, float]:
    """(x, elevation) of the sun on the chart: x is the azimuth from the direction of the equator, positive clockwise (east in the south hemisphere)."""
    lat, dec, h = (math.radians(v) for v in (latitude_deg, declination_deg, hour_angle_deg))
    sin_el = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(h)
    az = (math.degrees(math.atan2(math.sin(h), math.cos(h) * math.sin(lat) - math.tan(dec) * math.cos(lat))) + 180.0) % 360.0
    ref = 0.0 if latitude_deg < 0 else 180.0
    return round((az - ref + 180.0) % 360.0 - 180.0, 3), round(math.degrees(math.asin(max(-1.0, min(1.0, sin_el)))), 3)


def _lerp(a: float, b: float, k: int, n: int) -> float:
    return a + (b - a) * k / n


def _outline(latitude_deg: float, d0: float, d1: float, h0: float, h1: float) -> List[List[float]]:
    """The border of a cell on the chart: the sun path of both declinations between the hour lines, and the two hour lines, with the part below the horizon cut at elevation 0."""
    path = [(d0, _lerp(h0, h1, k, CUT_STEPS)) for k in range(CUT_STEPS + 1)] + [(_lerp(d0, d1, k, CUT_STEPS), h1) for k in range(1, CUT_STEPS + 1)]
    path += [(d1, _lerp(h1, h0, k, CUT_STEPS)) for k in range(1, CUT_STEPS + 1)] + [(_lerp(d1, d0, k, CUT_STEPS), h0) for k in range(1, CUT_STEPS)]
    out = []
    for dec, h in path:
        x, el = sun_xy(latitude_deg, dec, h)
        out.append([x, max(el, 0.0)])
    return out


def _samples(d0: float, d1: float, h0: float, h1: float) -> List[Tuple[float, float]]:
    return [(_lerp(d0, d1, 2 * i + 1, 2 * SAMPLES), _lerp(h0, h1, 2 * j + 1, 2 * SAMPLES)) for i in range(SAMPLES) for j in range(SAMPLES)]


def _cover(latitude_deg: float, points: List[Tuple[float, float]], profile: Optional[Sequence[Dict[str, float]]], afternoon: bool) -> Tuple[float, bool]:
    """(hidden share of the cell by the profile, the cell has a sun above the horizon)."""
    up = hidden = 0
    for dec, h in points:
        h_signed = h if afternoon else -h
        x, el = sun_xy(latitude_deg, dec, h_signed)
        if el <= 0.0:
            continue
        up += 1
        az = (x + (0.0 if latitude_deg < 0 else 180.0)) % 360.0
        if profile and el < shading.horizon_elevation_deg(profile, az):
            hidden += 1
    return (hidden / up if up else 0.0), up > 0


def quantize(cover: float) -> float:
    """The cover rounded to the nearest of 0, 0.25, 0.5, 0.75, 1 (the filling factors of the method)."""
    return min(COVER_STEPS, key=lambda c: (abs(c - cover), c))


def layout(latitude_deg: float, profile: Optional[Sequence[Dict[str, float]]] = None) -> List[Dict[str, Any]]:
    """The cells of the chart for a latitude: id, declination and hour-angle limits, outline on the chart and the share hidden by `profile`. Cells with no sun above the horizon are left out."""
    edges, cells = _edges(latitude_deg), []
    for band in range(len(BANDS)):
        d0, d1 = edges[band], edges[band + 1]
        for hour in range(1, HOURS_EACH_SIDE + 1):
            h0, h1 = 15.0 * (hour - 1), 15.0 * hour
            for afternoon in (True, False):
                a, b = (h0, h1) if afternoon else (-h1, -h0)
                cover, up = _cover(latitude_deg, _samples(d0, d1, h0, h1), profile, afternoon)
                if up:
                    cells.append({"id": cell_id(band, hour, afternoon), "band": BANDS[band], "declination_deg": [round(d0, 3), round(d1, 3)], "hour_angle_deg": [a, b],
                                  "outline": _outline(latitude_deg, d0, d1, a, b), "cover": quantize(cover)})
    return cells


def _band_of(edges: List[float], dec: float) -> int:
    lo, hi = sorted((edges[0], edges[-1]))
    step = (edges[-1] - edges[0]) / len(BANDS)
    return min(max(int((min(max(dec, lo), hi) - edges[0]) / step), 0), len(BANDS) - 1)


def weights(doc: Union[dict, str, bytes], tilt_deg: float, azimuth_deg: float, options: Optional[Options] = None) -> Dict[str, float]:
    """{cell id: share (0 to 1) of the annual plane-of-array irradiation that falls inside the cell} for the plane; the shares add up to 1."""
    site, w, p = pipeline.sky_context(doc)
    edges, model = _edges(site["lat"]), (options or Options()).transposition
    inst = pipeline.instants(site, w, p)
    surface, totals = {"tilt_deg": tilt_deg, "azimuth_deg": azimuth_deg}, {}
    for k, i in enumerate(inst):
        if i["apparent"] >= 90.0:
            continue
        utc = w["start"] + timedelta(minutes=w["step_min"] * k) - timedelta(hours=w["offset_h"])
        dec, h = solar.sun_angles(utc.date(), utc.hour * 60 + utc.minute + utc.second / 60.0, site["lon"])
        sun = {"zenith_deg": i["apparent"], "azimuth_deg": i["azimuth"], "dni_extra": i["extra"]}
        g = irradiance.plane_of_array(model, surface, sun, {"ghi": w["ghi"][k], "dni": w["dni"][k], "dhi": w["dhi"][k]}, site["albedo"], p["iam_ashrae_b0"])["global"]
        cid = cell_id(_band_of(edges, dec), min(max(int(math.ceil(abs(h) / 15.0)), 1), HOURS_EACH_SIDE), h >= 0)
        totals[cid] = totals.get(cid, 0.0) + g * w["step_min"]
    whole = sum(totals.values())
    if whole <= 0.0:
        raise PvError("err_range", name="weather.ghi", rule="> 0", value=0)
    return {cid: v / whole for cid, v in sorted(totals.items())}


def compute(doc: Union[dict, str, bytes], tilt_deg: float, azimuth_deg: float, options: Optional[Options] = None) -> Dict[str, Any]:
    """{"cells": [...], "profile": [[x, elevation]...], "loss_pct": ..., "latitude_deg": ...}: the abacus of the site for the plane, with the loss the profile `site.horizon` causes (0 without one).

    Each cell has `id`, `band`, `outline` on the chart, `cover` (0, 0.25, 0.5, 0.75 or 1) and `weight_pct`."""
    site = pipeline.sky_context(doc)[0]
    share = weights(doc, tilt_deg, azimuth_deg, options)
    cells = layout(site["lat"], site["horizon"])
    for c in cells:
        c["weight_pct"] = round(100.0 * share.get(c["id"], 0.0), 4)
    loss = round(sum(c["weight_pct"] * c["cover"] for c in cells), 3)
    ref = 0.0 if site["lat"] < 0 else 180.0
    profile = sorted([round((pt["azimuth_deg"] - ref + 180.0) % 360.0 - 180.0, 3), pt["elevation_deg"]] for pt in (site["horizon"] or []))
    return {"latitude_deg": site["lat"], "cells": cells, "profile": profile, "loss_pct": loss, "tilt_deg": tilt_deg, "azimuth_deg": azimuth_deg}
