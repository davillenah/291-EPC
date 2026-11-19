"""From the landing form to a project the pipeline can run: plans drawn by `epc_arch.author`, the load list and the `engine_inputs` of the building.

Every value is either typed in the form or a proposal of `house_defaults.json` shown in the form (pending review); nothing is calculated here.
The plans go to `inputs/plans/` through the project store (inputs are immutable after intake), the run is the `epc run` command.
"""
import contextlib
import io
import json
import re
import tempfile
from pathlib import Path

import brief
import house

D = house.DEFAULTS
KIND_ORDER = ("bathroom", "bedroom", "kitchen", "garage", "laundry", "living")


def kind_of(name):
    """The kind of room a written name is (`Baño 2` -> bathroom, `Pasillo` -> hall); living (the generic room) when no word matches."""
    text = brief.fold(name)
    if re.search(r"pasillo|hall|corredor|corridor", text):
        return "hall"
    if re.search(r"escalera|stair", text):
        return "stair"
    return next((k for k in KIND_ORDER if re.search(brief.KINDS[k], text)), "living")


def _num(vals, key, default):
    try:
        return float(vals.get(key) if vals.get(key) not in (None, "") else default)
    except (TypeError, ValueError):
        return float(default)


def floors_of(vals, rows):
    """The `epc_arch.author` descriptions of the floors (rooms grouped by the prefix of their code: PB, P1) from the form values."""
    height, slab = _num(vals, "house.wall_height_m", D["wall_height_m"]), 0.2
    out = []
    for prefix, group in house.floors_of(rows):
        index = house.floor_index(prefix)
        name = (vals.get("floor.name") if index == 0 else None) or house.floor_name(prefix, vals.get("language") or "es")
        out.append(house.floor_description(group, name=name, index=index, wall_thickness_m=_num(vals, "floor.wall_thickness_m", D["wall_thickness_m"]),
                                           wall_height_m=height, elevation_m=index * (height + slab)))
    return out


def floor_of(vals, rows):
    """The description of the first floor (kept for callers with one floor)."""
    return floors_of(vals, rows)[0]


