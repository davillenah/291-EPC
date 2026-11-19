"""Runs and wiring of a floor: the luminaires and outlets the engines placed, the board, and `epc_plan.design` (ADR-0026) that lays the trays and conduits and routes the circuits.

The discipline draws nothing and measures nothing: the positions come from `epc_lighting` and `epc_receptacles` (in the frame of each room), the rooms from the recognised
architecture (`box_m`), the board from the caller (`board`: its place on the plan, an input), and the runs, the circuits and their lengths from `epc_plan`.
Every branch circuit the engine proposes (IUG-xx, TUG-xx) becomes a load of its own. Its length is the run from the main board to the board of the floor (an input) plus the length
the plan engine gives for the voltage drop by electrical moments (`moment_length_m`: the length equivalent to the sum of current x distance of its loads), and the circuit is sized
with the moments flag of the calculation engine. A circuit the runs do not reach is an error: its length would be wrong.

The run from the main board to the board of a floor (the riser) is an input (`length` of the floor) or, when the building gives its `main_board`, it is routed too: `route_riser` lays the horizontal runs
on the main floor and on the floor of the board, joined by a plenum (a vertical shaft) as high as the difference of the levels of both floors, and the plan engine measures it (the height of the plenum is added to the
route). Levels (`elevation_m`) and the place of each shaft are inputs.

The plan is drawn in metres (scale 1 unit = 1 m) in the frame of the architecture, which the floors share.
"""
import copy

from disciplines.electrical_lv import lux_map

KINDS = {"general": "TG", "special": "TE"}                # kind of receptacle (epc_receptacles) -> node kind of the plan profile
FAMILIES = {"IUG": "lighting", "IUE": "lighting", "TUG": "receptacles", "TUE": "receptacles"}
SCALE = {"p1": [0, 0], "p2": [1, 0], "distance_m": 1}
BOARD_ID = "TB-01"
UNITS = {"lighting": "W", "receptacles": "VA"}
LOAD_PREFIX = {"lighting": "L", "receptacles": "T"}


