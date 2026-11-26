"""The master output: SVG in paper millimetres, one `<g id="A-...">` per layer (in the order of the style), widths and dashes in mm, the font named once."""
from typing import List
from xml.sax.saxutils import escape

import base64

from epc_draw.arch.drawing import PAPER, ArcItem, Drawing, ImageItem, Poly, Style, TextItem, load_style, pen_width, text_height

ANCHOR = {"start": "start", "middle": "middle", "end": "end"}


def _f(v: float) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".")


def _dash(style: Style, linetype: str) -> str:
    pat = style.linetypes[linetype]
    return f' stroke-dasharray="{" ".join(_f(x) for x in pat)}"' if pat else ""


def _poly(it: Poly, style: Style) -> str:
    spec = style.layers[it.layer]
    fill = spec.hex if it.fill == "layer" else (it.fill or "none")
    stroke = spec.hex if it.stroke and pen_width(it, style) else "none"
    tag = "polygon" if it.closed else "polyline"
    pts = " ".join(f"{_f(x)},{_f(y)}" for x, y in it.points)
    lt = it.linetype or spec.linetype
    return f'<{tag} points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{_f(pen_width(it, style))}"{_dash(style, lt)} stroke-linejoin="miter"/>'


def _arc(it: ArcItem, style: Style) -> str:
    import math
    spec = style.layers[it.layer]
    span = (it.end - it.start) % 360.0 or 360.0
    p = (it.c[0] + it.r * math.cos(math.radians(it.start)), it.c[1] + it.r * math.sin(math.radians(it.start)))
    q = (it.c[0] + it.r * math.cos(math.radians(it.start + span)), it.c[1] + it.r * math.sin(math.radians(it.start + span)))
    lt = it.linetype or spec.linetype
    return (f'<path d="M{_f(p[0])} {_f(p[1])} A{_f(it.r)} {_f(it.r)} 0 {1 if span > 180 else 0} 1 {_f(q[0])} {_f(q[1])}" fill="none" stroke="{spec.hex}" '
            f'stroke-width="{_f(pen_width(it, style))}"{_dash(style, lt)}/>')


def _text(it: TextItem, style: Style) -> str:
    spec = style.layers[it.layer]
    h = text_height(it, style)
    weight = ' font-weight="700"' if it.bold else ""
    turn = f' transform="rotate({_f(it.rotation)} {_f(it.at[0])} {_f(it.at[1])})"' if it.rotation else ""
    return f'<text x="{_f(it.at[0])}" y="{_f(it.at[1])}" font-size="{_f(h)}" text-anchor="{ANCHOR[it.anchor]}"{weight}{turn} fill="{spec.hex}" stroke="none" data-style="{it.style}">{escape(it.value)}</text>'


def _image(it: ImageItem) -> str:
    kind = "jpeg" if it.data[:3] == b"\xff\xd8\xff" else "png"
    return (f'<image x="{_f(it.x)}" y="{_f(it.y)}" width="{_f(it.w)}" height="{_f(it.h)}" preserveAspectRatio="xMidYMid meet" '
            f'href="data:image/{kind};base64,{base64.b64encode(it.data).decode("ascii")}"/>')


def _item(it, style: Style) -> str:
    if isinstance(it, Poly):
        return _poly(it, style)
    if isinstance(it, ArcItem):
        return _arc(it, style)
    if isinstance(it, ImageItem):
        return _image(it)
    return _text(it, style)


def to_svg(d: Drawing, style: Style = None) -> str:
    style = style or load_style()
    W, H = d.size
    font = f'{style.font["family"]}, {style.font["fallback"]}'
    out: List[str] = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(W)}mm" height="{_f(H)}mm" viewBox="0 0 {_f(W)} {_f(H)}" font-family="{font}" data-scale="{d.scale}" data-sheet="{d.sheet}">',
                      f'<rect x="0" y="0" width="{_f(W)}" height="{_f(H)}" fill="{PAPER}"/>']
    for name in d.layers_used():
        spec = style.layers[name]
        out.append(f'<g id="{name}" data-pen="{spec.pen or ""}" data-linetype="{spec.linetype}">')
        out += [_item(it, style) for it in d.of(name)]
        out.append("</g>")
    return chr(10).join(out + ["</svg>", ""])
