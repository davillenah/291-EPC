"""A stand-in for a symbol the library does not have yet: a box with the symbol's name inside (owner rule, 2026-11-24).

The owner replaces the box by the real symbol later. A stand-in is never silent: it is asked for by name, it says it is provisional, and `resolve` still
raises for a symbol that does not exist. A pure function: the answer is data (an SVG fragment and the entities of a DXF drawing); the caller draws it.
"""
from typing import Any, Dict
from xml.sax.saxutils import escape

from epc_draw.symbols.errors import SymbolsError

CHAR_WIDTH = 0.6        # average width of a character, as a fraction of the text height (the box only needs to hold the name)


def placeholder(name: str, *, width: float, height: float, text_height: float) -> Dict[str, Any]:
    """A box `width` x `height` (drawing units) with `name` centred inside, origin at the lower left corner.

    `text_height` is the wanted text height; when the name does not fit across the box, the text gets smaller (the answer says which height was used).
    Returns {"name", "size", "text_height", "provisional": True, "svg": fragment, "entities": [{"type": "line"|"text", ...}]}."""
    label = " ".join(str(name).split())
    if not label:
        raise SymbolsError("err_placeholder_name")
    for field, value in (("width", width), ("height", height), ("text_height", text_height)):
        if not value > 0:
            raise SymbolsError("err_placeholder_size", field=field, value=value)
    fit = 0.9 * width / (CHAR_WIDTH * len(label))
    th = min(float(text_height), fit, 0.9 * height)
    corners = [(0.0, 0.0), (width, 0.0), (width, height), (0.0, height)]
    lines = [{"type": "line", "start": corners[i], "end": corners[(i + 1) % 4]} for i in range(4)]
    text = {"type": "text", "text": label, "at": (width / 2, height / 2), "height": th, "align": "middle_center"}
    svg = (f'<g class="provisional-symbol"><rect x="0" y="0" width="{width:g}" height="{height:g}" fill="none" stroke="currentColor"/>'
           f'<text x="{width / 2:g}" y="{height / 2:g}" font-size="{th:g}" text-anchor="middle" dominant-baseline="central">{escape(label)}</text></g>')
    return {"name": label, "size": (float(width), float(height)), "text_height": th, "provisional": True, "svg": svg, "entities": lines + [text]}
