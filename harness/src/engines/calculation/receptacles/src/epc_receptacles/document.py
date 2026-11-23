"""Reads and checks the document the engine is given: the outlets in use and the rooms (rectangles, in metres)."""
import json
from typing import Any, Dict, List, Union

from epc_receptacles.config import PARAMS, data
from epc_receptacles.model import NORMS, ReceptaclesError
from epc_receptacles.model import ReceptaclesError

MAX_SIDE_M = 1000.0


def load(source: Union[Dict[str, Any], str, bytes]) -> Dict[str, Any]:
    """The document as a dict: it may come as a dict, a JSON string or JSON bytes."""
    if isinstance(source, (str, bytes, bytearray)):
        try:
            source = json.loads(source)
        except ValueError as exc:
            raise ReceptaclesError("err_document_not_json", exc=exc)
    if not isinstance(source, dict):
        raise ReceptaclesError("err_document_shape")
    return source


def _number(where: str, value: Any, low: float, high: float, optional: bool = False) -> Any:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low < value <= high:
        raise ReceptaclesError("err_number_range", where=where, low=low, high=high)
    return float(value)


def _outlet(entry: Any, index: int) -> Dict[str, Any]:
    where = f"receptacles[{index}]"
    if not isinstance(entry, dict) or not str(entry.get("id", "")).strip():
        raise ReceptaclesError("err_outlet_needs_id", where=where)
    kind = entry.get("kind", "general")
    if kind not in ("general", "special"):
        raise ReceptaclesError("err_outlet_kind", where=where)
    out = dict(entry)
    out["kind"] = kind
    out["power_va"] = _number(f"{where}.power_va", entry.get("power_va", 100), -1, 100000)
    out["height_m"] = _number(f"{where}.height_m", entry.get("height_m"), -1, 5, optional=True)
    return out


def _positions(where: str, value: Any) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > PARAMS["max_outlets_per_room"]:
        raise ReceptaclesError("err_positions_list", where=where, max_outlets=PARAMS['max_outlets_per_room'])
    for i, p in enumerate(value):
        if not isinstance(p, dict) or any(isinstance(p.get(k), bool) or not isinstance(p.get(k), (int, float)) for k in ("x_m", "y_m")):
            raise ReceptaclesError("err_position_needs_xy", where=where, i=i)
    return value


def _use(where: str, entry: Dict[str, Any]) -> str:
    use = entry.get("use") or "general"
    if use not in data("uses")["uses"]:
        raise ReceptaclesError("err_use_unknown", where=where, use=use, known=', '.join(data('uses')['uses']))
    return use


def _count(where: str, count: Any) -> Any:
    """The number of outlets the person fixed: a whole number up to the limit, or nothing."""
    if count is not None and (isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= PARAMS["max_outlets_per_room"]):
        raise ReceptaclesError("err_count_invalid", where=where, max_outlets=PARAMS['max_outlets_per_room'])
    return count


def _narrow(where: str, value: Any) -> bool:
    """Whether the person states the room is a narrow corridor in the sense of the norm; nothing means it is not stated."""
    if value is not None and not isinstance(value, bool):
        raise ReceptaclesError("err_narrow_invalid", where=where)
    return bool(value)


def _choices(where: str, entry: Dict[str, Any], outlets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """What the person chose for the room: the outlet, the section of the norm and a fixed count (each one optional)."""
    outlet = entry.get("receptacle") or ""
    if outlet and outlet not in outlets:
        raise ReceptaclesError("err_outlet_not_found", where=where, outlet=outlet)
    norm = entry.get("norm") or None
    if norm is not None and norm not in NORMS:
        raise ReceptaclesError("err_norm_invalid", where=where, allowed=', '.join(NORMS))
    return {"receptacle": outlet, "norm": norm, "count": _count(where, entry.get("count"))}


def _room(entry: Any, index: int, outlets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    where = f"rooms[{index}]"
    if not isinstance(entry, dict) or not str(entry.get("id", "")).strip():
        raise ReceptaclesError("err_room_needs_id", where=where)
    return {**entry, "id": str(entry["id"]), "name": str(entry.get("name") or entry["id"]), "use": _use(where, entry), **_choices(where, entry, outlets),
            "length_m": _number(f"{where}.length_m", entry.get("length_m"), 0, MAX_SIDE_M), "width_m": _number(f"{where}.width_m", entry.get("width_m"), 0, MAX_SIDE_M),
            "height_m": _number(f"{where}.height_m", entry.get("height_m"), -1, 5, optional=True), "positions": _positions(where, entry.get("positions")), "wet": entry.get("wet"), "narrow": _narrow(where, entry.get("narrow"))}


def parse(source: Union[Dict[str, Any], str, bytes]) -> Dict[str, Any]:
    """The document checked and ready: `{"receptacles": {id: outlet}, "rooms": [room]}`. Every problem says what to correct."""
    doc = load(source)
    raw = doc.get("receptacles", [])
    if not isinstance(raw, list):
        raise ReceptaclesError("err_receptacles_not_list")
    outlets = {}
    for i, entry in enumerate(raw):
        o = _outlet(entry, i)
        if o["id"] in outlets:
            raise ReceptaclesError("err_outlet_id_repeated", i=i, o=o['id'])
        outlets[o["id"]] = o
    rooms_raw = doc.get("rooms", [])
    if not isinstance(rooms_raw, list) or len(rooms_raw) > PARAMS["max_rooms"]:
        raise ReceptaclesError("err_rooms_list", max_rooms=PARAMS['max_rooms'])
    rooms, seen = [], set()
    for i, entry in enumerate(rooms_raw):
        room = _room(entry, i, outlets)
        if room["id"] in seen:
            raise ReceptaclesError("err_room_id_repeated", i=i, room=room['id'])
        seen.add(room["id"])
        rooms.append(room)
    return {"receptacles": outlets, "rooms": rooms}
