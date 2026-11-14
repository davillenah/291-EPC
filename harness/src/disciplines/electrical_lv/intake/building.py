"""Building intake: the recognised architecture of each floor becomes the lighting rooms and the lighting loads (`L-<floor>`) of the load list.

The load list is frozen in stage 1 and the lighting is calculated in stage 3, so the power of a lighting circuit has to be known before the pipeline starts.
This module is that derivation. It calculates nothing: the power of each lighting load is the installed power that `epc_lighting.run` returns for the
rooms of the floor. Nothing is defaulted: the activity, luminaire, height and coefficient of utilisation of every room, and the phases and run length of
every lighting load, are inputs; a room the caller did not describe is an error unless it is excluded by name on purpose.

`engine_inputs["building"]`:

    {"luminaires": [...],                                  # epc_lighting luminaires
     "options": {...},                                     # optional, epc_lighting.Options fields
     "tolerance_pct": 1,                                   # optional; with it stage 3 compares each load with its rooms
     "floors": [{"id": "PB", "name": "Ground floor",       # `id` is also the area of the load list (added when it is not there)
                 "phases": 1, "length": {"value": 20, "unit": "m"},
                 "architecture": {...},                    # `epc_arch` result as a dict (rooms with `area_m2` and `size_m`)
                 "rooms": {"r1": {...}},                   # per recognised room id: the epc_lighting room fields except id, name and size
                 "by_name": {"HALL": {...}},               # the same, by the written name of the room (exact match); `rooms` wins
                 "exclude": ["r7"]}]}                      # room ids that are deliberately not lit

Receptacles (optional, same rules): `building.receptacles` is the epc_receptacles catalogue, each room's data then carries `receptacles`
(`{"use": ..., "receptacle": <catalogue id>, "count"?, "height_m"?}`, or `false` for a room that deliberately has none), and each floor gives
`receptacles_load` (`{"phases", "length"}`); the load `T-<floor id>` (kind receptacles, VA) is the sum of the load of the engine for the rooms of the floor.
A floor may also give `circuits` (`{"lighting": {...}, "receptacles": {...}}`): the per-circuit options of `engine_inputs.circuits` for its derived loads.

`derive` returns the load list with the derived loads and the `lighting` section for stage 3 (document, options, load map).
`engine_inputs_for` returns the `engine_inputs` of the run: the `lighting` section and the circuit options of the derived loads added.
"""
import copy
import math

from disciplines.electrical_lv.intake.routing import RoutingError, design_floor

SIZE_FIELDS = ("id", "name", "width_m", "length_m")


class BuildingError(ValueError):
    """The building section cannot be turned into lighting loads; `errors` lists the reasons."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = list(errors)


def _is_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _shape(floor, room):
    """(width_m, length_m) of the room: the box of its rectangles scaled to the recognised area (so an L-shaped room keeps its area), shorter side as width."""
    area, size = room.get("area_m2"), room.get("size_m")
    if not area or not size or not all(size):
        raise BuildingError([f"floor {floor['id']}: room {room['id']} has no area or size in metres (the plan units are not known)"])
    k = math.sqrt(area / (size[0] * size[1]))
    sides = sorted((size[0] * k, size[1] * k))
    return round(sides[0], 3), round(sides[1], 3)


def _check_floor(floor, index):
    here = f"floors/{index}"
    errors = []
    if not isinstance(floor, dict):
        return [f"{here}: must be an object"]
    unknown = sorted(set(floor) - {"id", "name", "phases", "length", "architecture", "rooms", "by_name", "exclude", "receptacles_load", "circuits", "board"})
    errors += [f"{here}: unknown key(s) {', '.join(unknown)}"] if unknown else []
    for key in ("id", "name"):
        if not isinstance(floor.get(key), str) or not floor.get(key):
            errors.append(f"{here}/{key}: required text")
    if floor.get("phases") not in (1, 3) or isinstance(floor.get("phases"), bool):
        errors.append(f"{here}/phases: required, 1 or 3 (no default)")
    length = floor.get("length")
    if not (isinstance(length, dict) and _is_num(length.get("value")) and length["value"] > 0 and length.get("unit") == "m"):
        errors.append(f"{here}/length: required, {{value > 0, unit m}} (the run from the board; no default)")
    if not isinstance(floor.get("architecture"), dict) or not isinstance(floor["architecture"].get("rooms"), list):
        errors.append(f"{here}/architecture: required, the epc_arch result with its `rooms`")
    errors += _check_receptacles_load(floor, here)
    board = floor.get("board")
    if board is not None and not (isinstance(board, dict) and set(board) == {"x_m", "y_m"} and all(_is_num(v) for v in board.values())):
        errors.append(f"{here}/board: {{x_m, y_m}}, the place of the floor board on the plan in metres")
    if not isinstance(floor.get("circuits", {}), dict) or not set(floor.get("circuits", {})) <= {"lighting", "receptacles"}:
        errors.append(f"{here}/circuits: an object with `lighting` and/or `receptacles`")
    for key in ("rooms", "by_name"):
        if not isinstance(floor.get(key, {}), dict):
            errors.append(f"{here}/{key}: must be an object")
    if not isinstance(floor.get("exclude", []), list):
        errors.append(f"{here}/exclude: must be a list of room ids")
    return errors


def _check_receptacles_load(floor, here):
    spec = floor.get("receptacles_load")
    if spec is None:
        return []
    length = spec.get("length") if isinstance(spec, dict) else None
    if not (isinstance(spec, dict) and spec.get("phases") in (1, 3) and not isinstance(spec.get("phases"), bool)
            and isinstance(length, dict) and _is_num(length.get("value")) and length["value"] > 0 and length.get("unit") == "m"):
        return [f"{here}/receptacles_load: {{phases 1|3, length {{value > 0, unit m}}}} (no default)"]
    return []


def _room_data(floor, room):
    """The caller's data for a recognised room (by id, else by written name), or None."""
    data = (floor.get("rooms") or {}).get(room["id"])
    return data if data is not None else (floor.get("by_name") or {}).get(room.get("name"))