def author_plans(descriptions):
    """{file name: DXF text} drawn by `epc_arch.author` (the plan of each floor and, with heights, the isometric, elevations and sections); raises ValueError with its message."""
    descriptions = descriptions if isinstance(descriptions, list) else [descriptions]
    from epc_arch import author
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "description.json"
        src.write_text(json.dumps({"floors": descriptions}), encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = author.main([str(src), "--out", str(Path(tmp) / "plans")])
        if code:
            raise ValueError(err.getvalue().strip() or "the plan could not be drawn")
        return {p.name: p.read_bytes() for p in sorted((Path(tmp) / "plans").glob("*.dxf"))}


def _luminaires(vals, garden):
    lum = dict(D["luminaire"], power_w=_num(vals, "house.luminaire_power_w", D["luminaire"]["power_w"]), lamp_flux_lm=_num(vals, "house.luminaire_flux_lm", D["luminaire"]["lamp_flux_lm"]))
    return [lum] + ([dict(D["floodlight"])] if garden else [])


def _room_data(row, vals, with_plugs):
    kind = kind_of(row["name"])
    base = D["rooms"].get(kind, D["rooms"]["living"])
    data = {"activity": D["hall_activity"] if kind == "hall" else base["activity"], "height_m": _num(vals, "house.wall_height_m", D["wall_height_m"]), "luminaire": D["luminaire"]["id"]}
    use = D["hall_use"] if kind == "hall" else base["use"]
    data["receptacles"] = {"use": use, "receptacle": D["receptacle"]["id"]} if with_plugs else False
    return data


def garden_of(vals):
    """The exterior lighting area of the garden when the form has one (area in m2), else None."""
    area = _num(vals, "house.garden_area_m2", 0)
    if area <= 0:
        return None
    return {"id": "EXT1", "name": "Jardin", "area_m2": area, "luminaire": D["floodlight"]["id"], "target_lux": _num(vals, "house.garden_lux", D["garden"]["target_lux"]),
            "load": {"area": "PB", "phases": D["garden"]["phases"], "length": {"value": _num(vals, "house.garden_length_m", D["garden"]["length_m"]), "unit": "m"}}}


def _floor_inputs(prefix, group, vals, plugs, main):
    """The building entry of one floor: its plan, level, rooms with their lighting (and receptacle) data, and the board; off the main floor the shaft of the stair too."""
    index, height = house.floor_index(prefix), _num(vals, "house.wall_height_m", D["wall_height_m"])
    board = house.board_point(group)
    floor = {"id": prefix, "name": house.floor_name(prefix, vals.get("language") or "es"), "phases": int(D["phases"]), "plan": f"plans/{'PB' if index == 0 else prefix}.dxf",
             "elevation_m": round(index * (height + 0.2), 3), "board": board, "rooms": {r["code"]: _room_data(r, vals, plugs) for r in group}}
    if plugs:
        floor["receptacles_load"] = {"phases": int(D["phases"])}
    if prefix != main:
        floor["shaft"] = dict(board)
    return floor, board


def engine_inputs(vals, rows, plan_names):
    """(loads, engine_inputs) of the building: its floors (one or two), their lighting and receptacle data, the board by the stair, the garden lighting."""
    garden, plugs = garden_of(vals), vals.get("house.receptacles", "yes") != "no"
    groups = house.floors_of(rows)
    main = groups[0][0]
    floors, boards = zip(*[_floor_inputs(p, g, vals, plugs, main) for p, g in groups])
    building = {"luminaires": _luminaires(vals, garden), "floors": list(floors), "main_board": dict(boards[0], floor=main)}
    if plugs:
        building["receptacles"] = [dict(D["receptacle"], power_va=_num(vals, "house.receptacle_va", D["receptacle"]["power_va"]))]
    if garden:
        building["exterior"] = [dict(garden, load=dict(garden["load"], area=main))]
    plans = {f["plan"].split("/")[-1] for f in floors}
    sheets = [f"plans/{n}" for n in plan_names if n not in plans]
    if sheets:
        building["presentation_sheets"] = sheets
    inputs = {"board": {"name": D["board"]["name"], "fp_default": _num(vals, "house.board_fp", D["board"]["fp_default"])}, "building": building}
    loads = {"schema_version": "1.0", "areas": [{"id": f["id"], "name": f["name"], "plan": f["plan"]} for f in floors], "loads": []}
    return loads, inputs


def rows_of(raw):
    """The room rows of the form ([{code, name, west, south, east, north}] as text or numbers) with numbers; (rows, problem). Rows left empty are dropped."""
    rows = []
    for r in raw or []:
        if not any(str(r.get(k, "")).strip() for k in ("code", "name", "west", "south", "east", "north")):
            continue
        try:
            rows.append({"code": str(r.get("code", "")).strip(), "name": str(r.get("name", "")).strip(), **{k: float(r[k]) for k in ("west", "south", "east", "north")}})
        except (KeyError, TypeError, ValueError):
            return [], {"code": "rooms", "detail": str(r.get("code") or r.get("name") or "")}
    return rows, (None if rows else {"code": "no_rooms", "detail": ""})


def _read_back(plans, groups):
    """The reader (`epc_arch`) must find the rooms that were drawn on each floor; a room it splits or merges would give wrong areas and lighting."""
    from disciplines.electrical_lv.intake import building
    for prefix, group in groups:
        name = f"{'PB' if house.floor_index(prefix) == 0 else prefix}.dxf"
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "plans").mkdir()
            (Path(tmp) / "plans" / name).write_bytes(plans[name])
            found = building.resolve_plans({"floors": [{"id": prefix, "plan": f"plans/{name}"}]}, Path(tmp))["floors"][0]["architecture"]["rooms"]
        if len(found) != len(group):
            return {"code": "read_back", "detail": f"{prefix} {len(found)}/{len(group)}"}
    return None


def check_floor(vals, raw_rows):
    """(rows, plans, problem): the rows with numbers, the DXF plans drawn from them and the first problem found ({code, detail}) or None. Nothing is written."""
    rows, problem = rows_of(raw_rows)
    if problem:
        return rows, None, problem
    try:
        plans = author_plans(floors_of(vals, rows))
    except ValueError as exc:
        return rows, None, {"code": "plan", "detail": str(exc).replace("ERROR ", "")[:300]}
    return rows, plans, _read_back(plans, house.floors_of(rows))
