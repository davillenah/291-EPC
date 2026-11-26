"""DXF R2018 from the common drawing: layers with their colour, lineweight and linetype, the LTYPE table in mm with `$LTSCALE = scale / 1000`, one STYLE per text style, solid HATCH fills and
`$INSUNITS` = metres. Paper millimetres become model metres (`mm * scale / 1000`) with y up, so reading the file back gives the plan in metres."""
import hashlib
import io
import math
from typing import Dict, List, Optional

from ezdxf.enums import TextEntityAlignment
from ezdxf.colors import rgb2int

from epc_draw.arch.drawing import ArcItem, Drawing, ImageItem, Poly, Style, TextItem, load_style, pen_width, text_height

ALIGN = {"start": TextEntityAlignment.LEFT, "middle": TextEntityAlignment.CENTER, "end": TextEntityAlignment.RIGHT}
LINEWEIGHTS = (0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80, 90, 100)


def _rgb(hex_colour: str):
    h = hex_colour.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lineweight(width_mm: float) -> int:
    return min(LINEWEIGHTS, key=lambda v: abs(v - width_mm * 100))


def _setup(doc, d: Drawing, style: Style) -> None:
    doc.units = 6                                                      # metres: the model is the building at 1:1
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LUNITS"] = 2                                          # decimal
    doc.header["$LUPREC"] = 3
    doc.header["$TEXTSIZE"] = 2.5 * d.scale / 1000.0                   # the 2.5 mm text of the sheet, in metres
    doc.header["$LTSCALE"] = d.scale / 1000.0
    doc.styles.get("Standard").dxf.font = style.font["files"][0]       # Arial, as every style
    doc.header["$LWDISPLAY"] = 1
    for name, pat in style.linetypes.items():
        if name == "CONTINUOUS" or not pat:
            continue
        doc.linetypes.add(name, pattern=[sum(pat)] + [v if i % 2 == 0 else -v for i, v in enumerate(pat)], description=name)
    for name, h in style.text_styles.items():
        doc.styles.add(name, font=style.font["files"][0])
    for spec in style.layers.values():
        lay = doc.layers.add(spec.name, color=spec.aci, linetype=spec.linetype if spec.linetype != "CONTINUOUS" else "Continuous")
        lay.dxf.lineweight = _lineweight(spec.width)
        lay.dxf.true_color = rgb2int(_rgb(spec.hex))
        lay.description = spec.description


class _Writer:
    def __init__(self, msp, d: Drawing, style: Style):
        self.msp, self.k, self.style, self.height = msp, d.scale / 1000.0, style, d.size[1]

    def pt(self, p):
        return (p[0] * self.k, (self.height - p[1]) * self.k)         # the lower left corner of the sheet is the origin, y up

    def _attrs(self, it) -> dict:
        a = {"layer": it.layer}
        if it.linetype:
            a["linetype"] = "Continuous" if it.linetype == "CONTINUOUS" else it.linetype
        if it.width is not None:
            a["lineweight"] = _lineweight(it.width)                    # a title block sheet says its own widths
        return a

    def poly(self, it: Poly) -> None:
        pts = [self.pt(p) for p in it.points]
        spec = self.style.layers[it.layer]
        if it.fill:
            rgb = _rgb(spec.hex if it.fill == "layer" else it.fill)
            h = self.msp.add_hatch(dxfattribs={"layer": it.layer})
            h.set_solid_fill(rgb=rgb)
            h.paths.add_polyline_path(pts, is_closed=True)
        if it.stroke and pen_width(it, self.style):
            self.msp.add_lwpolyline(pts, close=it.closed, dxfattribs=self._attrs(it))

    def arc(self, it: ArcItem) -> None:
        self.msp.add_arc(self.pt(it.c), it.r * self.k, -it.end, -it.start, dxfattribs=self._attrs(it))

    def text(self, it: TextItem) -> None:
        h = text_height(it, self.style) * self.k
        t = self.msp.add_text(it.value, height=h, dxfattribs={"layer": it.layer, "style": it.style, "rotation": -it.rotation})
        t.set_placement(self.pt(it.at), align=ALIGN[it.anchor])

    def image(self, it: ImageItem) -> None:
        """A DXF keeps no picture here: the logos of a title block are left out of it."""


WIPEOUT_LAYER = "291-A-ANNO-NPLT"
BLOCK_NAMES = {"door": "EPC_DOOR", "window": "EPC_WINDOW"}


