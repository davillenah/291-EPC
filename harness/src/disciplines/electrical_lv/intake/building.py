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
                 "architecture": {...},                    # `epc_arch` result as a dict (rooms with `area_m2` and `size_m`), or
                 "plan": "plans/PB.dxf",                   # the plan of the floor in `inputs/`: the pipeline recognises it with `epc_arch` (see `resolve_plans`)
                 "rooms": {"r1": {...}},                   # per recognised room id: the epc_lighting room fields except id, name and size
                 "by_name": {"HALL": {...}},               # the same, by the written name of the room (exact match); `rooms` wins
                 "exclude": ["r7"],                        # room ids that are deliberately not lit
                 "emergency": {"r2": {...}}}],             # antipanic emergency lighting of a room: the epc_lighting emergency fields except id, name, width_m, length_m
     "exterior": [{"id": "EXT1", "area_m2": 300, "luminaire": "...", "load": {"area": "AZ", "phases": 1, "length": {...}}}]}   # exterior areas: epc_lighting area fields + the load they make

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


FLOOR_KEYS = {"id", "name", "phases", "length", "architecture", "plan", "rooms", "by_name", "exclude", "receptacles_load", "circuits", "board", "emergency"}


def _is_length(value):
    """A length as the load list writes it: {value > 0, unit m}."""
    return isinstance(value, dict) and _is_num(value.get("value")) and value["value"] > 0 and value.get("unit") == "m"


def _is_board(value):
    return isinstance(value, dict) and set(value) == {"x_m", "y_m"} and all(_is_num(v) for v in value.values())


def _check_floor_basics(floor, here):
    """Errors of the identity, the phases, the run from the main board and the architecture of a floor."""
    errors = [f"{here}/{key}: required text" for key in ("id", "name") if not isinstance(floor.get(key), str) or not floor.get(key)]
    if floor.get("phases") not in (1, 3) or isinstance(floor.get("phases"), bool):
        errors.append(f"{here}/phases: required, 1 or 3 (no default)")
    if not _is_length(floor.get("length")):
        errors.append(f"{here}/length: required, {{value > 0, unit m}} (the run from the board; no default)")
    if not isinstance(floor.get("architecture"), dict) or not isinstance(floor["architecture"].get("rooms"), list):
        errors.append(f"{here}/architecture: required, the epc_arch result with its `rooms`")
    return errors


def _check_floor_options(floor, here):
    """Errors of the board, the circuit options and the room data of a floor."""
    errors = _check_receptacles_load(floor, here)
    if floor.get("board") is not None and not _is_board(floor["board"]):
        errors.append(f"{here}/board: {{x_m, y_m}}, the place of the floor board on the plan in metres")
    if not isinstance(floor.get("circuits", {}), dict) or not set(floor.get("circuits", {})) <= {"lighting", "receptacles"}:
        errors.append(f"{here}/circuits: an object with `lighting` and/or `receptacles`")
    return errors + _check_room_keys(floor, here)


def _check_room_keys(floor, here):
    """Errors of the keys that describe the rooms: `rooms` and `by_name` are objects, `exclude` a list of room ids."""
    errors = [f"{here}/{key}: must be an object" for key in ("rooms", "by_name") if not isinstance(floor.get(key, {}), dict)]
    return errors + ([] if isinstance(floor.get("exclude", []), list) else [f"{here}/exclude: must be a list of room ids"])


def _check_floor(floor, index):
    here = f"floors/{index}"
    if not isinstance(floor, dict):
        return [f"{here}: must be an object"]
    unknown = sorted(set(floor) - FLOOR_KEYS)
    return ([f"{here}: unknown key(s) {', '.join(unknown)}"] if unknown else []) + _check_floor_basics(floor, here) + _check_floor_options(floor, here)


def _check_receptacles_load(floor, here):
    spec = floor.get("receptacles_load")
    if spec is None:
        return []
    if not (isinstance(spec, dict) and spec.get("phases") in (1, 3) and not isinstance(spec.get("phases"), bool) and _is_length(spec.get("length"))):
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
    unknown = sorted(set(building) - {"luminaires", "options", "tolerance_pct", "floors", "receptacles", "exterior"})
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


