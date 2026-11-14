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

`derive` returns the load list with one `L-<floor id>` load per floor and the `lighting` section for stage 3 (document, options, load map).
"""
import copy
import math

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
    unknown = sorted(set(floor) - {"id", "name", "phases", "length", "architecture", "rooms", "by_name", "exclude"})
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
    for key in ("rooms", "by_name"):
        if not isinstance(floor.get(key, {}), dict):
            errors.append(f"{here}/{key}: must be an object")
    if not isinstance(floor.get("exclude", []), list):
        errors.append(f"{here}/exclude: must be a list of room ids")
    return errors


def _room_data(floor, room):
    """The caller's data for a recognised room (by id, else by written name), or None."""
    data = (floor.get("rooms") or {}).get(room["id"])
    return data if data is not None else (floor.get("by_name") or {}).get(room.get("name"))


def _floor_rooms(floor):
    """(document rooms of the floor, errors): one room per recognised room that is not excluded."""
    rooms, errors, excluded = [], [], set(floor.get("exclude") or [])
    found = floor["architecture"]["rooms"]
    unknown = sorted(excluded - {r["id"] for r in found}) + sorted(set(floor.get("rooms") or {}) - {r["id"] for r in found})
    errors += [f"floor {floor['id']}: room id {i} is not in the recognised architecture" for i in unknown]
    for room in found:
        if room["id"] in excluded:
            continue
        data = _room_data(floor, room)
        if data is None or not isinstance(data, dict):
            errors.append(f"floor {floor['id']}: room {room['id']} ({room.get('name') or 'no name'}) has no lighting data: describe it or exclude it")
            continue
        clash = sorted(set(data) & set(SIZE_FIELDS))
        if clash:
            errors.append(f"floor {floor['id']}: room {room['id']}: {', '.join(clash)} come from the architecture, not from the data")
            continue
        try:
            width, length = _shape(floor, room)
        except BuildingError as exc:
            errors += exc.errors
            continue
        label = room.get("name") or room["id"]
        rooms.append({"id": f"{floor['id']}-{room['id']}", "name": f"{floor['name']} {label}", "width_m": width, "length_m": length, **copy.deepcopy(data)})
    return rooms, errors


def _check(building, loads):
    if not isinstance(building, dict):
        return ["building must be an object"]
    errors = []
    unknown = sorted(set(building) - {"luminaires", "options", "tolerance_pct", "floors"})
    errors += [f"building: unknown key(s) {', '.join(unknown)}"] if unknown else []
    if not isinstance(building.get("luminaires"), list) or not building["luminaires"]:
        errors.append("building/luminaires: required, the epc_lighting luminaires")
    if not isinstance(building.get("floors"), list) or not building["floors"]:
        errors.append("building/floors: required, at least one floor")
        return errors
    tol = building.get("tolerance_pct")
    if tol is not None and (not _is_num(tol) or tol < 0):
        errors.append("building/tolerance_pct: a number >= 0 (no default)")
    for i, floor in enumerate(building["floors"]):
        errors += _check_floor(floor, i)
    ids = [f.get("id") for f in building["floors"] if isinstance(f, dict)]
    errors += [f"building/floors: id {d} is repeated" for d in sorted({i for i in ids if ids.count(i) > 1})]
    have = {load["id"] for load in loads["loads"]}
    errors += [f"load {f'L-{i}'} already exists in the load list: it is derived from the floor {i}" for i in ids if f"L-{i}" in have]
    return errors


def _lighting_run(document, options):
    import epc_lighting
    try:
        return epc_lighting.run(copy.deepcopy(document), epc_lighting.Options(**(options or {}))).as_dict()
    except (epc_lighting.LightingError, TypeError) as exc:
        raise BuildingError([str(exc)]) from exc


def derive(building, loads):
    """(loads with the lighting loads added, `lighting` section for stage 3). The inputs are not changed."""
    errors = _check(building, loads)
    if errors:
        raise BuildingError(errors)
    rooms, floors_rooms = [], {}
    for floor in building["floors"]:
        found, errs = _floor_rooms(floor)
        errors += errs
        floors_rooms[floor["id"]] = [r["id"] for r in found]
        rooms += found
    empty = [i for i, ids in floors_rooms.items() if not ids]
    errors += [f"floor {i}: no room is lit" for i in empty] if not errors else []
    if errors:
        raise BuildingError(errors)
    document = {"schema_version": "1.0", "luminaires": copy.deepcopy(building["luminaires"]), "rooms": rooms}
    result = _lighting_run(document, building.get("options"))
    installed = {r["id"]: r["energy"]["installed_power_w"] for r in result["rooms"]}
    out = copy.deepcopy(loads)
    known = {a["id"] for a in out["areas"]}
    for floor in building["floors"]:
        if floor["id"] not in known:
            out["areas"].append({"id": floor["id"], "name": floor["name"]})
        watts = sum(installed[i] for i in floors_rooms[floor["id"]])
        if not watts or watts <= 0:
            raise BuildingError([f"floor {floor['id']}: the lighting calculation gives no installed power"])
        out["loads"].append({"id": f"L-{floor['id']}", "description": f"Lighting {floor['name']}", "area": floor["id"], "kind": "lighting",
                             "power": {"value": watts, "unit": "W"}, "phases": floor["phases"], "length": copy.deepcopy(floor["length"])})
    section = {"document": document}
    if building.get("options"):
        section["options"] = copy.deepcopy(building["options"])
    if building.get("tolerance_pct") is not None:
        section["loads"] = {f"L-{i}": ids for i, ids in floors_rooms.items()}
        section["tolerance_pct"] = building["tolerance_pct"]
    return out, section
