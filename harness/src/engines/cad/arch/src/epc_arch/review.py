"""What a recognized (or authored) plan says about itself, for the person who checks it before the disciplines use it: which rooms each door joins, and the things worth a second look
(a room no door reaches, a room with no name, two rooms with one code, an area written on the plan that is not the area measured). Nothing is changed and nothing is judged against a standard:
these are notes about the drawing."""
import math
from typing import Any, Dict, List, Optional, Tuple

from epc_arch.config import PARAMS
from epc_arch.model import Architecture, Opening, Room

OUTSIDE = ""                               # the other side of a door or window that leads out of the building
STEPS = (1.0, 1.5, 2.0, 3.0)               # how far across the wall a room is looked for, in wall thicknesses


def _room_at(rooms: List[Room], p: Tuple[float, float]) -> Optional[Room]:
    return next((r for r in rooms if any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for x0, y0, x1, y1 in r.rects)), None)


def _side(o: Opening, rooms: List[Room], reach: float, sign: float) -> str:
    a = math.radians(o.angle + 90.0)
    for k in STEPS:
        room = _room_at(rooms, (o.at[0] + sign * k * reach * math.cos(a), o.at[1] + sign * k * reach * math.sin(a)))
        if room is not None:
            return room.id
    return OUTSIDE


def connections(arch: Architecture) -> List[Dict[str, Any]]:
    """Each door, window and plain opening with the rooms it joins: `{"opening", "kind", "rooms": [id, id]}`, an empty id being the outside (written last)."""
    reach = arch.wall_thickness or 0.0
    return [{"opening": o.id, "kind": o.kind, "rooms": sorted((_side(o, arch.rooms, reach, 1.0), _side(o, arch.rooms, reach, -1.0)), reverse=True)} for o in arch.openings]


def _reached(arch: Architecture) -> set:
    return {r for c in connections(arch) if c["kind"] in ("door", "opening") for r in c["rooms"] if r}


def _label(r: Room) -> str:
    return r.code or r.name or r.id


def _area_notes(arch: Architecture, tolerance: float) -> List[Dict[str, Any]]:
    return [{"rule": "area_differs", "room": r.id, "message": f"room {_label(r)}: the plan says {r.written_m2:.2f} m2 and {float(r.area_m2):.2f} m2 were measured"}
            for r in arch.rooms if r.written_m2 and r.area_m2 and abs(r.area_m2 - r.written_m2) > tolerance * r.written_m2]


def _code_notes(arch: Architecture) -> List[Dict[str, Any]]:
    codes = [r.code for r in arch.rooms if r.code]
    return [{"rule": "code_repeated", "room": r.id, "message": f"room {r.id}: the code {r.code} is on more than one room"} for r in arch.rooms if r.code and codes.count(r.code) > 1]


def notes(arch: Architecture) -> List[Dict[str, Any]]:
    """The things worth a second look, as `{"rule", "room", "message"}`; empty when there is nothing to say."""
    reached = _reached(arch)
    out = [{"rule": "no_door", "room": r.id, "message": f"room {_label(r)}: no door or opening reaches it"} for r in arch.rooms if r.id not in reached]
    out += [{"rule": "no_name", "room": r.id, "message": f"room {r.id}: no name was read inside it"} for r in arch.rooms if not r.name]
    out += _code_notes(arch) + _area_notes(arch, PARAMS["review"]["area_tolerance"])
    if arch.rooms and arch.units_per_metre is None:
        out.append({"rule": "no_units", "room": "", "message": "the plan does not say its units or scale: areas and sizes in metres are not known"})
    return out


def review(arch: Architecture) -> Dict[str, Any]:
    """`{"connections": [...], "notes": [...]}` of one plan."""
    return {"connections": connections(arch), "notes": notes(arch)}
