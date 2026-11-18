"""The lighting data of a room the caller did not describe, taken from what the harness already knows (the owner asked for as few questions as possible).

The activity comes from the words of the room's name (`epc_lighting` data `room_types`), and with it the illuminance of `levels`; the luminaire is the first one of the catalogue;
the ceiling height is the engine's default (pending review). The coefficient of utilisation, the reflectances and the maintenance factor are left to the engine, which estimates them
(and says so). A room no rule matches is not guessed: it stays an error (describe it or exclude it). The values are design defaults pending review: they are what edit mode is for.
"""
from epc_lighting.config import data


def _words(name):
    return str(name or "").lower()


def activity_of(name):
    """The activity id for a room name, or None when no rule matches."""
    text = _words(name)
    return next((r["activity"] for r in data("room_types")["rules"] if any(w in text for w in r["words"])), None)


def room_data(room, luminaires, receptacles):
    """(lighting data, receptacle data or None) of a room, or None when its name matches no rule or the catalogue has no luminaire."""
    activity = activity_of(room.get("name"))
    if activity is None or not luminaires:
        return None
    lighting = {"activity": activity, "height_m": data("room_types")["default_height_m"], "luminaire": luminaires[0]["id"]}
    general = next((r for r in receptacles or [] if r.get("kind") == "general"), None)
    return lighting, ({"use": "general", "receptacle": general["id"]} if general else None)