def _emergency_items(floor):
    """The antipanic emergency lighting of the rooms of a floor that ask for it: one item per room, sized like the room (see `_shape`), with the data the caller gives."""
    found = {r["id"]: r for r in floor["architecture"]["rooms"]}
    items, errors = [], []
    for rid, data in sorted((floor.get("emergency") or {}).items()):
        if rid not in found or not isinstance(data, dict):
            errors.append(f"floor {floor['id']}: emergency room {rid} is not in the recognised architecture or its data is not an object")
            continue
        try:
            width, length = _shape(floor, found[rid])
        except BuildingError as exc:
            errors += exc.errors
            continue
        items.append({"id": f"{floor['id']}-{rid}-EM", "name": f"{floor['name']} {found[rid].get('name') or rid} emergency", "width_m": width, "length_m": length, **copy.deepcopy(data)})
    return items, errors


def _exterior(building):
    """(exterior areas for the lighting document, {area id: load spec}, errors): the `load` of each area (area of the load list, phases, length) is not an epc_lighting field."""
    areas, specs, errors = [], {}, []
    for i, raw in enumerate(building.get("exterior") or []):
        spec = raw.get("load") if isinstance(raw, dict) else None
        if not (isinstance(spec, dict) and isinstance(spec.get("area"), str) and spec.get("phases") in (1, 3) and _is_length(spec.get("length"))):
            errors.append(f"building/exterior/{i}: `load` is required: {{area, phases 1|3, length {{value > 0, unit m}}}} (no default)")
            continue
        areas.append({k: v for k, v in raw.items() if k != "load"})
        specs[raw.get("id")] = spec
    return areas, specs, errors


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


def _lighting_section(building, lit, lengths, document):
    """The `lighting` section of stage 3: the document, the options and, with a tolerance, the loads by floor to compare (the circuits of a routed floor come from the same rooms, so only floors without a board)."""
    section = {"document": document}
    if building.get("options"):
        section["options"] = copy.deepcopy(building["options"])
    floor_loads = {f"L-{i}": ids for i, ids in lit.items() if i in lengths}
    if building.get("tolerance_pct") is not None and floor_loads:
        section["loads"], section["tolerance_pct"] = floor_loads, building["tolerance_pct"]
    return section


def _lighting_loads(building, lit, out, lengths, result, document):
    """Adds the `L-<floor>` loads (power: installed power of the engine) to `out`; returns the `lighting` section of stage 3."""
    installed = {r["id"]: r["energy"]["installed_power_w"] for r in result["rooms"]}
    for floor in [f for f in building["floors"] if f["id"] in lengths]:           # a floor with a board has one load per branch circuit (see `_circuit_loads`)
        watts = sum(installed[i] for i in lit[floor["id"]])
        if not watts or watts <= 0:
            raise BuildingError([f"floor {floor['id']}: the lighting calculation gives no installed power"])
        out["loads"].append({"id": f"L-{floor['id']}", "description": f"Lighting {floor['name']}", "area": floor["id"], "kind": "lighting",
                             "power": {"value": watts, "unit": "W"}, "phases": floor["phases"], "length": lengths[floor["id"]]("lighting")})
    return _lighting_section(building, lit, lengths, document)


def _receptacle_loads(building, outlets, out, lengths, result):
    """Adds the `T-<floor>` loads (VA: the load of the engine for the rooms of the floor) to `out`."""
    if result is None:
        return
    va = {r["id"]: r["load_va"] for r in result["rooms"]}
    for floor in building["floors"]:
        plugs = outlets[floor["id"]]
        if not plugs or floor["id"] not in lengths:
            continue
        spec = floor["receptacles_load"]
        out["loads"].append({"id": f"T-{floor['id']}", "description": f"Receptacles {floor['name']}", "area": floor["id"], "kind": "receptacles",
                             "power": {"value": sum(va[r["id"]] for r in plugs), "unit": "VA"}, "phases": spec["phases"], "length": lengths[floor["id"]]("receptacles", spec["length"])})


