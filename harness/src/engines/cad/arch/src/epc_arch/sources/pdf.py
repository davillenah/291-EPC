"""PDF reader. A vector PDF (one made from CAD) is read path by path: its lines and the quarter circles of its door swings are exact. A PDF with no vector drawing in it (a scan) falls back to the
picture of its page, read like any image. Page, rotation of the page and nested forms are not interpreted: the first page as the CAD program wrote it."""
import ctypes
import io
import math
import re
from collections import Counter
from typing import List, Optional, Tuple

import pypdfium2 as pdfium
import pypdfium2.raw as raw
from PIL import Image

from epc_arch.config import PARAMS
from epc_arch.geometry import circle_through
from epc_arch.model import Arc, ArchError, Line, Options, Primitives, Text
from epc_arch.sources import register
from epc_arch.sources.raster import read_image
from epc_arch.sources.render import render_or_fail

SCALES = (20, 25, 50, 75, 100, 125, 150, 200, 250, 500)        # the scales a plan is drawn at
POINTS_PER_METRE = 72 / 0.0254
MIN_VECTOR = 12                                          # fewer strokes than this and the page is a picture
Seg = Tuple[int, float, float, bool]                     # type, x, y, closes the subpath


def _matrix(path) -> Tuple[float, float, float, float, float, float]:
    m = raw.FS_MATRIX()
    raw.FPDFPageObj_GetMatrix(path, m)
    return m.a, m.b, m.c, m.d, m.e, m.f


def _segments(path) -> List[Seg]:
    out = []
    for i in range(raw.FPDFPath_CountSegments(path)):
        seg = raw.FPDFPath_GetPathSegment(path, i)
        x, y = ctypes.c_float(), ctypes.c_float()
        raw.FPDFPathSegment_GetPoint(seg, x, y)
        out.append((raw.FPDFPathSegment_GetType(seg), x.value, y.value, bool(raw.FPDFPathSegment_GetClose(seg))))
    return out


def _stroke_width(path, m) -> float:
    w = ctypes.c_float()
    raw.FPDFPageObj_GetStrokeWidth(path, w)
    return float(w.value) * math.sqrt(abs(m[0] * m[3] - m[1] * m[2]))


def arc_from_bezier(p0, c1, c2, p3) -> Optional[Arc]:
    """A cubic Bézier that is (nearly) a circular arc, as the arc: CAD programs draw a door swing that way. None for any other curve."""
    pt = lambda t: tuple((1 - t) ** 3 * p0[k] + 3 * (1 - t) ** 2 * t * c1[k] + 3 * (1 - t) * t * t * c2[k] + t ** 3 * p3[k] for k in (0, 1))      # noqa: E731
    fit = circle_through(p0, pt(0.5), p3)
    if fit is None:
        return None
    c, r = fit
    if any(abs(math.hypot(pt(t)[0] - c[0], pt(t)[1] - c[1]) - r) > 0.03 * r for t in (0.25, 0.75)):
        return None
    ang = lambda p: math.degrees(math.atan2(p[1] - c[1], p[0] - c[0])) % 360.0                    # noqa: E731
    a0, am, a3 = ang(p0), ang(pt(0.5)), ang(p3)
    ccw = (am - a0) % 360.0 < (a3 - a0) % 360.0
    return Arc(c, r, a0 if ccw else a3, a3 if ccw else a0)


def _apply(m, x: float, y: float) -> Tuple[float, float]:
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


