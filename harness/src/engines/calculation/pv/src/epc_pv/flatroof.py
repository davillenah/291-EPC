"""Flat roof: the structure the harness proposes when nothing is known about the roof.

With no roof information the roof is assumed flat and the modules go on tilted frames (rows facing the equator). The harness chooses the tilt that gives the most energy from the roof:
a steep tilt gains per module but needs a long row pitch (the rows shade each other), so fewer modules fit. For every candidate tilt it counts the tables that fit (`layout` rules: row pitch
from the sun at noon of the winter solstice, table gap, setback) and the yield of the weather year (`orient`), and keeps the tilt with the most energy in total (or, when a power was asked, the best yield
among the tilts that hold it). The result is the layout input of `epc_pv.plan_layout`, so the plan drawings come from the same engine as a ground plant, plus the frame schedule.

Not calculated: wind uplift, ballast, roof loads and fixings (they need the roof's structural data and the wind code); the result says so. Every datum is given (roof size, setback, walkway, frame shape,
clearance): nothing is defaulted here.
"""
import math
from typing import Any, Dict, List, Optional, Tuple

from epc_pv import equipment
from epc_pv import layout as lay
from epc_pv import orient
from epc_pv.messages import bi, item
from epc_pv.model import PvError

SCHEMA_VERSION = "1.0"
REQUIRED = ("width_m", "length_m", "setback_m", "walkway_m", "module_dimensions_mm", "module_gap_m", "table", "table_gap_m", "front_clearance_m", "station", "inverter_pad", "array")
TILTS_DEG = tuple(range(5, 41, 5))


def check(spec: Any) -> None:
    lay._need(spec, REQUIRED, "flat_roof")
    for key in ("width_m", "length_m"):
        lay._number(spec, key, "flat_roof")
    for key in ("setback_m", "walkway_m", "module_gap_m", "table_gap_m", "front_clearance_m"):
        lay._number(spec, key, "flat_roof", positive=False)
    lay._need(spec["table"], lay.TABLE_KEYS, "flat_roof.table")
    lay._need(spec["array"], ("module", "inverter"), "flat_roof.array")


def _layout(spec: Dict[str, Any]) -> Dict[str, Any]:
    return {"site": {"width_m": spec["width_m"], "length_m": spec["length_m"], "setback_m": spec["setback_m"]}, "module_dimensions_mm": spec["module_dimensions_mm"], "module_gap_m": spec["module_gap_m"],
            "table": spec["table"], "table_gap_m": spec["table_gap_m"], "road_width_m": spec["walkway_m"], "station": spec["station"], "inverter_pad": spec["inverter_pad"],
            "mounting": spec.get("mounting", "roof"), **({"structure_id": spec["structure_id"]} if spec.get("structure_id") is not None else {})}