def _route_floor(floor, building, mine, lighting, plug_result, taken):
    """The design of one floor with a `board` (see routing.py) for its lit rooms `mine`."""
    arch = {r["id"]: r for r in floor["architecture"]["rooms"]}
    boxes = {r["id"]: arch[r["id"].split("-", 1)[1]].get("box_m") for r in mine}
    if not all(boxes.values()):
        raise BuildingError([f"floor {floor['id']}: a room has no position in metres (`box_m`): the plan units are not known"])
    plugs = {"rooms": [x for x in (plug_result or {"rooms": []})["rooms"] if x["id"] in boxes]} if plug_result else None
    return design_floor(floor, mine, boxes, {"rooms": [x for x in lighting["rooms"] if x["id"] in boxes]}, plugs, building.get("receptacles"), taken)


def _own_length(floor):
    return lambda part, own=None: copy.deepcopy(own or floor["length"])


def _routing(building, lit_rooms, rooms, lighting, outlets, plug_result):
    """{floor id: design of the floor} for the floors that have a `board` (see routing.py), and the function that gives the length of each derived load."""
    by_id = {r["id"]: r for r in rooms}
    designs, lengths, taken = {}, {}, set()
    for floor in building["floors"]:
        fid = floor["id"]
        if not floor.get("board"):
            lengths[fid] = _own_length(floor)
            continue
        designs[fid] = _route_floor(floor, building, [by_id[i] for i in lit_rooms[fid]], lighting, plug_result, taken)
        taken.update(designs[fid]["circuits"])
    return designs, lengths


def _circuit_loads(building, designs, out):
    """Adds one load per branch circuit of the routed floors: its power from the engines, its length riser + moment length (voltage drop by electrical moments), the phases of the floor."""
    for floor in building["floors"]:
        design = designs.get(floor["id"])
        for tag, c in (design or {"circuits": {}})["circuits"].items():
            phases = floor["phases"] if c["part"] == "lighting" else floor["receptacles_load"]["phases"]
            label = "Lighting" if c["part"] == "lighting" else "Receptacles"
            out["loads"].append({"id": c["load"], "description": f"{label} {floor['name']} {tag}", "area": floor["id"], "kind": c["part"],
                                 "power": {"value": c["power"], "unit": c["unit"]}, "phases": phases, "length": {"value": round(design["riser_m"][c["part"]] + c["moment_m"], 3), "unit": "m"}})


def _circuit_options(building, designs):
    """{load id: options of the circuit}: what each floor says for its `circuits` and, for a branch circuit, the moments flag (its length is the one equivalent to the moments)."""
    options = {}
    for floor in building["floors"]:
        given = floor.get("circuits") or {}
        if floor["id"] in designs:
            for c in designs[floor["id"]]["circuits"].values():
                options[c["load"]] = {**copy.deepcopy(given.get(c["part"]) or {}), "moments": True}
        else:
            options.update({f"{p}-{floor['id']}": copy.deepcopy(given[part]) for part, p in (("lighting", "L"), ("receptacles", "T")) if part in given})
    return options


def _extra_lighting(building):
    """The emergency items of every floor and the exterior areas, as keys of the lighting document (raises with every error found)."""
    emergency, errors = [], []
    for floor in building["floors"]:
        items, errs = _emergency_items(floor)
        emergency, errors = emergency + items, errors + errs
    areas, _, area_errors = _exterior(building)
    if errors + area_errors:
        raise BuildingError(errors + area_errors)
    return {**({"emergency": emergency} if emergency else {}), **({"areas": areas} if areas else {})}