class _Walker:
    """Follows the segments of one path: where the pen is, where the subpath began and the control points of a curve being collected."""

    def __init__(self, prims: Primitives, skipped: List[int], width: float):
        self.prims, self.skipped, self.width = prims, skipped, width
        self.start: Optional[Tuple[float, float]] = None
        self.cur: Optional[Tuple[float, float]] = None
        self.bez: List[Tuple[float, float]] = []

    def move(self, p) -> None:
        self.start = self.cur = p

    def line(self, p) -> None:
        if self.cur is not None:
            self.prims.lines.append(Line(self.cur, p, self.width))
            self.cur = p

    def curve(self, p) -> None:
        if self.cur is None:
            return
        self.bez.append(p)
        if len(self.bez) == 3:
            arc = arc_from_bezier(self.cur, self.bez[0], self.bez[1], self.bez[2])
            self.prims.arcs.append(arc) if arc else self.skipped.append(1)
            self.cur, self.bez = self.bez[2], []

    def close(self) -> None:
        if self.start is not None and self.cur is not None and self.cur != self.start:
            self.prims.lines.append(Line(self.cur, self.start, self.width))
            self.cur = self.start


def _path_geometry(path, prims: Primitives, skipped: List[int]) -> None:
    m = _matrix(path)
    walk = _Walker(prims, skipped, _stroke_width(path, m))
    step = {raw.FPDF_SEGMENT_MOVETO: walk.move, raw.FPDF_SEGMENT_LINETO: walk.line, raw.FPDF_SEGMENT_BEZIERTO: walk.curve}
    for typ, x, y, close in _segments(path):
        if typ in step:
            step[typ](_apply(m, x, y))
        if close:
            walk.close()


def weld_arcs(arcs: List[Arc], gap: float = 6.0) -> List[Arc]:
    """A swing or a circle that a program wrote as many short arcs (some write them dashed) is one arc: pieces of the same circle that follow one another, up to `gap` degrees apart, are joined."""
    groups: dict = {}
    for a in arcs:
        groups.setdefault((round(a.c[0] / 0.5), round(a.c[1] / 0.5), round(a.r / 0.3)), []).append(a)
    out: List[Arc] = []
    for pieces in groups.values():
        pieces.sort(key=lambda a: a.start)
        cur = pieces[0]
        for a in pieces[1:]:
            if (a.start - cur.end) % 360.0 <= gap and a.start >= cur.start:
                cur = Arc(cur.c, cur.r, cur.start, a.end, cur.layer)
            else:
                out.append(cur)
                cur = a
        out.append(cur)
    return out


def _is_frame(line: Line, page: Tuple[float, float]) -> bool:
    """The border of the sheet: a long stroke along the edge of the page, which is not part of the plan."""
    w, h = page
    near = lambda v, edge: abs(v - edge) < 0.01 * max(w, h)          # noqa: E731
    horiz = near(line.a[1], line.b[1]) and (near(line.a[1], 0) or near(line.a[1], h))
    vert = near(line.a[0], line.b[0]) and (near(line.a[0], 0) or near(line.a[0], w))
    return (horiz or vert) and math.hypot(line.b[0] - line.a[0], line.b[1] - line.a[1]) > 0.9 * min(w, h)


def _paper_fill(obj) -> bool:
    """A path that is only filled, and with a colour so light that it is paper or a tint (white cuts over walls, room tints): it draws no line of the plan."""
    fill, stroke = ctypes.c_int(), ctypes.c_int()
    raw.FPDFPath_GetDrawMode(obj.raw, ctypes.byref(fill), ctypes.byref(stroke))
    if not fill.value or stroke.value:
        return False
    r, g, b, a = (ctypes.c_uint() for _ in range(4))
    if not raw.FPDFPageObj_GetFillColor(obj.raw, ctypes.byref(r), ctypes.byref(g), ctypes.byref(b), ctypes.byref(a)):
        return False
    return (0.299 * r.value + 0.587 * g.value + 0.114 * b.value) / 255.0 > 0.85


def _edge_key(l: Line) -> tuple:
    return tuple(sorted(((round(l.a[0], 1), round(l.a[1], 1)), (round(l.b[0], 1), round(l.b[1], 1)))))


def _is_filled_only(obj) -> bool:
    fill, stroke = ctypes.c_int(), ctypes.c_int()
    raw.FPDFPath_GetDrawMode(obj.raw, ctypes.byref(fill), ctypes.byref(stroke))
    return bool(fill.value) and not stroke.value


