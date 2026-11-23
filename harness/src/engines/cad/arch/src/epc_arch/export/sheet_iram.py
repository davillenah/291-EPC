"""The sheet of a drawing from an IRAM sheet SVG (frame, coordinates, title block IRAM 4504 / 4508, logos), as `epc_titleblock` makes it. The engines are independent of one another, so the sheet is
not asked of `epc_titleblock` from here: the caller gives its SVG (made with `epc_titleblock.service.render` or `python -m epc_titleblock.sheet_generator A3 sheet.svg`). Its marks become items of the
common drawing, in the layer `A-TITLE` with the widths and sizes the sheet says, so that the four formats show the same sheet; the logos are kept as pictures (an SVG, PNG and PDF show them; a DXF has none).

The sheet says where the drawing goes: `data-zona-util` is the usable zone and `data-rotulo` and `data-modificaciones` the boxes of the title block and the list of modifications; the plan is
laid out in the zone above them. The fields of the title block are the texts with a `data-key`: the caller's values replace them (the engine gives the scale and the name of the plan)."""
import base64
import math
import re
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from epc_arch.drawing import ArcItem, ImageItem, Poly, TextItem
from epc_arch.model import ArchError
from epc_arch.sources.svg import IDENTITY, Matrix, _apply, _mul, _nums, _style, parse_transform

LAYER = "A-TITLE"
TOKEN = re.compile(r"\{(\w+)\}")
GAP = 5.0                                              # mm of clear paper between the plan and the frame or the title block
Box = Tuple[float, float, float, float]


@dataclass
class SheetTemplate:
    """An IRAM sheet read: its name and size, the free area for the drawing, its marks, and which of its texts are fields."""
    name: str
    size: Tuple[float, float]
    free: Box
    items: List[object] = field(default_factory=list)
    keys: Dict[int, str] = field(default_factory=dict)          # index in `items` of a field's text -> its key (`escala`, `denominacion`...)
    placeholders: Dict[str, str] = field(default_factory=dict)  # key -> the sample value the sheet came with

    def filled(self, values: Dict[str, str]) -> List[object]:
        """The marks of the sheet with the given values in their fields. A `{key}` the sheet was made with (alone or inside a longer text, as in `CUIT: {empresa_cuit}`) takes its value, or nothing when
        nobody gave one (as `epc_titleblock` leaves it); a text left empty is not drawn."""
        out: List[object] = []
        for i, it in enumerate(self.items):
            key = self.keys.get(i)
            text = getattr(it, "value", None)
            if text is None:
                out.append(it)                                                # a line, a circle, a picture
                continue
            text = str(values[key]) if key in values else TOKEN.sub(lambda m: str(values.get(m.group(1), "")), text)
            if text.strip():
                out.append(replace(it, value=text))
        return out


def _box(text: Optional[str]) -> Optional[Box]:
    v = _nums(text or "")
    return (v[0], v[1], v[2], v[3]) if len(v) == 4 else None


def _free_area(root) -> Box:
    """The usable zone less the title block and the list of modifications: the zone above them, with a clear gap all round."""
    zone = _box(root.attrib.get("data-zona-util"))
    if zone is None:
        raise ArchError("err_sheet_no_zone")
    blocks = [b for b in (_box(root.attrib.get("data-rotulo")), _box(root.attrib.get("data-modificaciones"))) if b]
    bottom = min([b[1] for b in blocks] + [zone[3]])
    return zone[0] + GAP, zone[1] + GAP, zone[2] - GAP, bottom - GAP


def _width(st: dict, m: Matrix) -> float:
    w = (_nums(st.get("stroke-width", "0")) or [0.0])[0]
    return w * (abs(m[0] * m[3] - m[1] * m[2]) ** 0.5)


def _stroked(st: dict) -> bool:
    return st.get("stroke", "none") not in ("none", "transparent")


def _filled(st: dict) -> bool:
    return st.get("fill", "black") not in ("none", "transparent", "#fff", "#ffffff", "white")