def _split(floor, room, with_outlets):
    """(lighting data, outlet data, errors) of a recognised room; `data` is None when the caller gave none."""
    data = _room_data(floor, room)
    where = f"floor {floor['id']}: room {room['id']} ({room.get('name') or 'no name'})"
    if not isinstance(data, dict):
        return None, None, [f"{where} has no lighting data: describe it or exclude it"]
    data = dict(data)
    outlets = data.pop("receptacles", None)
    clash = sorted(set(data) & set(SIZE_FIELDS))
    if clash:
        return None, None, [f"{where}: {', '.join(clash)} come from the architecture, not from the data"]
    if with_outlets and not (outlets is False or isinstance(outlets, dict)):
        return None, None, [f"{where}: `receptacles` must be the receptacle data, or false when the room has none"]
    if outlets is not None and not with_outlets:
        return None, None, [f"{where}: `receptacles` given but building.receptacles (the catalogue) is not"]
    return data, outlets, []


def _floor_rooms(floor, with_outlets):
    """(lighting rooms, receptacle rooms, errors) of the floor: one room per recognised room that is not excluded."""
    rooms, outlet_rooms, errors, excluded = [], [], [], set(floor.get("exclude") or [])
    found = floor["architecture"]["rooms"]
    unknown = sorted(excluded - {r["id"] for r in found}) + sorted(set(floor.get("rooms") or {}) - {r["id"] for r in found})
    errors += [f"floor {floor['id']}: room id {i} is not in the recognised architecture" for i in unknown]
    for room in found:
        if room["id"] not in excluded:
            lit, plug, errs = _one_room(floor, room, with_outlets)
            errors += errs
            rooms += [lit] if lit else []
            outlet_rooms += [plug] if plug else []
    return rooms, outlet_rooms, errors


def _one_room(floor, room, with_outlets):
    """(lighting room, receptacle room or None, errors) of one recognised room; the rooms are None when it has errors."""
    data, outlets, errs = _split(floor, room, with_outlets)
    if errs:
        return None, None, errs
    try:
        width, length = _shape(floor, room)
    except BuildingError as exc:
        return None, None, exc.errors
    base = {"id": f"{floor['id']}-{room['id']}", "name": f"{floor['name']} {room.get('name') or room['id']}", "width_m": width, "length_m": length}
    return {**base, **copy.deepcopy(data)}, ({**base, **copy.deepcopy(outlets)} if outlets else None), []