def _thin(prims: Primitives, limit: int) -> None:
    """A plan drawn with hatching, dimension ticks and furniture has far more strokes than walls and doors need: over the limit the arcs (door swings) and the longest strokes stay, in the order they
    were drawn, and the person is told how many of the shortest were left out."""
    keep = max(0, limit - len(prims.arcs))
    if len(prims.lines) <= keep:
        return
    size = lambda i: math.hypot(prims.lines[i].b[0] - prims.lines[i].a[0], prims.lines[i].b[1] - prims.lines[i].a[1])      # noqa: E731
    chosen = sorted(sorted(range(len(prims.lines)), key=size, reverse=True)[:keep])
    prims.warnings.append(f"pdf: {len(prims.lines)} strokes are more than can be read at once: the {len(prims.lines) - keep} shortest (hatching, ticks, fine detail) were left out")
    prims.lines = [prims.lines[i] for i in chosen]


def written_scale(page) -> Optional[int]:
    """The scale the sheet says it is drawn at ("ESCALA 1:50", "1/100"): the one written most often, when it is a usual scale."""
    try:
        text = page.get_textpage().get_text_range()
    except Exception:                                         # noqa: BLE001 - a page with no text layer
        return None
    found = Counter(int(d) for d in re.findall(r"(?<![\d.,])1\s*[:/]\s*(\d{2,3})(?![\d.,])", text) if int(d) in SCALES)
    return found.most_common(1)[0][0] if found else None


def _phrase(chars: list) -> Optional[Text]:
    """One phrase from its characters (text, left, bottom, right, top), or None when it is only blanks."""
    text = "".join(c[0] for c in chars).strip()
    if not text:
        return None
    letters = [c for c in chars if not c[0].isspace()]
    left, bottom = letters[0][1], min(c[2] for c in letters)
    return Text(text, (left, bottom), max(c[4] for c in letters) - bottom)


def _breaks(prev: tuple, box: tuple) -> bool:
    """A character starts a new phrase when it is on another line or far from the one before."""
    h = max(box[3] - box[1], prev[4] - prev[2], 1e-6)                # a hyphen, a comma or a dot is small: the letters around it give the height
    return abs(box[1] - prev[2]) > 0.5 * h or box[0] - prev[3] > 3.0 * h


def _utf8_pair(a: str, b: str) -> Optional[str]:
    """The character a pair stands for when it is the two bytes of a UTF-8 character read one by one (`Ã` + U+0091 for `Ñ`, `Â` + `·`... for `·`): what a CAD export writes in the text layer when it labels the glyphs with bytes."""
    try:
        pair = a.encode("cp1252") + b.encode("cp1252")                   # the bytes as a Windows text layer shows them (U+2018 is the byte 0x91)
    except UnicodeEncodeError:
        return None
    return pair.decode("utf-8", "ignore") or None if 0xC2 <= pair[0] <= 0xDF and 0x80 <= pair[1] <= 0xBF else None


def _repaired(full: str, boxes: list) -> Tuple[str, list]:
    """The text with each such pair merged into the character it stands for (its box the two boxes together); a text with none comes back as it was."""
    chars, out = [], []
    i = 0
    while i < len(full):
        merged = _utf8_pair(full[i], full[i + 1]) if i + 1 < len(full) and i + 1 < len(boxes) else None
        if merged:
            a, b = boxes[i], boxes[i + 1]
            chars.append(merged)
            out.append((min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])))
            i += 2
        else:
            chars.append(full[i])
            out.append(boxes[i] if i < len(boxes) else (0.0, 0.0, 0.0, 0.0))
            i += 1
    return "".join(chars), out


def _characters(page) -> Tuple[str, list]:
    """The characters of the page's text layer and the box (left, bottom, right, top) of each; nothing for a page with no text layer."""
    try:
        tp = page.get_textpage()
        full = tp.get_text_range()
        return _repaired(full, [tp.get_charbox(i) for i in range(min(tp.count_chars(), len(full)))])
    except Exception:                                         # noqa: BLE001 - a page with no text layer
        return "", []