class RoutingError(ValueError):
    """The floor cannot be routed; `errors` lists the reasons."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = list(errors)


def to_plan(box, room, x, y):
    """Plan coordinates of a point given in the frame of a room of the document (x along `length_m`, y along `width_m`): the room is laid in its box with its long side along the long side of the box."""
    w, h = box[2] - box[0], box[3] - box[1]
    if w >= h:
        return round(box[0] + x * w / room["length_m"], 4), round(box[1] + y * h / room["width_m"], 4)
    return round(box[0] + y * w / room["width_m"], 4), round(box[1] + x * h / room["length_m"], 4)


def _nodes(rooms, boxes, lighting, outlets, kinds):
    """The load nodes of the plan: a luminaire per position of the lighting result and an outlet per position of the receptacles result."""
    nodes = []
    by_id = {r["id"]: r for r in rooms}
    for item in lighting["rooms"]:
        room, per = by_id[item["id"]], item["energy"]["installed_power_w"] / max(item["layout"]["installed"], 1)
        for p in item["layout"]["positions"]:
            x, y = to_plan(boxes[item["id"]], room, p["x_m"], p["y_m"])
            nodes.append({"id": p["tag"], "kind": "LU", "x": x, "y": y, "attrs": {"lighting": {"power_w": per}}})
    for item in (outlets or {"rooms": []})["rooms"]:
        room = by_id[item["id"]]
        for p in item["layout"]["positions"]:
            x, y = to_plan(boxes[item["id"]], room, p["x_m"], p["y_m"])
            nodes.append({"id": f"{item['id']}.{p['tag']}", "kind": KINDS[kinds[item["receptacle"]]], "x": x, "y": y, "attrs": {"receptacles": {"power_va": item["power_va_each"]}}})
    return nodes


def _room_polygons(boxes):
    return [{"id": rid, "name": rid, "points": [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]]} for rid, b in boxes.items()]


def backdrop_of(architecture):
    """The walls, the room names and the openings of a recognised floor in metres, for the DXF under the services and the 3D model (the plan units divided by the units per metre the architecture reports)."""
    k = architecture.get("units_per_metre")
    if not k:
        return None
    walls = [{"a": [w["a"][0] / k, w["a"][1] / k], "b": [w["b"][0] / k, w["b"][1] / k], "thickness_m": w["thickness"] / k} for w in architecture.get("walls", [])]
    rooms = [{"name": r["name"], "at": [(r["box_m"][0] + r["box_m"][2]) / 2, (r["box_m"][1] + r["box_m"][3]) / 2]} for r in architecture.get("rooms", []) if r.get("name") and r.get("box_m")]
    openings = [{"kind": o["kind"], "at": [o["at"][0] / k, o["at"][1] / k], "width_m": o["width"] / k, "angle": o["angle"]} for o in architecture.get("openings", [])]
    return {"walls": walls, "rooms": rooms, "openings": openings}


def _propose(design, document, floor, boxes, taken):
    """(runs, wiring) the plan engine proposes for the floor document; adds the runs to the document as lines. `taken`: the circuit tags of the floors before (the tags are unique in the building)."""
    try:
        runs = design.propose_runs(document)
        document["lines"] = [{"id": f"RUN-{i:03d}", "kind": r["kind"], "points": r["points"]} for i, r in enumerate(runs["lines"], 1)]
        return runs, design.propose_wiring(document, _room_polygons(boxes), {"taken": sorted(taken)})
    except ValueError as exc:
        raise RoutingError([f"floor {floor['id']}: {exc}"]) from exc


def _refuse_unrouted(floor, wiring):
    """A circuit whose runs do not reach its loads, or a load outside every room, stops the floor."""
    lost = [f"floor {floor['id']}: circuit {t}: the runs do not reach {', '.join(r['unreached'][:6]) or 'all its loads'}" for t, r in wiring["routes"].items() if not r["found"]]
    if lost or wiring["unassigned"]:
        raise RoutingError(lost + [f"floor {floor['id']}: {w}" for w in wiring["warnings"] if "outside every room" in w])


def _circuits(wiring):
    """{circuit tag: its data as a load}: family and part of the installation, room, power (W for lighting, VA for receptacles), the load id and the length the engine gives for the moments."""
    out = {}
    for c in wiring["circuits"]:
        part = FAMILIES[c["family"]]
        out[c["tag"]] = {"family": c["family"], "part": part, "room": c["room"], "outlets": c["outlets"], "power": c["va"], "unit": UNITS[part], "load": f"{LOAD_PREFIX[part]}-{c['tag']}",
                         "moment_m": wiring["routes"][c["tag"]]["moment_length_m"], "max_m": wiring["routes"][c["tag"]]["max_distance_m"]}
    return out


def _risers(floor):
    """{part: run in metres from the main board to the board of the floor}: lighting by the `length` of the floor, receptacles by that of `receptacles_load` (else the same)."""
    given = (floor.get("receptacles_load") or {}).get("length") or floor["length"]
    return {"lighting": floor["length"]["value"], "receptacles": given["value"]}


def design_floor(floor, rooms, boxes, lighting, outlets, catalogue, taken=()):
    """{document, runs, wiring, circuits, riser_m, backdrop, warnings} of one floor. `rooms`: the lit rooms of the document (the lighting and receptacle results are keyed by their ids); `boxes`: room id -> box in metres."""
    import epc_plan.design as design
    board = floor["board"]
    kinds = {r["id"]: r["kind"] for r in catalogue or []}
    document = {"schema_version": "1.0", "plan": {"id": floor["id"], "scale": copy.deepcopy(SCALE)}, "discipline": "electrica_BT",
                "nodes": [{"id": BOARD_ID, "kind": "TB", "x": board["x_m"], "y": board["y_m"]}] + _nodes(rooms, boxes, lighting, outlets, kinds)}
    runs, wiring = _propose(design, document, floor, boxes, taken)
    _refuse_unrouted(floor, wiring)
    return {"document": document, "runs": runs, "wiring": wiring, "circuits": _circuits(wiring), "riser_m": _risers(floor), "backdrop": backdrop_of(floor["architecture"]),
            "luxmap": lux_map.floor_map(lighting["rooms"], boxes, {r["id"]: r for r in rooms}, to_plan), "warnings": [f"floor {floor['id']}: {w}" for w in runs["warnings"] + wiring["warnings"]]}


def _corner(points):
    """The points of an orthogonal run (horizontal first) without repeated points."""
    out = [points[0]]
    for p in points[1:]:
        if p != out[-1]:
            out.append(p)
    return out


def _riser_document(main, floor, height):
    """The plan document of the riser: the main board, the board of the floor and, when they are not on the same floor, the shaft (a plenum of the height of the levels) between them. A board that
    stands at the shaft is the shaft: two nodes at one point would be one node of the graph and the plenum would be lost."""
    board, here = floor["board"], main["floor"] == floor["id"]
    start, end = (main["x_m"], main["y_m"]), (board["x_m"], board["y_m"])
    shaft = None if here else (floor["shaft"]["x_m"], floor["shaft"]["y_m"])
    ids = {"from": "TB-MAIN" if shaft != start else "PL-SHAFT", "to": BOARD_ID if shaft != end else "PL-SHAFT"}
    nodes = ([] if ids["from"] == "PL-SHAFT" else [{"id": "TB-MAIN", "kind": "TB", "x": start[0], "y": start[1]}]) + ([] if ids["to"] == "PL-SHAFT" else [{"id": BOARD_ID, "kind": "TB", "x": end[0], "y": end[1]}])
    if shaft is None:
        runs = [[start, (end[0], start[1]), end]]
    else:
        nodes.append({"id": "PL-SHAFT", "kind": "PL", "x": shaft[0], "y": shaft[1], "attrs": {"altura_m": height}})
        runs = [[start, (shaft[0], start[1]), shaft], [shaft, (shaft[0], end[1]), end]]
    lines = [{"id": f"RISER-{i}", "kind": "BN", "points": [list(p) for p in _corner(r)]} for i, r in enumerate(runs, 1) if len(_corner(r)) > 1]
    return {"schema_version": "1.0", "plan": {"id": f"riser-{floor['id']}", "scale": copy.deepcopy(SCALE)}, "discipline": "electrica_BT", "nodes": nodes, "lines": lines,
            "circuits": [{"tag": "RISER", "from": ids["from"], "to": ids["to"], "via": [], "ternas": 1}]}


def route_riser(main, floor, height):
    """{"length_m", "height_m", "document"}: the run from the main board to the board of `floor`, measured by the plan engine (the height of the shaft included)."""
    import epc_plan.core as core
    if height == 0 and main["floor"] == floor["id"] and (main["x_m"], main["y_m"]) == (floor["board"]["x_m"], floor["board"]["y_m"]):
        return {"length_m": 0.0, "height_m": 0.0, "document": None}            # the board of the floor is the main board: there is no run
    document = _riser_document(main, floor, height)
    if document["circuits"][0]["from"] == document["circuits"][0]["to"]:
        return {"length_m": height, "height_m": height, "document": document}   # both boards stand at the shaft: the run is the shaft itself
    try:
        route = core.process(document)["circuits"]["RISER"]
    except (core.PlanError, KeyError) as exc:
        raise RoutingError([f"floor {floor['id']}: the riser cannot be routed: {exc}"]) from exc
    if not route["found"]:
        raise RoutingError([f"floor {floor['id']}: the riser does not reach the board of the floor (check the shaft and the board positions)"])
    return {"length_m": route["length_m"], "height_m": height, "document": document}