def _shape_errors(building):
    """Errors of the keys of the building outside the floors: unknown keys, luminaires, receptacle catalogue."""
    errors = []
    unknown = sorted(set(building) - {"luminaires", "options", "tolerance_pct", "floors", "receptacles"})
    errors += [f"building: unknown key(s) {', '.join(unknown)}"] if unknown else []
    if not isinstance(building.get("luminaires"), list) or not building["luminaires"]:
        errors.append("building/luminaires: required, the epc_lighting luminaires")
    if building.get("receptacles") is not None and not (isinstance(building["receptacles"], list) and building["receptacles"]):
        errors.append("building/receptacles: the epc_receptacles catalogue (a non-empty list)")
    return errors


def _floors_errors(building, loads):
    """Errors of the tolerance and of the floors: each floor, repeated ids, derived loads that already exist in the load list."""
    errors = []
    tol = building.get("tolerance_pct")
    if tol is not None and (not _is_num(tol) or tol < 0):
        errors.append("building/tolerance_pct: a number >= 0 (no default)")
    for i, floor in enumerate(building["floors"]):
        errors += _check_floor(floor, i)
    return errors + _id_errors([f.get("id") for f in building["floors"] if isinstance(f, dict)], loads)


def _id_errors(ids, loads):
    """Repeated floor ids and derived loads (`L-<floor>`, `T-<floor>`) that already exist in the load list."""
    have = {load["id"] for load in loads["loads"]}
    errors = [f"building/floors: id {d} is repeated" for d in sorted({i for i in ids if ids.count(i) > 1})]
    return errors + [f"load {p}-{i} already exists in the load list: it is derived from the floor {i}" for i in ids for p in "LT" if f"{p}-{i}" in have]


def _check(building, loads):
    if not isinstance(building, dict):
        return ["building must be an object"]
    errors = _shape_errors(building)
    if not isinstance(building.get("floors"), list) or not building["floors"]:
        return errors + ["building/floors: required, at least one floor"]
    return errors + _floors_errors(building, loads)


def _run(engine, document, options=None):
    import importlib
    module = importlib.import_module(engine)
    try:
        args = (copy.deepcopy(document),) + ((module.Options(**options),) if options is not None else ())
        return module.run(*args).as_dict()
    except (getattr(module, "LightingError", ValueError), getattr(module, "ReceptaclesError", ValueError), TypeError) as exc:   # TypeError: an option the engine does not have
        raise BuildingError([f"{engine}: {exc}"]) from exc


def _floors(building):
    """({floor id: [lit room ids]}, lighting rooms, {floor id: receptacle rooms}); raises with every error found."""
    with_outlets = bool(building.get("receptacles"))
    lit, rooms, outlets, errors = {}, [], {}, []
    for floor in building["floors"]:
        found, plugs, errs = _floor_rooms(floor, with_outlets)
        errors += errs
        lit[floor["id"]], outlets[floor["id"]] = [r["id"] for r in found], plugs
        rooms += found
        if plugs and not floor.get("receptacles_load"):
            errors.append(f"floor {floor['id']}: `receptacles_load` (phases and length of the receptacle load) is required")
    errors += [f"floor {i}: no room is lit" for i, ids in lit.items() if not ids] if not errors else []
    if errors:
        raise BuildingError(errors)
    return lit, rooms, outlets


def _lighting_loads(building, lit, out, lengths, result, document):
    """Adds the `L-<floor>` loads (power: installed power of the engine) to `out`; returns the `lighting` section of stage 3."""
    installed = {r["id"]: r["energy"]["installed_power_w"] for r in result["rooms"]}
    for floor in building["floors"]:
        watts = sum(installed[i] for i in lit[floor["id"]])
        if not watts or watts <= 0:
            raise BuildingError([f"floor {floor['id']}: the lighting calculation gives no installed power"])
        out["loads"].append({"id": f"L-{floor['id']}", "description": f"Lighting {floor['name']}", "area": floor["id"], "kind": "lighting",
                             "power": {"value": watts, "unit": "W"}, "phases": floor["phases"], "length": lengths[floor["id"]]("lighting")})
    section = {"document": document}
    if building.get("options"):
        section["options"] = copy.deepcopy(building["options"])
    if building.get("tolerance_pct") is not None:
        section["loads"] = {f"L-{i}": ids for i, ids in lit.items()}
        section["tolerance_pct"] = building["tolerance_pct"]
    return section