class _Reader:
    def __init__(self) -> None:
        self.items: List[object] = []
        self.keys: Dict[int, str] = {}
        self.placeholders: Dict[str, str] = {}

    def add(self, item: object, key: str = "") -> None:
        if key:
            self.keys[len(self.items)] = key
        self.items.append(item)

    @staticmethod
    def _points(el, tag: str) -> List[Tuple[float, float]]:
        num = lambda k: (_nums(el.attrib.get(k, "0")) or [0.0])[0]                           # noqa: E731
        if tag == "line":
            return [(num("x1"), num("y1")), (num("x2"), num("y2"))]
        if tag in ("polygon", "polyline"):
            v = _nums(el.attrib.get("points", ""))
            return list(zip(v[0::2], v[1::2]))
        if tag == "rect":
            x, y, w, h = num("x"), num("y"), num("width"), num("height")
            return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        return []

    def shape(self, el, tag: str, m: Matrix, st: dict) -> None:
        pts = self._points(el, tag)
        closed = tag in ("polygon", "rect")
        fill = "layer" if closed and _filled(st) else None
        stroke = _stroked(st)
        if pts and (stroke or fill):
            self.add(Poly(tuple(_apply(m, p) for p in pts), LAYER, closed=closed, fill=fill, stroke=stroke, width=_width(st, m) if stroke else None))

    def circle(self, el, m: Matrix, st: dict) -> None:
        c = _apply(m, ((_nums(el.attrib.get("cx", "0")) or [0.0])[0], (_nums(el.attrib.get("cy", "0")) or [0.0])[0]))
        r = (_nums(el.attrib.get("r", "0")) or [0.0])[0] * (abs(m[0] * m[3] - m[1] * m[2]) ** 0.5)
        if _stroked(st) and r > 0:
            self.add(ArcItem(c, r, 0.0, 180.0, LAYER, width=_width(st, m)))
            self.add(ArcItem(c, r, 180.0, 360.0, LAYER, width=_width(st, m)))

    def text(self, el, m: Matrix, st: dict) -> None:
        value = "".join(el.itertext()).strip()
        if not value and not el.attrib.get("data-key"):
            return                                                          # an empty field is kept: a value may be given for it
        size = (_nums(el.attrib.get("font-size", "0")) or [0.0])[0] * (abs(m[0] * m[3] - m[1] * m[2]) ** 0.5)
        at = _apply(m, ((_nums(el.attrib.get("x", "0")) or [0.0])[0], (_nums(el.attrib.get("y", "0")) or [0.0])[0]))
        own = parse_transform(el.attrib.get("transform"))                       # a turned text turns about its own anchor: its place is the parent's, its angle the turn's
        angle = math.degrees(math.atan2(own[1], own[0]))
        key = el.attrib.get("data-key", "")
        if key:
            self.placeholders[key] = value
        self.add(TextItem(value, at, "TXT_25", LAYER, {"start": "start", "middle": "middle", "end": "end"}.get(el.attrib.get("text-anchor", "start"), "start"),
                          el.attrib.get("font-weight") == "bold" or "bold" in el.attrib.get("style", ""), size or None, angle), key)

    def image(self, el, m: Matrix) -> None:
        href = el.attrib.get("{http://www.w3.org/1999/xlink}href") or el.attrib.get("href") or ""
        mt = re.match(r"data:image/(?:png|jpeg);base64,(.*)", href, re.S)
        if not mt:
            return
        x0, y0 = _apply(m, ((_nums(el.attrib.get("x", "0")) or [0.0])[0], (_nums(el.attrib.get("y", "0")) or [0.0])[0]))
        x1, y1 = _apply(m, ((_nums(el.attrib.get("x", "0")) or [0.0])[0] + (_nums(el.attrib.get("width", "0")) or [0.0])[0],
                            (_nums(el.attrib.get("y", "0")) or [0.0])[0] + (_nums(el.attrib.get("height", "0")) or [0.0])[0]))
        self.add(ImageItem(base64.b64decode(mt.group(1)), x0, y0, x1 - x0, y1 - y0, LAYER))

    def walk(self, el, m: Matrix, inherited: dict) -> None:
        tag = el.tag.split("}")[-1]
        if tag in ("title", "defs", "metadata", "desc") or el.attrib.get("id") == "dibujo":
            return
        st = {**inherited, **{k: v for k, v in _style(el).items() if k in ("stroke", "stroke-width", "fill")}}
        if tag != "text":
            m = _mul(m, parse_transform(el.attrib.get("transform")))
        {"text": lambda: self.text(el, m, st), "circle": lambda: self.circle(el, m, st), "image": lambda: self.image(el, m)}.get(tag, lambda: self.shape(el, tag, m, st))()
        if tag in ("g", "svg"):
            for child in el:
                self.walk(child, m, st)


def load_template(svg: str) -> SheetTemplate:
    """Read an IRAM sheet SVG (see the module's doc). Raises ArchError when it is not one."""
    try:
        root = ET.fromstring(svg)
    except ET.ParseError:
        raise ArchError("err_sheet_not_xml")
    view = _nums(root.attrib.get("viewBox", ""))
    if len(view) != 4:
        raise ArchError("err_sheet_no_viewbox")
    r = _Reader()
    r.walk(root, IDENTITY, {})
    return SheetTemplate(root.attrib.get("data-format", "A?"), (view[2], view[3]), _free_area(root), r.items, r.keys, r.placeholders)
