"""A building drawn from a description, not read from a file: rooms given as rectangles in metres become walls, doors, windows and rooms (an `Architecture`), and a plan sheet
(DXF, with the layers and the typeface of `epc_style.json` and the IRAM title block) that `recognize` reads back with the same rooms, codes and names.

The description of one floor:

    {"name": "PLANTA BAJA", "index": 0,                      # the title of the plan and its level (0 ground floor, 1 first floor, -1 basement)
     "wall_thickness_m": 0.20,
     "rooms": [{"code": "PB-01", "name": "Local comercial", "key": "SHOP", "box_m": [0, 0, 8, 7]}],     # box between wall axes: [west, south, east, north], x to the east, y to the north
     "doors": [{"room": "PB-01", "side": "E", "width_m": 0.9, "offset_m": 3.5, "opens": "in"}],        # offset: from the west (or south) end of that side of the room to the middle of the door; default the middle
     "windows": [{"room": "PB-01", "side": "W", "width_m": 2.0}],
     "heights_m": {"wall_height_m": 3.0, "door_head_m": 2.1, "window_sill_m": 0.9, "window_head_m": 2.1, "slab_m": 0.2, "elevation_m": 0.0}}      # optional; never assumed: without it there is no isometric, elevation or section

Every plan is a presentation sheet: the plan with its dimension chains, the tags of the doors and windows, the room schedule, the opening schedule and the general notes (`epc_arch.presentation`),
the doors and windows being blocks with a wipeout. With `heights_m` in every floor, `ISO.dxf` (the isometric of the whole building), `ELEV_S_<floor>.dxf` and `SEC_A_<floor>.dxf` are written too.

Nothing is assumed: the thickness, every box and every width are given. Rooms must not overlap; walls are the sides of the rooms (a side two rooms share is one wall).
`python -m epc_arch.author DESCRIPTION.json --out DIR [--sheet A1]` writes one DXF per floor (`<floor>.dxf`); the description is `{"floors": [...]}` or one floor.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from epc_arch.model import ArchError, Architecture, Level, Opening, Room, Wall

FIT = 20                                    # the smallest scale denominator asked for: the view takes the first standard scale that fits the sheet
MM = 1000.0                                # plan units per metre of an authored plan
SIDES = ("N", "S", "E", "W")
LEVEL_KEYS = {0: "GROUND_FLOOR", 1: "FIRST_FLOOR", 2: "SECOND_FLOOR", 3: "THIRD_FLOOR", -1: "BASEMENT"}
FLOOR_FIELDS = {"name", "index", "wall_thickness_m", "rooms", "doors", "windows", "heights_m"}
ROOM_FIELDS = {"code", "name", "key", "box_m"}
OPENING_FIELDS = {"room", "side", "width_m", "offset_m", "opens", "id"}


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_box(box: Any) -> bool:
    return isinstance(box, list) and len(box) == 4 and all(_num(v) for v in box) and box[0] < box[2] and box[1] < box[3]


def _room_errors(r: Any, here: str) -> List[str]:
    if not isinstance(r, dict):
        return [f"{here}: must be an object"]
    out = [f"{here}: unknown key(s) {', '.join(sorted(set(r) - ROOM_FIELDS))}"] if set(r) - ROOM_FIELDS else []
    out += [f"{here}/{k}: required text" for k in ("code", "name") if not isinstance(r.get(k), str) or not r.get(k)]
    if not _is_box(r.get("box_m")):
        out.append(f"{here}/box_m: required, [west, south, east, north] in metres with west < east and south < north")
    return out


def _overlaps(rooms: List[dict]) -> List[str]:
    out = []
    for i, a in enumerate(rooms):
        for b in rooms[i + 1:]:
            p, q = a["box_m"], b["box_m"]
            if min(p[2], q[2]) - max(p[0], q[0]) > 1e-9 and min(p[3], q[3]) - max(p[1], q[1]) > 1e-9:
                out.append(f"rooms {a['code']} and {b['code']} overlap")
    return out


def _opening_basics(o: dict, here: str, rooms: Dict[str, dict]) -> List[str]:
    """The first thing wrong with the room, the side or the width of an opening (the rest cannot be judged without them)."""
    if o.get("room") not in rooms:
        return [f"{here}/room: required, the code of one of the rooms"]
    if o.get("side") not in SIDES:
        return [f"{here}/side: required, one of N, S, E, W"]
    if not _num(o.get("width_m")) or o["width_m"] <= 0:
        return [f"{here}/width_m: required, a width in metres above 0"]
    return []


def _fit_errors(o: dict, here: str, box: List[float]) -> List[str]:
    lo, hi = _span(box, o["side"])
    at = o.get("offset_m", (hi - lo) / 2)
    if not _num(at) or at - o["width_m"] / 2 < -1e-9 or at + o["width_m"] / 2 > hi - lo + 1e-9:
        return [f"{here}/offset_m: the opening ({o['width_m']} m wide) does not fit in that side of the room ({round(hi - lo, 3)} m)"]
    return []


def _opening_errors(o: Any, here: str, rooms: Dict[str, dict], door: bool) -> List[str]:
    if not isinstance(o, dict):
        return [f"{here}: must be an object"]
    allowed = OPENING_FIELDS if door else OPENING_FIELDS - {"opens"}
    out = [f"{here}: unknown key(s) {', '.join(sorted(set(o) - allowed))}"] if set(o) - allowed else []
    basics = _opening_basics(o, here, rooms)
    if basics:
        return out + basics
    if door and o.get("opens", "in") not in ("in", "out"):
        out.append(f"{here}/opens: `in` (into the room, the default) or `out`")
    return out + _fit_errors(o, here, rooms[o["room"]]["box_m"])


def _floor_basics(floor: dict) -> List[str]:
    out = [f"unknown key(s) {', '.join(sorted(set(floor) - FLOOR_FIELDS))}"] if set(floor) - FLOOR_FIELDS else []
    if not isinstance(floor.get("name"), str) or not floor.get("name"):
        out.append("name: required text (the title of the plan, as `PLANTA BAJA`)")
    if not isinstance(floor.get("index"), int) or isinstance(floor.get("index"), bool):
        out.append("index: required, the level as a whole number (0 the ground floor)")
    if not _num(floor.get("wall_thickness_m")) or floor["wall_thickness_m"] <= 0:
        out.append("wall_thickness_m: required, above 0")
    return out


def _rooms_errors(rooms: Any) -> List[str]:
    if not isinstance(rooms, list) or not rooms:
        return ["rooms: required, at least one room"]
    bad = [e for i, r in enumerate(rooms) for e in _room_errors(r, f"rooms/{i}")]
    if bad:
        return bad
    codes = [r["code"] for r in rooms]
    return [f"rooms: the code {c} is used twice" for c in sorted({c for c in codes if codes.count(c) > 1})] + _overlaps(rooms)


def _openings_errors(floor: dict, by_code: Dict[str, dict]) -> List[str]:
    out: List[str] = []
    for key, door in (("doors", True), ("windows", False)):
        items = floor.get(key, [])
        if not isinstance(items, list):
            out.append(f"{key}: must be a list")
            continue
        out += [e for i, o in enumerate(items) for e in _opening_errors(o, f"{key}/{i}", by_code, door)]
    return out


def errors_of(floor: Any) -> List[str]:
    """What is wrong with the description of a floor (empty when it can be drawn)."""
    if not isinstance(floor, dict):
        return ["the floor must be an object"]
    out = _floor_basics(floor)
    bad = _rooms_errors(floor.get("rooms"))
    if bad:
        return out + bad
    return out + _openings_errors(floor, {r["code"]: r for r in floor["rooms"]}) + _heights_errors(floor)


def _heights_errors(floor: dict) -> List[str]:
    if "heights_m" not in floor:
        return []
    from epc_arch.sections import heights_errors
    return [f"heights_m: {e}" for e in heights_errors(floor["heights_m"])]


def _span(box: List[float], side: str) -> Tuple[float, float]:
    """The interval one side of a box runs along (x for N and S, y for W and E)."""
    return (box[0], box[2]) if side in "NS" else (box[1], box[3])


def _fixed(box: List[float], side: str) -> float:
    return {"S": box[1], "N": box[3], "W": box[0], "E": box[2]}[side]


def _wall_lines(rooms: List[dict]) -> List[Tuple[bool, float, float, float]]:
    """The sides of every room as (horizontal, position, start, end), those on one line that touch or overlap merged into one wall."""
    lines: Dict[Tuple[bool, float], List[Tuple[float, float]]] = {}
    for r in rooms:
        for side in SIDES:
            lines.setdefault((side in "NS", round(_fixed(r["box_m"], side), 6)), []).append(_span(r["box_m"], side))
    out = []
    for (horizontal, pos), spans in sorted(lines.items()):
        merged: List[List[float]] = []
        for a, b in sorted(spans):
            if merged and a <= merged[-1][1] + 1e-9:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        out += [(horizontal, pos, a, b) for a, b in merged]
    return out


class _Frame:
    """From the metres of the description (y to the north) to the plan space (millimetres, y down, the building's north-west corner at half a wall from the origin)."""

    def __init__(self, rooms: List[dict], thickness: float):
        self.x0 = min(r["box_m"][0] for r in rooms)
        self.y1 = max(r["box_m"][3] for r in rooms)
        self.pad = thickness / 2
        self.size = ((max(r["box_m"][2] for r in rooms) - self.x0 + thickness) * MM, (self.y1 - min(r["box_m"][1] for r in rooms) + thickness) * MM)

    def __call__(self, x: float, y: float) -> Tuple[float, float]:
        return ((x - self.x0 + self.pad) * MM, (self.y1 - y + self.pad) * MM)


def _walls(rooms: List[dict], T: float, f: _Frame) -> Tuple[List[Wall], List[Tuple[bool, float, float, float]]]:
    lines = _wall_lines(rooms)
    walls = []
    for i, (horizontal, pos, a, b) in enumerate(lines, 1):
        p, q = (f(a, pos), f(b, pos)) if horizontal else (f(pos, a), f(pos, b))
        walls.append(Wall(f"w{i}", p, q, T * MM, 1.0, "authored"))
    return walls, lines


def _wall_at(lines, walls: List[Wall], horizontal: bool, pos: float, t: float) -> str:
    for line, w in zip(lines, walls):
        if line[0] == horizontal and abs(line[1] - pos) < 1e-6 and line[2] - 1e-9 <= t <= line[3] + 1e-9:
            return w.id
    return ""


def _opening(o: dict, kind: str, n: int, room: dict, lines, walls: List[Wall], f: _Frame) -> Opening:
    box, side, width = room["box_m"], o["side"], float(o["width_m"])
    horizontal = side in "NS"
    lo, hi = _span(box, side)
    t = lo + o.get("offset_m", (hi - lo) / 2)
    pos = _fixed(box, side)
    at = f(t, pos) if horizontal else f(pos, t)
    wall = _wall_at(lines, walls, horizontal, pos, t)
    ident = o.get("id") or f"{'d' if kind == 'door' else 'v'}{n}"
    if kind != "door":
        return Opening(ident, kind, at, width * MM, 0.0 if horizontal else 90.0, wall, 1.0, "authored")
    inward = {"S": 1.0, "N": -1.0, "W": 1.0, "E": -1.0}[side] * (1.0 if o.get("opens", "in") == "in" else -1.0)     # towards the inside of the room, in metres (y to the north)
    start = t - width / 2
    hinge = f(start, pos) if horizontal else f(pos, start)
    swing = f(start, pos + inward * width) if horizontal else f(pos + inward * width, start)
    return Opening(ident, "door", at, width * MM, 0.0 if horizontal else 90.0, wall, 1.0, "authored", hinge, swing)


def _room(r: dict, T: float, f: _Frame) -> Room:
    x0, y0, x1, y1 = r["box_m"]
    (ax, ay), (bx, by) = f(x0 + T / 2, y1 - T / 2), f(x1 - T / 2, y0 + T / 2)
    area = (bx - ax) * (by - ay)
    return Room(r["code"], area, area / MM ** 2, ((ax + bx) / 2, (ay + by) / 2), [(ax, ay, bx, by)], r["name"], r.get("key", ""), r["code"])


def architecture_of(floor: Dict[str, Any], source: str = "") -> Architecture:
    """The architecture of a described floor; an `ArchError` lists what is wrong with the description."""
    bad = errors_of(floor)
    if bad:
        raise ArchError("err_description_not_drawable", reason='; '.join(bad))
    T, rooms = float(floor["wall_thickness_m"]), floor["rooms"]
    f = _Frame(rooms, T)
    walls, lines = _walls(rooms, T, f)
    by_code = {r["code"]: r for r in rooms}
    openings = [_opening(o, "door", i, by_code[o["room"]], lines, walls, f) for i, o in enumerate(floor.get("doors", []), 1)]
    openings += [_opening(o, "window", i, by_code[o["room"]], lines, walls, f) for i, o in enumerate(floor.get("windows", []), 1)]
    level = Level(floor["name"], floor["index"], "text", LEVEL_KEYS.get(floor["index"], ""))
    return Architecture(source=source or f"{floor['name']}.dxf", size=f.size, units_per_metre=MM, scale_hint=None, wall_thickness=T * MM, walls=walls, openings=openings,
                        rooms=[_room(r, T, f) for r in rooms], level=level)


def plan_dxf(arch: Architecture, sheet: str = "A1", fields: Optional[Dict[str, str]] = None, template=None) -> str:
    """The plan of an architecture on an IRAM sheet, as DXF text: the layers and the typeface of `epc_style.json`; `fields` fills the title block (client, project, revision...); `template` is the IRAM sheet as data (`epc_arch.sheets.template_from_svg`), none = the engine's own frame."""
    from epc_arch.drawing import build_drawing, load_style
    from epc_arch.export.export_dxf import to_dxf
    style = load_style()
    title = arch.level.name if arch.level else ""
    drawing = build_drawing(arch, style=style, sheet=sheet, template=template, document=arch.source, fields=dict({"denominacion": title}, **(fields or {})), presentation=True)
    return to_dxf(drawing, style)


def _origin(floor: Dict[str, Any]) -> Tuple[float, float]:
    """The world point (metres) the plan frame of a floor starts at: west of its west wall face and north of its north wall face."""
    pad = float(floor["wall_thickness_m"]) / 2
    return (min(r["box_m"][0] for r in floor["rooms"]) - pad, max(r["box_m"][3] for r in floor["rooms"]) + pad)


def building_views(floors: List[Dict[str, Any]], archs: List[Architecture], sheet: str = "A1", fields: Optional[Dict[str, str]] = None, template=None) -> Dict[str, str]:
    """The views the heights allow, as DXF text by file name: the isometric of the building, and the south elevation and the section A of each floor. Empty when a floor has no `heights_m`."""
    if not floors or any("heights_m" not in f for f in floors):
        return {}
    from epc_arch.drawing import load_style
    from epc_arch.export.export_dxf import to_dxf
    from epc_arch.isometric import isometric_drawing
    from epc_arch.sections import elevation, section, view_dxf
    corner = (min(_origin(f)[0] for f in floors), max(_origin(f)[1] for f in floors))
    parts = [(a, f["heights_m"], (_origin(f)[0] - corner[0], _origin(f)[1] - corner[1])) for f, a in zip(floors, archs)]
    style = load_style()
    out = {"ISO.dxf": to_dxf(isometric_drawing(parts, style, sheet, None, template, fields), style)}
    for f, a in zip(floors, archs):
        stem = _stem(f)
        h = f["heights_m"]
        out[f"ELEV_S_{stem}.dxf"] = view_dxf(elevation(a, "S", h), a, sheet, FIT, fields, template)
        mid = (min(r["box_m"][0] for r in f["rooms"]) + max(r["box_m"][2] for r in f["rooms"])) / 2 - _origin(f)[0]
        out[f"SEC_A_{stem}.dxf"] = view_dxf(section(a, "x", mid, "E", h), a, sheet, FIT, fields, template)
    return out


def floors_of(description: Any) -> List[Dict[str, Any]]:
    if isinstance(description, dict) and isinstance(description.get("floors"), list):
        return description["floors"]
    return [description]


def _stem(floor: Dict[str, Any]) -> str:
    index = floor.get("index")
    return {0: "PB"}.get(index, f"P{index}" if isinstance(index, int) and index > 0 else f"S{-index}" if isinstance(index, int) else "plan")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="epc_arch.author", description="draw the plans of a building from its description (rooms as rectangles in metres)")
    ap.add_argument("description")
    ap.add_argument("--out", default="out")
    ap.add_argument("--sheet", default="A1")
    ap.add_argument("--fields", default=None, help="a JSON file with the fields of the title block")
    a = ap.parse_args(argv)
    try:
        floors = floors_of(json.loads(Path(a.description).read_text(encoding="utf-8")))
        fields = json.loads(Path(a.fields).read_text(encoding="utf-8")) if a.fields else None
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        from epc_arch.cli_v2 import iram_template                      # the command line is the adapter: it fetches the sheet and hands it to the engine as data
        template = iram_template(a.sheet)
        archs = []
        for floor in floors:
            name = f"{_stem(floor)}.dxf"
            arch = architecture_of(floor, name)
            archs.append(arch)
            (out / name).write_text(plan_dxf(arch, a.sheet, fields, template), encoding="utf-8")
            print(f"OK {name}: {len(arch.rooms)} rooms, {len(arch.walls)} walls, {arch.counts()['doors']} doors, {arch.counts()['windows']} windows")
        views = building_views(floors, archs, a.sheet, fields, template)
        for name, text in views.items():
            (out / name).write_text(text, encoding="utf-8")
            print(f"OK {name}")
        if not views:
            print("NOTE no isometric, elevations or sections: every floor needs `heights_m` / falta `heights_m` en cada planta para el isométrico, las elevaciones y los cortes")
    except (ArchError, OSError, ValueError) as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