def capacity(spec: Dict[str, Any], tilt_deg: float, altitude_deg: float) -> Dict[str, Any]:
    """Tables and modules that fit on the roof at `tilt_deg` (same rules as `epc_pv.layout.plan`)."""
    layout = _layout(spec)
    size, frame = lay.table_size(layout), lay._frame(layout)
    footprint = size["slope_m"] * math.cos(math.radians(tilt_deg))
    pitch = lay.row_pitch_m(size["slope_m"], tilt_deg, altitude_deg)
    per_row = max(int((frame["x1"] - frame["x0"] + layout["table_gap_m"]) // (size["width_m"] + layout["table_gap_m"])), 0)
    depth = frame["y1"] - frame["y0"]
    rows = int((depth - footprint) // pitch) + 1 if depth >= footprint else 0
    tables = per_row * rows
    return {"tilt_deg": float(tilt_deg), "tables": tables, "modules": tables * int(spec["table"]["rows"] * spec["table"]["modules_per_row"]), "pitch_m": round(pitch, 3), "footprint_m": round(footprint, 3)}


def _document(document: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any]:
    return dict(document, arrays=[dict(spec["array"], id="A1", tilt_deg=0, azimuth_deg=0, n_modules=1)])


def _options(document: Dict[str, Any], spec: Dict[str, Any], altitude: float, azimuth: float) -> List[Dict[str, Any]]:
    """Capacity and yield of every candidate tilt (a tilt the person fixed is the only candidate)."""
    base = _document(document, spec)
    return [dict(capacity(spec, t, altitude), specific_yield_kwh_kwp=orient._yield(base, t, azimuth)) for t in candidate_tilts(spec)]


def candidate_tilts(spec: Dict[str, Any]) -> Tuple[float, ...]:
    """The tilts to try: the one the person fixed, else those of `TILTS_DEG` inside the range of the structure record (its lowest tilt when none of them is inside)."""
    if "tilt_deg" in spec:
        return (float(spec["tilt_deg"]),)
    window = equipment.tilt_range_deg(spec.get("structure_id"))
    if window is None:
        return TILTS_DEG
    return tuple(t for t in TILTS_DEG if window[0] <= t <= window[1]) or (window[0],)


def propose(document: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any]:
    """The assumed-flat roof structure: tilt, azimuth, modules, layout input and frame schedule. `document` carries the site and the weather."""
    check(spec)
    site = document["site"]
    altitude = lay.solar_altitude_deg(float(site["latitude_deg"]), float(site["longitude_deg"]))
    azimuth = float(spec["azimuth_deg"]) if "azimuth_deg" in spec else orient.equator_azimuth_deg(float(site["latitude_deg"]))
    options = _options(document, spec, altitude, azimuth)
    target = spec.get("target_modules")
    pool = [o for o in options if target is None or o["modules"] >= target] or options
    best = max(pool, key=lambda o: ((min(o["modules"], target) if target else o["modules"]) * o["specific_yield_kwh_kwp"], -o["tilt_deg"]))
    modules = min(best["modules"], target) if target else best["modules"]
    short = max((target or 0) - best["modules"], 0)
    return {"schema_version": SCHEMA_VERSION, "assumption": spec.get("assumption", "flat roof, tilted frames facing the equator"), "tilt_deg": best["tilt_deg"], "azimuth_deg": azimuth, "modules": modules,
            "capacity_modules": best["modules"], "options": options, "layout": _layout(spec), "structure": structure(spec, best), "fits": short == 0,
            "warnings": [item("roof_short", n=short, capacity=best["modules"])] if short else []}


def compare_structures(document: Dict[str, Any], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The ground fixed-table structures that state a tilt range, each tried on the same site: [{structure_id, tilt_deg, modules, specific_yield_kwh_kwp, energy_index}] best first, where `energy_index` is
    modules x specific yield (kWh/kWp, relative: the DC power of a module is the same for all). Structures without a range, trackers and structures that hold no module on the site are left out. Cost is not compared (no price data)."""
    rows = []
    for record in equipment.structures("ground"):
        if "fixed_table" not in record["id"] or equipment.tilt_range_deg(record["id"]) is None:
            continue
        try:
            found = propose(document, dict(spec, structure_id=record["id"]))
        except PvError:
            continue
        best = next(o for o in found["options"] if o["tilt_deg"] == found["tilt_deg"])
        if found["modules"] >= 1:
            rows.append({"structure_id": record["id"], "tilt_deg": found["tilt_deg"], "modules": found["modules"], "specific_yield_kwh_kwp": best["specific_yield_kwh_kwp"],
                         "energy_index": round(found["modules"] * best["specific_yield_kwh_kwp"], 1)})
    return sorted(rows, key=lambda r: (-r["energy_index"], r["structure_id"]))


def fit_table(layout: Dict[str, Any]) -> Dict[str, Any]:
    """The layout with the largest table (modules per row, then rows) that fits inside the site; the same layout, untouched, when the table already fits. The shape is the person's table reduced, never enlarged."""
    frame, table = lay._frame(layout), dict(layout["table"])
    smallest = math.cos(math.radians(min(TILTS_DEG)))
    fitted = dict(layout, table=table)
    while table["modules_per_row"] > 1 and lay.table_size(fitted)["width_m"] > frame["x1"] - frame["x0"]:
        table["modules_per_row"] -= 1
    while table["rows"] > 1 and lay.table_size(fitted)["slope_m"] * smallest > frame["y1"] - frame["y0"]:
        table["rows"] -= 1
    return fitted if table != layout["table"] else layout


def fit_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """The `propose` input with the table reduced until it fits the roof (`fit_table`); the same spec, untouched, when it already fits."""
    fitted = fit_table(_layout(spec))
    frame = lay._frame(fitted)
    if lay.table_size(fitted)["width_m"] > frame["x1"] - frame["x0"]:      # one module across still does not fit: turn the module the other way
        turned = dict(fitted, table=dict(fitted["table"], orientation="landscape" if fitted["table"]["orientation"] == "portrait" else "portrait"))
        fitted = fit_table(turned)
    return spec if fitted["table"] == spec["table"] else dict(spec, table=fitted["table"])


def minimum_roof_m(spec: Dict[str, Any]) -> Dict[str, float]:
    """Smallest roof (width, length in metres) that holds one module with the setback and the walkway of `spec`, the module in its best orientation at the lowest candidate tilt."""
    short_m = min(spec["module_dimensions_mm"]) / 1000.0
    s = float(spec["setback_m"])
    return {"width_m": round(short_m + 2 * s, 2), "length_m": round(short_m * math.cos(math.radians(min(TILTS_DEG))) + 2 * s + float(spec["walkway_m"]), 2)}


def spec_from_layout(layout: Dict[str, Any], array: Dict[str, Any], target_modules: Optional[int] = None) -> Dict[str, Any]:
    """The `propose` input of a ground site: the plant layout (site, tables, road, station) filled with as many tables as fit; `target_modules` caps it (None: fill the site).
    `front_clearance_m` (the lowest edge above the ground) is given in the layout: nothing is defaulted here."""
    lay._need(layout, ("front_clearance_m",), "layout")
    site = layout["site"]
    spec = {"width_m": site["width_m"], "length_m": site["length_m"], "setback_m": site["setback_m"], "walkway_m": layout["road_width_m"], "module_dimensions_mm": layout["module_dimensions_mm"],
            "module_gap_m": layout["module_gap_m"], "table": layout["table"], "table_gap_m": layout["table_gap_m"], "front_clearance_m": layout["front_clearance_m"], "station": layout["station"],
            "inverter_pad": layout["inverter_pad"], "array": array, "assumption": "ground plant, tables facing the equator filled to the site"}
    spec["mounting"] = "ground"
    if layout.get("structure_id") is not None:
        spec["structure_id"] = layout["structure_id"]
    spec.update({k: array[k] for k in ("tilt_deg", "azimuth_deg") if k in array})
    if target_modules is not None:
        spec["target_modules"] = target_modules
    return spec


def structure(spec: Dict[str, Any], best: Dict[str, Any]) -> Dict[str, Any]:
    """The frame schedule: how many frames, their tilt and heights. Wind, ballast and fixings are NOT calculated."""
    layout = _layout(spec)
    size = lay.table_size(layout)
    tilt = math.radians(best["tilt_deg"])
    front = float(spec["front_clearance_m"])
    return {"frames": best["tables"], "modules_per_frame": int(spec["table"]["rows"] * spec["table"]["modules_per_row"]), "tilt_deg": best["tilt_deg"], "frame_width_m": round(size["width_m"], 3),
            "frame_slope_m": round(size["slope_m"], 3), "front_height_m": front, "rear_height_m": round(front + size["slope_m"] * math.sin(tilt), 3), "row_pitch_m": best["pitch_m"],
            "not_calculated": bi("wind uplift, ballast, roof loads and fixings (need the roof structure data and the wind code)", "succión del viento, lastre, cargas del techo y fijaciones (requieren datos de la estructura del techo y la norma de viento)")}
