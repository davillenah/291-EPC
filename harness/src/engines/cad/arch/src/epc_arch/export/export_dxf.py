"""DXF R2018 from the common drawing: layers with their colour, lineweight and linetype, the LTYPE table in mm with `$LTSCALE = scale / 1000`, one STYLE per text style, solid HATCH fills and
`$INSUNITS` = metres. Paper millimetres become model metres (`mm * scale / 1000`) with y up, so reading the file back gives the plan in metres."""
import io
from typing import Optional

import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf.colors import rgb2int

from epc_arch.drawing import ArcItem, Drawing, ImageItem, Poly, Style, TextItem, load_style, pen_width, text_height

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


def to_dxf(d: Drawing, style: Optional[Style] = None) -> str:
    style = style or load_style()
    doc = ezdxf.new("R2018", setup=False)
    _setup(doc, d, style)
    w = _Writer(doc.modelspace(), d, style)
    for it in d.items:
        {Poly: w.poly, ArcItem: w.arc, TextItem: w.text, ImageItem: w.image}[type(it)](it)
    _extents(doc, d)
    buf = io.StringIO()
    doc.write(buf)
    return buf.getvalue()