def _exterior_loads(building, lighting, out):
    """One lighting load per exterior area: the installed power of the engine and the area, phases and length the caller gave."""
    _, specs, _ = _exterior(building)
    known = {a["id"] for a in out["areas"]}
    for item in lighting.get("areas") or []:
        spec = specs[item["id"]]
        if spec["area"] not in known:
            raise BuildingError([f"exterior area {item['id']}: the area {spec['area']} of its load is not in the load list"])
        out["loads"].append({"id": f"L-{item['id']}", "description": f"Exterior lighting {item.get('name') or item['id']}", "area": spec["area"], "kind": "lighting",
                             "power": {"value": item["energy"]["installed_power_w"], "unit": "W"}, "phases": spec["phases"], "length": copy.deepcopy(spec["length"])})


def _recognise(plan, inputs_dir, floor_id):
    """The architecture of a plan file of `inputs/` as a dict (`epc_arch.recognize`); raises BuildingError when the path leaves `inputs/`, the file is missing or the engine cannot read it."""
    from pathlib import Path
    import epc_arch
    root = Path(inputs_dir).resolve()
    path = (root / plan).resolve()
    if root not in path.parents or not path.is_file():
        raise BuildingError([f"floor {floor_id}: the plan {plan!r} is not a file of the inputs folder"])
    try:
        return epc_arch.recognize(path.read_bytes(), path.name).architecture.as_dict()
    except epc_arch.ArchError as exc:
        raise BuildingError([f"floor {floor_id}: the plan {plan!r} cannot be read: {exc}"]) from exc


def resolve_plans(building, inputs_dir):
    """A copy of the building where every floor that names its `plan` (a file of `inputs/`) has its `architecture` recognised by `epc_arch`; a floor that gives both is an error."""
    out = copy.deepcopy(building)
    for floor in (out.get("floors") if isinstance(out, dict) and isinstance(out.get("floors"), list) else []):
        if not isinstance(floor, dict) or "plan" not in floor:
            continue
        if "architecture" in floor or not isinstance(floor["plan"], str):
            raise BuildingError([f"floor {floor.get('id')}: give `architecture` or `plan` (a file name of the inputs folder), not both"])
        floor["architecture"] = _recognise(floor.pop("plan"), inputs_dir, floor.get("id"))
    return out


def _receptacle_result(building, outlets):
    """The epc_receptacles result for the rooms that have outlets, or None when no room has any."""
    rooms = [r for plugs in outlets.values() for r in plugs]
    if not rooms:
        return None
    return _run("epc_receptacles", {"schema_version": "1.0", "receptacles": copy.deepcopy(building["receptacles"]), "rooms": rooms})


def derive_all(building, loads, inputs_dir=None):
    """{"loads": load list with the derived loads, "lighting": section for stage 3, "routing": {floor id: design} (floors with a `board`), "circuits": {load id: options}}. The inputs are not changed."""
    building = resolve_plans(building, inputs_dir) if inputs_dir is not None else building
    errors = _check(building, loads)
    if errors:
        raise BuildingError(errors)
    lit, rooms, outlets = _floors(building)
    out = copy.deepcopy(loads)
    known = {a["id"] for a in out["areas"]}
    out["areas"] += [{"id": f["id"], "name": f["name"]} for f in building["floors"] if f["id"] not in known]
    document = {"schema_version": "1.0", "luminaires": copy.deepcopy(building["luminaires"]), "rooms": rooms}
    document.update(_extra_lighting(building))
    lighting = _run("epc_lighting", document, building.get("options") or {})
    plug_result = _receptacle_result(building, outlets)
    try:
        designs, lengths = _routing(building, lit, rooms, lighting, outlets, plug_result)
    except RoutingError as exc:
        raise BuildingError(exc.errors) from exc
    section = _lighting_loads(building, lit, out, lengths, lighting, document)
    _receptacle_loads(building, outlets, out, lengths, plug_result)
    _circuit_loads(building, designs, out)
    _exterior_loads(building, lighting, out)
    return {"loads": out, "lighting": section, "routing": designs, "circuits": _circuit_options(building, designs)}


def derive(building, loads):
    """(loads with the derived loads added, `lighting` section for stage 3)."""
    done = derive_all(building, loads)
    return done["loads"], done["lighting"]