def _grouped(full: str, boxes: list) -> List[list]:
    """The characters grouped along a baseline until a wide gap or the end of a line."""
    phrases: List[list] = [[]]
    last: Optional[tuple] = None                              # the last character that is not a blank, to measure the gap from
    for ch, box in zip(full, boxes):
        newline = ch in "\r\n"
        if newline or (last is not None and not ch.isspace() and _breaks(last, box)):
            phrases.append([])
        if newline:
            last = None
            continue
        phrases[-1].append((ch, *box))
        last = last if ch.isspace() else (ch, *box)
    return phrases


def page_texts(page) -> List[Text]:
    """The phrases written on the page with their position (to name the views of a sheet)."""
    full, boxes = _characters(page)
    return [t for t in (_phrase(c) for c in _grouped(full, boxes)) if t]


def _check_size(drawn: List[Tuple[bool, Primitives]]) -> None:
    if sum(len(q.lines) + len(q.arcs) for _, q in drawn) > PARAMS["plan"]["hard_max_primitives"]:
        raise ArchError("the PDF has too many strokes to read: export the plan with fewer layers or without hatching")


def _read_paths(page, prims: Primitives, skipped: List[int]) -> None:
    """The strokes of every path of the page, in the order they were drawn, leaving out what is only paper and the edges of a fill that an outline draws again."""
    drawn: List[Tuple[bool, Primitives]] = []
    for obj in page.get_objects(filter=[raw.FPDF_PAGEOBJ_PATH]):
        if _paper_fill(obj):
            continue
        part = Primitives(source="pdf")
        _path_geometry(obj.raw, part, skipped)
        drawn.append((_is_filled_only(obj), part))
        _check_size(drawn)
    _merge(drawn, prims)


def _merge(drawn: List[Tuple[bool, Primitives]], prims: Primitives) -> None:
    outlined = {_edge_key(l) for only, part in drawn if not only for l in part.lines}
    for only, part in drawn:
        prims.lines += [l for l in part.lines if not only or _edge_key(l) not in outlined]
        prims.arcs += part.arcs


def read_vector(data: bytes, options: Options) -> Primitives:
    try:
        page = pdfium.PdfDocument(data)[options.page]
    except Exception:                                         # noqa: BLE001 - damaged, protected or no such page
        raise ArchError("the PDF cannot be read: it may be damaged or protected")
    units = options.units_per_metre
    scale = None if units else written_scale(page)
    if scale:
        units = POINTS_PER_METRE / scale                                   # a metre of the building is 1/scale of a metre of paper
    prims = Primitives(source="pdf", y_up=True, fit=True, units_per_metre=units, scale=scale)
    if scale:
        prims.warnings.append(f"pdf: the sheet says it is drawn at 1:{scale}; sizes are in metres from that")
    skipped: List[int] = []
    _read_paths(page, prims, skipped)
    prims.texts = page_texts(page)
    prims.arcs = weld_arcs(prims.arcs)
    size = page.get_size()
    prims.lines = [l for l in prims.lines if not _is_frame(l, size)]
    _thin(prims, PARAMS["plan"]["max_primitives"])
    if skipped:
        prims.warnings.append(f"pdf: {len(skipped)} curves that are not arcs were not read")
    return prims


@register
class PdfReader:
    kind = "pdf"

    def read(self, data: bytes, options: Options) -> Primitives:
        prims = read_vector(data, options)
        if len(prims.lines) + len(prims.arcs) >= MIN_VECTOR:
            return prims
        picture = Image.open(io.BytesIO(render_or_fail(data, options.page, PARAMS["raster"]["max_side"])))
        out = read_image(picture, options)
        out.source = "pdf-image"
        out.warnings.insert(0, "pdf: no vector drawing found, the picture of the page was read")
        return out
