"""Runs and wiring of a floor: the luminaires and outlets the engines placed, the board, and `epc_plan.design` (ADR-0026) that lays the trays and conduits and routes the circuits.

The discipline draws nothing and measures nothing: the positions come from `epc_lighting` and `epc_receptacles` (in the frame of each room), the rooms from the recognised
architecture (`box_m`), the board from the caller (`board`: its place on the plan, an input), and the runs, the circuits and their lengths from `epc_plan`.
The length of a derived load is the run from the main board to the board of the floor (`length` of the floor, an input) plus the longest route of the circuits of its family
(`max_distance_m` of the engine). A circuit the runs do not reach is an error: its length would be wrong.

The plan is drawn in metres (scale 1 unit = 1 m) in the frame of the architecture, which the floors share.
"""
import copy

KINDS = {"general": "TG", "special": "TE"}                # kind of receptacle (epc_receptacles) -> node kind of the plan profile
FAMILIES = {"IUG": "lighting", "IUE": "lighting", "TUG": "receptacles", "TUE": "receptacles"}
SCALE = {"p1": [0, 0], "p2": [1, 0], "distance_m": 1}
BOARD_ID = "TB-01"


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
    """The walls and room names of a recognised floor in metres, for the DXF under the services (the plan units divided by the units per metre the architecture reports)."""
    k = architecture.get("units_per_metre")
    if not k:
        return None
    walls = [{"a": [w["a"][0] / k, w["a"][1] / k], "b": [w["b"][0] / k, w["b"][1] / k], "thickness_m": w["thickness"] / k} for w in architecture.get("walls", [])]
    rooms = [{"name": r["name"], "at": [(r["box_m"][0] + r["box_m"][2]) / 2, (r["box_m"][1] + r["box_m"][3]) / 2]} for r in architecture.get("rooms", []) if r.get("name") and r.get("box_m")]
    return {"walls": walls, "rooms": rooms}


def _propose(design, document, floor, boxes):
    """(runs, wiring) the plan engine proposes for the floor document; adds the runs to the document as lines."""
    try:
        runs = design.propose_runs(document)
        document["lines"] = [{"id": f"RUN-{i:03d}", "kind": r["kind"], "points": r["points"]} for i, r in enumerate(runs["lines"], 1)]
        return runs, design.propose_wiring(document, _room_polygons(boxes))
    except ValueError as exc:
        raise RoutingError([f"floor {floor['id']}: {exc}"]) from exc


def _refuse_unrouted(floor, wiring):
    """A circuit whose runs do not reach its loads, or a load outside every room, stops the floor."""
    lost = [f"floor {floor['id']}: circuit {t}: the runs do not reach {', '.join(r['unreached'][:6]) or 'all its loads'}" for t, r in wiring["routes"].items() if not r["found"]]
    if lost or wiring["unassigned"]:
        raise RoutingError(lost + [f"floor {floor['id']}: {w}" for w in wiring["warnings"] if "outside every room" in w])


def _branch_lengths(wiring):
    """{part of the installation: longest branch distance in metres} over the circuits of each family."""
    branch = {}
    for c in wiring["circuits"]:
        part = FAMILIES[c["family"]]
        branch[part] = max(branch.get(part, 0.0), wiring["routes"][c["tag"]]["max_distance_m"])
    return branch


def design_floor(floor, rooms, boxes, lighting, outlets, catalogue):
    """{document, runs, wiring, branch_m, warnings} of one floor. `rooms`: the lit rooms of the document (the lighting and receptacle results are keyed by their ids); `boxes`: room id -> box in metres."""
    import epc_plan.design as design
    board = floor["board"]
    kinds = {r["id"]: r["kind"] for r in catalogue or []}
    document = {"schema_version": "1.0", "plan": {"id": floor["id"], "scale": copy.deepcopy(SCALE)}, "discipline": "electrica_BT",
                "nodes": [{"id": BOARD_ID, "kind": "TB", "x": board["x_m"], "y": board["y_m"]}] + _nodes(rooms, boxes, lighting, outlets, kinds)}
    runs, wiring = _propose(design, document, floor, boxes)
    _refuse_unrouted(floor, wiring)
    branch = _branch_lengths(wiring)
    return {"document": document, "runs": runs, "wiring": wiring, "branch_m": branch, "riser_m": floor["length"]["value"], "backdrop": backdrop_of(floor["architecture"]), "loads": {"lighting": f"L-{floor['id']}", "receptacles": f"T-{floor['id']}"}, "warnings": [f"floor {floor['id']}: {w}" for w in runs["warnings"] + wiring["warnings"]]}