def _receptacle_loads(building, outlets, out, lengths, result):
    """Adds the `T-<floor>` loads (VA: the load of the engine for the rooms of the floor) to `out`."""
    if result is None:
        return
    va = {r["id"]: r["load_va"] for r in result["rooms"]}
    for floor in building["floors"]:
        plugs = outlets[floor["id"]]
        if not plugs:
            continue
        spec = floor["receptacles_load"]
        out["loads"].append({"id": f"T-{floor['id']}", "description": f"Receptacles {floor['name']}", "area": floor["id"], "kind": "receptacles",
                             "power": {"value": sum(va[r["id"]] for r in plugs), "unit": "VA"}, "phases": spec["phases"], "length": lengths[floor["id"]]("receptacles", spec["length"])})


def _route_floor(floor, building, mine, lighting, plug_result):
    """The design of one floor with a `board` (see routing.py) for its lit rooms `mine`."""
    arch = {r["id"]: r for r in floor["architecture"]["rooms"]}
    boxes = {r["id"]: arch[r["id"].split("-", 1)[1]].get("box_m") for r in mine}
    if not all(boxes.values()):
        raise BuildingError([f"floor {floor['id']}: a room has no position in metres (`box_m`): the plan units are not known"])
    plugs = {"rooms": [x for x in (plug_result or {"rooms": []})["rooms"] if x["id"] in boxes]} if plug_result else None
    return design_floor(floor, mine, boxes, {"rooms": [x for x in lighting["rooms"] if x["id"] in boxes]}, plugs, building.get("receptacles"))


def _routed_length(design):
    riser = design["riser_m"]
    return lambda part, own=None: {"value": round(riser + design["branch_m"][part], 3), "unit": "m"}


def _own_length(floor):
    return lambda part, own=None: copy.deepcopy(own or floor["length"])


def _routing(building, lit_rooms, rooms, lighting, outlets, plug_result):
    """{floor id: design of the floor} for the floors that have a `board` (see routing.py), and the function that gives the length of each derived load."""
    by_id = {r["id"]: r for r in rooms}
    designs, lengths = {}, {}
    for floor in building["floors"]:
        fid = floor["id"]
        if not floor.get("board"):
            lengths[fid] = _own_length(floor)
            continue
        designs[fid] = _route_floor(floor, building, [by_id[i] for i in lit_rooms[fid]], lighting, plug_result)
        lengths[fid] = _routed_length(designs[fid])
    return designs, lengths


def derive_all(building, loads):
    """{"loads": load list with the derived loads, "lighting": section for stage 3, "routing": {floor id: design}} (the last only for floors with a `board`). The inputs are not changed."""
    errors = _check(building, loads)
    if errors:
        raise BuildingError(errors)
    lit, rooms, outlets = _floors(building)
    out = copy.deepcopy(loads)
    known = {a["id"] for a in out["areas"]}
    out["areas"] += [{"id": f["id"], "name": f["name"]} for f in building["floors"] if f["id"] not in known]
    document = {"schema_version": "1.0", "luminaires": copy.deepcopy(building["luminaires"]), "rooms": rooms}
    lighting = _run("epc_lighting", document, building.get("options") or {})
    plug_result = _run("epc_receptacles", {"schema_version": "1.0", "receptacles": copy.deepcopy(building["receptacles"]), "rooms": [r for p in outlets.values() for r in p]}) if any(outlets.values()) else None
    try:
        designs, lengths = _routing(building, lit, rooms, lighting, outlets, plug_result)
    except RoutingError as exc:
        raise BuildingError(exc.errors) from exc
    section = _lighting_loads(building, lit, out, lengths, lighting, document)
    _receptacle_loads(building, outlets, out, lengths, plug_result)
    return {"loads": out, "lighting": section, "routing": designs}


def derive(building, loads):
    """(loads with the derived loads added, `lighting` section for stage 3)."""
    done = derive_all(building, loads)
    return done["loads"], done["lighting"]


def circuit_options(building, loads):
    """{load id: options} of the derived loads, from each floor's `circuits`; they go into `engine_inputs.circuits`."""
    ids = {x["id"] for x in loads["loads"]}
    options = {}
    for floor in building["floors"]:
        for part, prefix in (("lighting", "L"), ("receptacles", "T")):
            if part in (floor.get("circuits") or {}) and f"{prefix}-{floor['id']}" in ids:
                options[f"{prefix}-{floor['id']}"] = copy.deepcopy(floor["circuits"][part])
    return options