class _BlockWriter(_Writer):
    """Writes the items of one door or window into a block, in the frame of the opening: the origin at its centre, the x axis along the wall (so a block is the same wherever it is inserted and turned)."""

    def __init__(self, blk, d: Drawing, style: Style, group: tuple):
        super().__init__(blk, d, style)
        self.origin, self.angle = group[2], group[3]

    def pt(self, p):
        dx, dy = p[0] - self.origin[0], p[1] - self.origin[1]
        c, s = math.cos(math.radians(self.angle)), math.sin(math.radians(self.angle))
        return (round((dx * c + dy * s) * self.k, 6), round(-(-dx * s + dy * c) * self.k, 6))

    def arc(self, it: ArcItem) -> None:
        c = self.pt(it.c)
        self.msp.add_arc(c, it.r * self.k, -(it.end - self.angle), -(it.start - self.angle), dxfattribs=self._attrs(it))

    def wipeout(self, it: Poly) -> None:
        w = self.msp.add_wipeout([self.pt(p) for p in it.points], dxfattribs={"layer": it.layer})
        w.dxf.layer = it.layer
        w.dxf.flags = 1                                                 # shown (frames are shown or hidden by the viewer: WIPEOUTFRAME)


def _signature(kind: str, items: List[object], group: tuple, d: Drawing, style: Style) -> str:
    """A name for the block that depends only on its shape: equal doors (and windows) share one block."""
    from epc_draw.core import new_document
    probe = _BlockWriter(new_document("R2018", setup=False).blocks.new("_"), d, style, group)
    parts = [kind] + [(type(i).__name__, i.layer, tuple(round(v, 3) for p in (i.points if isinstance(i, Poly) else [i.c]) for v in probe.pt(p)), round(getattr(i, "r", 0.0), 3),
                       round(getattr(i, "start", 0.0) - probe.angle, 2), round(getattr(i, "end", 0.0) - probe.angle, 2)) for i in items]
    return f"{BLOCK_NAMES[kind]}_{hashlib.sha1(repr(parts).encode()).hexdigest()[:8].upper()}"


def _write_group(doc, msp, d: Drawing, style: Style, group: tuple, items: List[object]) -> None:
    """One door or window: its block (wipeout first, then the lines) and the insertion of it at the opening."""
    kind = group[0]
    name = _signature(kind, items, group, d, style)
    if name not in doc.blocks:
        w = _BlockWriter(doc.blocks.new(name), d, style, group)
        for it in items:
            if it.layer == WIPEOUT_LAYER:
                w.wipeout(it)
            else:
                {Poly: w.poly, ArcItem: w.arc}[type(it)](it)
    k = d.scale / 1000.0
    msp.add_blockref(name, ((group[2][0]) * k, (d.size[1] - group[2][1]) * k), dxfattribs={"layer": "291-A-DOOR-N" if kind == "door" else "291-A-GLAZ-N", "rotation": -group[3]})


def _extents(doc, d: Drawing) -> None:
    """What the drawing reaches and the limits of the sheet, kept in the model space (the writer copies them to the header), so that a program opens it on the whole sheet."""
    from ezdxf import bbox, zoom

    msp = doc.modelspace()
    box = bbox.extents(msp)
    if box.has_data:
        msp.dxf.extmin, msp.dxf.extmax = tuple(box.extmin), tuple(box.extmax)
    k = d.scale / 1000.0
    msp.dxf.limmin, msp.dxf.limmax = (0.0, 0.0), (d.size[0] * k, d.size[1] * k)
    zoom.extents(msp)


def _write_items(doc, d: Drawing, style: Style) -> None:
    """Every item of the drawing; the items of a door or a window (one group) are written once, as a block and its insertion, where the first of them comes."""
    w = _Writer(doc.modelspace(), d, style)
    grouped: Dict[tuple, List[object]] = {}
    for it in d.items:
        grouped.setdefault(getattr(it, "group", None), []).append(it)
    done = set()
    for it in d.items:
        g = getattr(it, "group", None)
        if g is None:
            {Poly: w.poly, ArcItem: w.arc, TextItem: w.text, ImageItem: w.image}[type(it)](it)
        elif g not in done:
            done.add(g)
            _write_group(doc, doc.modelspace(), d, style, g, grouped[g])


def to_dxf(d: Drawing, style: Optional[Style] = None) -> str:
    style = style or load_style()
    from epc_draw.core import new_document
    doc = new_document("R2018", setup=False)
    _setup(doc, d, style)
    _write_items(doc, d, style)
    _extents(doc, d)
    buf = io.StringIO()
    doc.write(buf)
    return buf.getvalue()
