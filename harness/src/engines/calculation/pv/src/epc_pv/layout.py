"""Plant layout: where the tables, the inverters and the station go inside the site, and which strings sit on which table.

The yield run (`pipeline.run`) says how many modules, strings and inverters every array has; this module places them. It is geometry only, in metres, origin at the
south-west corner of the site, x to the east, y to the north (a plane that faces the sun in the southern hemisphere faces north, azimuth 0).

  row pitch   D = l (sin b / tan a + cos b)   l: slope length of a table, b: tilt, a: apparent solar altitude at solar noon of the winter solstice
  tables      a table is `rows` x `modules_per_row` modules; the last table of an array holds the remaining modules
  strings     string s covers modules s*n .. (s+1)*n-1 of its array, in table order; the strings are shared among the inverters as evenly as possible (inverter of string s: s*I // S)

Every datum of the layout is given (site, module size, table shape, gaps, road, station, inverter pad): nothing is defaulted. If the tables do not fit, the
result says `fits: false` with the tables that were left out, and a warning; it never shrinks a distance to make them fit.
"""
import math
from datetime import date
from typing import Any, Dict, List, Optional

from epc_pv import solar
from epc_pv.messages import bi, item
from epc_pv.model import PvError

REQUIRED = ("site", "module_dimensions_mm", "module_gap_m", "table", "table_gap_m", "road_width_m", "station", "inverter_pad")
SITE_KEYS = ("width_m", "length_m", "setback_m")
TABLE_KEYS = ("rows", "modules_per_row", "orientation")
PAD_KEYS = ("width_m", "depth_m")
ORIENTATIONS = ("portrait", "landscape")
SCHEMA_VERSION = "1.0"


def _need(block: Any, keys, where: str) -> None:
    if not isinstance(block, dict):
        raise PvError("err_type", name=where, kind=bi("an object", "un objeto"))
    missing = [k for k in keys if k not in block]
    if missing:
        raise PvError("err_missing", where=where, names=", ".join(missing))


