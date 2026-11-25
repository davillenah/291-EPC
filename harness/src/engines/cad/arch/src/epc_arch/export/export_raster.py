"""PNG and PDF from the common drawing, with the same style as the SVG and the DXF. The PNG is grey, `dpi` dots per inch (300 by default); the PDF is vector (lines, fills and dashes as
PDF operators) in Arial (named, not embedded: the viewer uses the Arial of the machine or its metric twin, so no font file is redistributed)."""
import io
import math
import zlib
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from epc_arch.drawing import PAPER, ArcItem, Drawing, ImageItem, Poly, Style, TextItem, arc_points, dashes, hex_grey, load_style, pen_width, text_height, text_width

FONT_DIRS = ("C:/Windows/Fonts", "/usr/share/fonts/truetype/msttcorefonts", "/usr/share/fonts/truetype/liberation", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts")
PT = 72.0 / 25.4
BS = chr(92)


def font_path(style: Style) -> Optional[str]:
    for d in FONT_DIRS:
        for f in style.font["files"]:
            p = Path(d) / f
            if p.exists():
                return str(p)
    return None


def _pieces(it, style: Style) -> List[List]:
    """The outline of an item as pieces of polyline, dashed by its linetype (a closed polygon's outline closes on itself)."""
    spec = style.layers[it.layer]
    pattern = style.linetypes[it.linetype or spec.linetype]
    if isinstance(it, ArcItem):
        return list(dashes(arc_points(it.c, it.r, it.start, it.end), pattern))
    return list(dashes(list(it.points), pattern, it.closed))


def _grey(hex_colour: str) -> int:
    return int(round(hex_grey(hex_colour) * 255))


def _stroke(draw: ImageDraw.ImageDraw, pieces, colour: str, width_mm: float, ppm: float) -> None:
    w = max(1, int(round(width_mm * ppm)))
    for piece in pieces:
        if len(piece) > 1:
            draw.line([(p[0] * ppm, p[1] * ppm) for p in piece], fill=_grey(colour), width=w, joint="curve")


def _paint_poly(draw: ImageDraw.ImageDraw, it: Poly, style: Style, ppm: float) -> None:
    spec = style.layers[it.layer]
    if it.fill:
        draw.polygon([(p[0] * ppm, p[1] * ppm) for p in it.points], fill=_grey(spec.hex if it.fill == "layer" else it.fill))
    if it.stroke and pen_width(it, style):
        _stroke(draw, _pieces(it, style), spec.hex, pen_width(it, style), ppm)


def _paint_text(img: Image.Image, it: TextItem, style: Style, ppm: float, path: Optional[str]) -> None:
    spec = style.layers[it.layer]
    size = max(6, int(round(text_height(it, style) * ppm)))
    font = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    anchor = {"start": "ls", "middle": "ms", "end": "rs"}[it.anchor] if path else None
    if not it.rotation:
        ImageDraw.Draw(img).text((it.at[0] * ppm, it.at[1] * ppm), it.value, font=font, fill=_grey(spec.hex), anchor=anchor)
        return
    box = int(size * (len(it.value) + 2) * 1.2)                        # a text that is turned is drawn upright on its own sheet, then turned and pasted
    layer = Image.new("L", (2 * box, 2 * box), 0)
    ImageDraw.Draw(layer).text((box, box), it.value, font=font, fill=255, anchor=anchor)
    turned = layer.rotate(-it.rotation, resample=Image.BICUBIC, center=(box, box))
    ink = Image.new("L", turned.size, _grey(spec.hex))
    img.paste(ink, (int(it.at[0] * ppm) - box, int(it.at[1] * ppm) - box), turned)


def _logo(it: ImageItem, ppm: float = 1.0) -> Image.Image:
    """The picture of a logo in grey on white, as big as its box on the paper at `ppm` pixels per mm."""
    pic = Image.open(io.BytesIO(it.data)).convert("RGBA")
    ground = Image.new("RGBA", pic.size, (255, 255, 255, 255))
    ground.alpha_composite(pic)
    pic = ground.convert("L")
    scale = min(it.w * ppm / pic.width, it.h * ppm / pic.height)             # kept in proportion, centred in its box, like the SVG does
    return pic.resize((max(1, int(pic.width * scale)), max(1, int(pic.height * scale))), Image.LANCZOS)


def _paint_image(img: Image.Image, it: ImageItem, ppm: float) -> None:
    pic = _logo(it, ppm)
    img.paste(pic, (int((it.x + it.w / 2) * ppm - pic.width / 2), int((it.y + it.h / 2) * ppm - pic.height / 2)))


def to_png(d: Drawing, style: Optional[Style] = None, dpi: int = 300) -> bytes:
    style = style or load_style()
    ppm = dpi / 25.4
    img = Image.new("L", (int(round(d.size[0] * ppm)), int(round(d.size[1] * ppm))), _grey(PAPER))
    draw = ImageDraw.Draw(img)
    path = font_path(style)
    for name in d.layers_used():
        for it in d.of(name):
            if isinstance(it, Poly):
                _paint_poly(draw, it, style, ppm)
            elif isinstance(it, ArcItem):
                _stroke(draw, _pieces(it, style), style.layers[name].hex, pen_width(it, style), ppm)
            elif isinstance(it, ImageItem):
                _paint_image(img, it, ppm)
            else:
                _paint_text(img, it, style, ppm, path)
    buf = io.BytesIO()
    img.save(buf, "PNG", dpi=(dpi, dpi))
    return buf.getvalue()


def _pdf_path(pts, H: float, close: bool) -> str:
    ops = [f"{pts[0][0] * PT:.3f} {(H - pts[0][1]) * PT:.3f} m"] + [f"{p[0] * PT:.3f} {(H - p[1]) * PT:.3f} l" for p in pts[1:]]
    return " ".join(ops) + (" h" if close else "")


def _pdf_dash(pattern) -> str:
    return ("[" + " ".join(f"{v * PT:.3f}" for v in pattern) + "] 0 d") if pattern else "[] 0 d"


def _pdf_pen(it, style: Style) -> str:
    spec = style.layers[it.layer]
    return f"{hex_grey(spec.hex):.3f} G {pen_width(it, style) * PT:.3f} w {_pdf_dash(style.linetypes[it.linetype or spec.linetype])}"


def _pdf_poly(it: Poly, style: Style, H: float) -> List[str]:
    spec = style.layers[it.layer]
    pts = list(it.points)
    out = []
    if it.fill:
        out.append(f"{hex_grey(spec.hex if it.fill == 'layer' else it.fill):.3f} g {_pdf_path(pts, H, True)} f")
    if it.stroke and pen_width(it, style):
        out += [_pdf_pen(it, style), f"{_pdf_path(pts, H, it.closed)} S"]
    return out


def _bezier_arc(it: ArcItem, H: float) -> str:
    """The arc as cubic Beziers of at most 90 degrees each, so that a PDF reader sees curves (as it does for any CAD export) and not a polyline."""
    span = (it.end - it.start) % 360.0 or 360.0
    n = max(1, int(math.ceil(span / 90.0)))
    step = math.radians(span / n)
    k = 4.0 / 3.0 * math.tan(step / 4.0)
    pt = lambda a, r=it.r: (it.c[0] + r * math.cos(a), it.c[1] + r * math.sin(a))                  # noqa: E731
    out = []
    for i in range(n):
        a0, a1 = math.radians(it.start) + i * step, math.radians(it.start) + (i + 1) * step
        p0, p3 = pt(a0), pt(a1)
        p1 = (p0[0] - k * it.r * math.sin(a0), p0[1] + k * it.r * math.cos(a0))
        p2 = (p3[0] + k * it.r * math.sin(a1), p3[1] - k * it.r * math.cos(a1))
        if i == 0:
            out.append(f"{p0[0] * PT:.3f} {(H - p0[1]) * PT:.3f} m")
        out.append(" ".join(f"{q[0] * PT:.3f} {(H - q[1]) * PT:.3f}" for q in (p1, p2, p3)) + " c")
    return " ".join(out)


def _pdf_arc(it: ArcItem, style: Style, H: float) -> List[str]:
    return [_pdf_pen(it, style), f"{_bezier_arc(it, H)} S"]


def _pdf_escaped(value: str) -> str:
    raw = value.encode("cp1252", "replace")
    for ch in (BS, "(", ")"):
        raw = raw.replace(ch.encode(), (BS + ch).encode())
    return raw.decode("latin-1")


def _pdf_text(it: TextItem, style: Style, H: float) -> List[str]:
    spec = style.layers[it.layer]
    h = text_height(it, style)
    w = text_width(it.value, h)
    shift = {"start": 0.0, "middle": w / 2, "end": w}[it.anchor]
    a = math.radians(-it.rotation)                                          # clockwise on the paper is counter-clockwise in a PDF
    x, y = it.at[0] - shift * math.cos(math.radians(it.rotation)), it.at[1] - shift * math.sin(math.radians(it.rotation))   # the anchor is on the baseline: the start is back along it
    font = "F2" if it.bold else "F1"
    matrix = f"{math.cos(a):.5f} {math.sin(a):.5f} {-math.sin(a):.5f} {math.cos(a):.5f} {x * PT:.3f} {(H - y) * PT:.3f} Tm"
    return [f"{hex_grey(spec.hex):.3f} g BT /{font} {h * PT:.3f} Tf {matrix} ({_pdf_escaped(it.value)}) Tj ET"]


def _pdf_image(it: ImageItem, n: int, H: float, ppm: float = 6.0) -> Tuple[List[str], bytes]:
    """The drawing operators for a logo and its PDF object (8-bit grey, deflated), `n` being its number among the images of the page."""
    pic = _logo(it, ppm)
    w, h = pic.width / ppm, pic.height / ppm
    x, y = it.x + (it.w - w) / 2, it.y + (it.h - h) / 2
    body = zlib.compress(pic.tobytes())
    obj = (f"<< /Type /XObject /Subtype /Image /Width {pic.width} /Height {pic.height} /ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode /Length {len(body)} >>".encode()
           + b"\nstream\n" + body + b"\nendstream")
    return [f"q {w * PT:.3f} 0 0 {h * PT:.3f} {x * PT:.3f} {(H - y - h) * PT:.3f} cm /Im{n} Do Q"], obj


def _pdf_ops(d: Drawing, style: Style) -> Tuple[List[str], List[bytes]]:
    """The drawing operators of the page, layer by layer, and the objects of the pictures they use."""
    ops: List[str] = []
    images: List[bytes] = []
    for it in [i for n in d.layers_used() for i in d.of(n)]:
        if isinstance(it, Poly):
            ops += _pdf_poly(it, style, d.size[1])
        elif isinstance(it, ArcItem):
            ops += _pdf_arc(it, style, d.size[1])
        elif isinstance(it, ImageItem):
            more, obj = _pdf_image(it, len(images) + 1, d.size[1])
            ops += more
            images.append(obj)
        else:
            ops += _pdf_text(it, style, d.size[1])
    return ops, images


def _pdf_font(name: str) -> bytes:
    """A font of the page by its name: Arial, not embedded (a viewer draws it with the Arial of the machine, or with the metric twin when it has none), so that no font file is distributed."""
    return f"<< /Type /Font /Subtype /TrueType /BaseFont /{name} /Encoding /WinAnsiEncoding >>".encode()


def to_pdf(d: Drawing, style: Optional[Style] = None) -> bytes:
    style = style or load_style()
    W, H = d.size
    ops, images = _pdf_ops(d, style)
    stream = zlib.compress(chr(10).join(ops).encode("latin-1"))
    xobjects = "".join(f"/Im{i + 1} {7 + i} 0 R " for i in range(len(images)))
    page = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W * PT:.3f} {H * PT:.3f}] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> /XObject << {xobjects}>> >> >>"
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", page.encode(),
            b"<< /Length %d /Filter /FlateDecode >>" % len(stream) + b"\nstream\n" + stream + b"\nendstream",
            _pdf_font(style.font["pdf_font"]), _pdf_font(style.font["pdf_font_bold"])] + images
    out, offsets = io.BytesIO(), []
    out.write(b"%PDF-1.4" + b"\n")
    for i, o in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj".encode() + b"\n" + o + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets))
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()
