"""The name of a room is the text written inside it. The name stays as written (in the language of the drawing); its key is an English uppercase word from a list of usual names of rooms
(`room_keys` in `params.json`), so that nothing downstream depends on the language of the plan. Figures, areas, scales and dimensions are not names."""
import re
from dataclasses import replace
from typing import List, Optional, Tuple

from epc_arch.model import Room, Text
from epc_arch.recognizers import Context

NOT_A_NAME = re.compile(r"^[\d\s.,:;/xX±+\-–m²2³³%'\"°()]*$|^\s*(esc|escala|scale|n\.?\s*p\.?t|nivel|cota)\b", re.IGNORECASE)


def _centre(t: Text) -> Tuple[float, float]:
    """Where the text lies: its middle, from the baseline point, its height and about 0.55 of its height a letter."""
    h = t.height
    return t.at[0] + 0.275 * h * len(t.value), t.at[1] - 0.5 * h


def _inside(room: Room, p: Tuple[float, float]) -> bool:
    return any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for x0, y0, x1, y1 in room.rects)


def key_of(name: str, ctx: Context) -> str:
    for entry in ctx.params["room_keys"]:
        if re.search(entry["re"], name, re.IGNORECASE):
            return entry["key"]
    return ""


CODE = re.compile(r"^(?:[A-Z]|P[A-Z0-9]|PO)$")
TAG_CODE = re.compile(r"^[A-Z][A-Z0-9]{0,2}-\d+$")                    # `PT-03`, `P-03`, and a floor in the code: `P1-02`, `N1-01`


def _clean(value: str) -> str:
    """The name part of a tag ("COCINA · 16 PB": the name, then the area and the floor): what comes before the dot, without the lone letters and floor codes the tag carries around it."""
    words = [w for w in value.split("·")[0].split() if not TAG_CODE.match(w)]                 # `PT-03`, `P-03`, `V-01`: tags of the room, of a door, of a window
    while words and CODE.match(words[0]):
        words.pop(0)
    while words and CODE.match(words[-1]):
        words.pop()
    return " ".join(words)


def _name(room: Room, texts: List[Text]) -> str:
    held = [t for t in texts if not NOT_A_NAME.match(t.value) and _inside(room, _centre(t))]
    held.sort(key=lambda t: (round(t.at[1] / max(t.height, 1.0)), t.at[0]))              # reading order: lines from the top, words from the left
    return " ".join(w for w in (_clean(t.value) for t in held) if w)


TAG = re.compile(r"^(?P<code>[A-Z][A-Z0-9]{0,2}\s?-\s?\d+)\s*·\s*(?P<area>\d+(?:[.,]\d+)?)\s*m[²2]\s*$")


def _tag(room: Room, texts: List[Text]) -> Tuple[str, Optional[float]]:
    """The code and the area a tag inside the room carries ("PT-01 · 10,50 m²"): what the designer wrote, which is the plan's own figure for the room."""
    for t in texts:
        m = TAG.match(t.value.strip())
        if m and _inside(room, _centre(t)):
            return re.sub(r"\s", "", m["code"]), float(m["area"].replace(",", "."))
    return "", None


def name_rooms(rooms: List[Room], texts: List[Text], ctx: Context) -> List[Room]:
    out = []
    for r in rooms:
        name = _name(r, texts)
        code, written = _tag(r, texts)
        out.append(replace(r, name=name, key=key_of(name, ctx) if name else r.key, code=code, written_m2=written))
    return out