def _number(block: Dict[str, Any], key: str, where: str, positive: bool = True) -> float:
    value = block[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (value <= 0 if positive else value < 0):
        raise PvError("err_range", name=f"{where}.{key}", rule=">0" if positive else ">=0", value=value)
    return float(value)


def check(layout: Any) -> None:
    """Refuse an incomplete or wrong layout input, in English and Spanish."""
    _need(layout, REQUIRED, "layout")
    _need(layout["site"], SITE_KEYS, "layout.site")
    _need(layout["table"], TABLE_KEYS, "layout.table")
    _need(layout["station"], PAD_KEYS, "layout.station")
    _need(layout["inverter_pad"], PAD_KEYS, "layout.inverter_pad")
    for key in ("width_m", "length_m"):
        _number(layout["site"], key, "layout.site")
    _number(layout["site"], "setback_m", "layout.site", positive=False)
    for key in ("rows", "modules_per_row"):
        _number(layout["table"], key, "layout.table")
    if layout["table"]["orientation"] not in ORIENTATIONS:
        raise PvError("err_range", name="layout.table.orientation", rule="portrait or landscape", value=layout["table"]["orientation"])
    dims = layout["module_dimensions_mm"]
    if not (isinstance(dims, list) and len(dims) == 2 and all(isinstance(d, (int, float)) and d > 0 for d in dims)):
        raise PvError("err_type", name="layout.module_dimensions_mm", kind=bi("[long side, short side] in mm", "[lado largo, lado corto] en mm"))
    for key in ("module_gap_m", "table_gap_m", "road_width_m"):
        _number(layout, key, "layout", positive=False)


def solar_altitude_deg(latitude_deg: float, longitude_deg: float) -> float:
    """Apparent altitude of the sun at solar noon of the winter solstice (the design hour of the row spacing)."""
    day = date(2023, 6, 21) if latitude_deg < 0 else date(2023, 12, 21)
    return max(90.0 - solar.position(day, minute, latitude_deg, longitude_deg)[1] for minute in range(0, 1440, 5))


def table_size(layout: Dict[str, Any]) -> Dict[str, float]:
    """Width of the row of modules and slope length of a table, in metres."""
    long_m, short_m = (d / 1000.0 for d in layout["module_dimensions_mm"])
    gap, t = layout["module_gap_m"], layout["table"]
    along, across = (short_m, long_m) if t["orientation"] == "portrait" else (long_m, short_m)
    return {"width_m": t["modules_per_row"] * along + (t["modules_per_row"] - 1) * gap, "slope_m": t["rows"] * across + (t["rows"] - 1) * gap}


def row_pitch_m(slope_m: float, tilt_deg: float, altitude_deg: float) -> float:
    """D = l (sin b / tan a + cos b): the distance between the front edges of two rows that keeps the shade of one off the next at the design hour."""
    b, a = math.radians(tilt_deg), math.radians(altitude_deg)
    return slope_m * (math.sin(b) / math.tan(a) + math.cos(b))


def _array_geometry(spec: Dict[str, Any], size: Dict[str, float], altitude: float) -> Dict[str, float]:
    tilt = float(spec["tilt_deg"])
    return {"tilt_deg": tilt, "footprint_m": size["slope_m"] * math.cos(math.radians(tilt)), "pitch_m": row_pitch_m(size["slope_m"], tilt, altitude)}


def _frame(layout: Dict[str, Any]) -> Dict[str, float]:
    site = layout["site"]
    s = float(site["setback_m"])
    return {"x0": s, "x1": float(site["width_m"]) - s, "y0": s + float(layout["road_width_m"]), "y1": float(site["length_m"]) - s}


def _place_array(spec: Dict[str, Any], arr: Dict[str, Any], geo: Dict[str, float], size: Dict[str, float], layout: Dict[str, Any], frame: Dict[str, float], cursor: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The tables of one array, row by row from the cursor; stops at the first table that does not fit."""
    t = layout["table"]
    per_table = int(t["rows"] * t["modules_per_row"])
    per_row = max(int((frame["x1"] - frame["x0"] + layout["table_gap_m"]) // (size["width_m"] + layout["table_gap_m"])), 0)
    tables, left = [], arr["modules"]
    while left > 0 and per_row > 0:
        y = frame["y0"] + cursor["row"] * geo["pitch_m"]
        if y + geo["footprint_m"] > frame["y1"] + 1e-9:
            break
        for col in range(per_row):
            if left <= 0:
                break
            n = min(per_table, left)
            cursor["table"] += 1
            tables.append({"id": f"T-{cursor['table']:03d}", "array": arr["id"], "row": cursor["row"] + 1, "x": round(frame["x0"] + col * (size["width_m"] + layout["table_gap_m"]), 3), "y": round(y, 3),
                           "width_m": round(size["width_m"], 3), "depth_m": round(geo["footprint_m"], 3), "modules": n, "strings": [], "inverters": []})
            left -= n
        cursor["row"] += 1
    return tables


def _assign_strings(tables: List[Dict[str, Any]], arr: Dict[str, Any], first_string: int, first_inverter: int) -> List[Dict[str, Any]]:
    """Strings and inverters on the placed tables; returns the inverter records (position set later)."""
    n_series, n_strings, count = arr["strings"]["n_series"], arr["strings"]["strings"], arr["inverters"]
    owner = lambda s: first_inverter + s * count // n_strings + 1                       # noqa: E731 - the strings are shared among the inverters as evenly as possible
    inverters = [{"id": f"INV-{first_inverter + j + 1:02d}", "array": arr["id"], "strings": []} for j in range(count)]
    for s in range(n_strings):
        inverters[owner(s) - first_inverter - 1]["strings"].append(f"S-{first_string + s + 1:03d}")
    index = 0
    for table in tables:
        for _ in range(table["modules"]):
            s, index = index // n_series, index + 1
            if s < n_strings:
                _mark(table, f"S-{first_string + s + 1:03d}", f"INV-{owner(s):02d}")
    return inverters


def _mark(table: Dict[str, Any], string: str, inverter: str) -> None:
    for key, value in (("strings", string), ("inverters", inverter)):
        if value not in table[key]:
            table[key].append(value)


def _place_inverters(inverters: List[Dict[str, Any]], tables: List[Dict[str, Any]], pad: Dict[str, float], gap_m: float) -> int:
    """Each inverter sits behind its first table, in the gap between the rows; returns how many do not fit in the gap."""
    first = {}
    for table in tables:
        for inv in table["inverters"]:
            first.setdefault(inv, table)
    tight = 0
    for inv in inverters:
        table = first.get(inv["id"])
        if table is None:
            inv.update(x=None, y=None)
            continue
        inv.update(x=round(table["x"] + table["width_m"] / 2.0, 3), y=round(table["y"] + table["depth_m"] + float(pad["depth_m"]) / 2.0 + 0.05, 3), width_m=float(pad["width_m"]), depth_m=float(pad["depth_m"]))
        tight += gap_m < float(pad["depth_m"]) + 0.1
    return tight


def plan(document: Dict[str, Any], result: Dict[str, Any], layout: Dict[str, Any]) -> Dict[str, Any]:
    """The layout of the plant: tables, inverters, station and the strings on each table (`document`: the epc_pv input, `result`: its `as_dict()`)."""
    check(layout)
    site = document["site"]
    altitude = solar_altitude_deg(float(site["latitude_deg"]), float(site["longitude_deg"]))
    size, frame = table_size(layout), _frame(layout)
    cursor, tables, inverters, left_out, tight, first_string = {"row": 0, "table": 0}, [], [], 0, 0, 0
    for spec, arr in zip(document["arrays"], result["arrays"]):
        geo = _array_geometry(spec, size, altitude)
        placed = _place_array(spec, arr, geo, size, layout, frame, cursor)
        invs = _assign_strings(placed, arr, first_string, len(inverters))
        tight += _place_inverters(invs, placed, layout["inverter_pad"], geo["pitch_m"] - geo["footprint_m"])
        needed = -(-arr["modules"] // int(layout["table"]["rows"] * layout["table"]["modules_per_row"]))
        left_out += needed - len(placed)
        tables += placed
        inverters += invs
        first_string += arr["strings"]["strings"]
    out = _result(document, layout, size, frame, altitude, tables, inverters, left_out, tight)
    return dict(out, tilts_deg={str(a["id"]): float(a["tilt_deg"]) for a in document["arrays"]})


def _result(document, layout, size, frame, altitude, tables, inverters, left_out, tight) -> Dict[str, Any]:
    warnings = []
    if left_out:
        warnings.append(item("layout_no_fit", n=left_out))
    if tight:
        warnings.append(item("layout_pad_tight", n=tight))
    site, st = layout["site"], layout["station"]
    s = float(site["setback_m"])
    station = {"x": s, "y": s, "width_m": float(st["width_m"]), "depth_m": float(st["depth_m"])}
    return {"schema_version": SCHEMA_VERSION, "site": {k: float(site[k]) for k in SITE_KEYS}, "road_width_m": float(layout["road_width_m"]), "solar_altitude_deg": round(altitude, 3),
            "table": {"rows": layout["table"]["rows"], "modules_per_row": layout["table"]["modules_per_row"], "orientation": layout["table"]["orientation"], "width_m": round(size["width_m"], 3),
                      "slope_m": round(size["slope_m"], 3)},
            "pitch_m": sorted({round(row_pitch_m(size["slope_m"], float(a["tilt_deg"]), altitude), 3) for a in document["arrays"]}),
            "module": {"dimensions_mm": [float(d) for d in layout["module_dimensions_mm"][:2]], "gap_m": float(layout["module_gap_m"]), "front_clearance_m": float(layout["front_clearance_m"]) if "front_clearance_m" in layout else None},
            "frame": {k: round(v, 3) for k, v in frame.items()}, "station": station, "tables": tables, "inverters": inverters,
            "counts": {"tables": len(tables), "tables_left_out": left_out, "inverters": len(inverters), "rows": max([t["row"] for t in tables], default=0)},
            "fits": left_out == 0, "warnings": warnings}
