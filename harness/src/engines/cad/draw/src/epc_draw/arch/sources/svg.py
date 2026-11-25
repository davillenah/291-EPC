"""SVG reader: line, polyline, polygon, rect, path (lines and circular arcs) and text, with the transforms of the groups and the stroke width of each element. Only what is drawn with a stroke is a
line of the plan: fills (rooms, wall tints, the paper) are not read. The scale is the one the file says (`data-scale`, or "1:100" in a title or a text), the units come from the size of the sheet
in millimetres against its viewBox; with both, the plan is in metres. Dashed arcs drawn in pieces are welded back, as in a PDF."""
import math
import re
from typing import List, Optional, Tuple
from xml.etree import ElementTree as ET

from epc_draw.arch.model import Arc, ArchError, Line, Options, Primitives, Text
from epc_draw.arch.sources import register
from epc_draw.arch.sources.pdf import SCALES, _edge_key as edge_key, weld_arcs
from epc_draw.arch.model import ArchError

Matrix = Tuple[float, float, float, float, float, float]
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
SKIP = {"defs", "pattern", "clipPath", "mask", "symbol", "marker", "title", "desc", "metadata", "style"}
NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
TRANSFORM = re.compile(r"(\w+)\s*\(([^)]*)\)")
LENGTH_MM = {"mm": 1.0, "cm": 10.0, "in": 25.4, "pt": 25.4 / 72.0, "px": 25.4 / 96.0}


def _nums(s: str) -> List[float]:
    return [float(x) for x in NUMBER.findall(s or "")]


def _mul(m: Matrix, n: Matrix) -> Matrix:
    """m applied after n."""
    a, b, c, d, e, f = m
    p, q, r, s, t, u = n
    return (a * p + c * q, b * p + d * q, a * r + c * s, b * r + d * s, a * t + c * u + e, b * t + d * u + f)


def _rotate(v: List[float]) -> Matrix:
    c, s = math.cos(math.radians(v[0])), math.sin(math.radians(v[0]))
    rot = (c, s, -s, c, 0.0, 0.0)
    if len(v) < 3:
        return rot
    return _mul(_mul((1.0, 0.0, 0.0, 1.0, v[1], v[2]), rot), (1.0, 0.0, 0.0, 1.0, -v[1], -v[2]))


TRANSFORMS = {
    "matrix": lambda v: tuple(v) if len(v) == 6 else IDENTITY,
    "translate": lambda v: (1.0, 0.0, 0.0, 1.0, v[0], v[1] if len(v) > 1 else 0.0),
    "scale": lambda v: (v[0], 0.0, 0.0, v[1] if len(v) > 1 else v[0], 0.0, 0.0),
    "rotate": _rotate,
}


def _one(name: str, v: List[float]) -> Matrix:
    return TRANSFORMS[name](v) if name in TRANSFORMS and v else IDENTITY


def parse_transform(text: Optional[str]) -> Matrix:
    m = IDENTITY
    for name, args in TRANSFORM.findall(text or ""):
        m = _mul(m, _one(name, _nums(args)))
    return m


def _apply(m: Matrix, p: Tuple[float, float]) -> Tuple[float, float]:
    return (m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5])


def _declarations(text: str) -> dict:
    out = {}
    for part in (text or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def css_rules(root) -> dict:
    """The simple rules of the `<style>` of a drawing (`.cls-1 { stroke: #000 }`, `line { ... }`), by class or tag name: what a program exports its strokes as when it does not write them on each element."""
    rules: dict = {}
    for el in root.iter():
        if el.tag.split("}")[-1] != "style":
            continue
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", "".join(el.itertext()), flags=re.S)):
            for name in (x.strip() for x in sel.split(",")):
                if re.fullmatch(r"\.?[\w-]+", name):
                    rules.setdefault(name, {}).update(_declarations(body))
    return rules


def _style(el, rules: Optional[dict] = None) -> dict:
    """The properties of an element: its attributes, then the rules of the style sheet (by tag and by class), then its own `style`."""
    out = dict(el.attrib)
    if rules:
        out.update(rules.get(el.tag.split("}")[-1], {}))
        for cls in (el.attrib.get("class") or "").split():
            out.update(rules.get("." + cls, {}))
    out.update(_declarations(el.attrib.get("style") or ""))
    return out


class _Ctx:
    def __init__(self, prims: Primitives, root=None):
        self.prims, self.skipped = prims, 0
        self.rules = css_rules(root) if root is not None else {}
        self.ids = {el.attrib["id"]: el for el in root.iter() if "id" in el.attrib} if root is not None else {}          # what a `<use>` points at
        self.depth = 0
        self.filled: List[Line] = []                       # the edges of shapes that are only filled (a wall drawn as a solid shape with no outline)
        self.target = prims.lines

    def line(self, a, b, m: Matrix, width: float, layer: str) -> None:
        if a != b:
            self.target.append(Line(_apply(m, a), _apply(m, b), width, layer))

    def poly(self, pts, closed: bool, m: Matrix, width: float, layer: str) -> None:
        for i in range(len(pts) - (0 if closed else 1)):
            self.line(pts[i], pts[(i + 1) % len(pts)], m, width, layer)

    def arc(self, c, r: float, start: float, end: float, m: Matrix, layer: str) -> None:
        s = math.hypot(m[0], m[1])
        flip = m[0] * m[3] - m[1] * m[2] < 0
        rot = math.degrees(math.atan2(m[1], m[0]))
        a0, a1 = (-end, -start) if flip else (start, end)
        self.prims.arcs.append(Arc(_apply(m, c), r * s, (a0 + rot) % 360.0, (a1 + rot) % 360.0, layer))


def _arc_center(p0, p1, r: float, large: int, sweep: int):
    """The centre and the angles (degrees, y down, growing) of the circular arc an SVG `A` command draws from p0 to p1."""
    mx, my = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    d2 = mx * mx + my * my
    if d2 == 0:
        return None
    r = max(r, math.sqrt(d2))
    coef = (1 if large != sweep else -1) * math.sqrt(max(0.0, (r * r - d2) / d2))
    c = (coef * my + (p0[0] + p1[0]) / 2, -coef * mx + (p0[1] + p1[1]) / 2)
    a0 = math.degrees(math.atan2(p0[1] - c[1], p0[0] - c[0])) % 360.0
    a1 = math.degrees(math.atan2(p1[1] - c[1], p1[0] - c[0])) % 360.0
    return c, r, (a0, a1) if sweep else (a1, a0)


class _PathReader:
    """Walks the commands of a path `d`: moves, lines and arcs are read; curves are counted as not read."""
    ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "Z": 0, "A": 7, "C": 6, "S": 4, "Q": 4, "T": 2}

    def __init__(self, d: str):
        self.tokens = re.findall(r"[MmLlHhVvZzAaCcSsQqTt]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d or "")
        self.i = 0

    def _take(self, cmd: str) -> List[float]:
        if cmd.upper() != "A":
            vals = [float(t) for t in self.tokens[self.i:self.i + self.ARGS[cmd.upper()]]]
            self.i += self.ARGS[cmd.upper()]
            return vals
        vals = [float(self.tokens[self.i + k]) for k in range(3)]
        flags = []
        self.i += 3
        for _ in range(2):                                    # the flags may be glued: "01" is two flags
            t = self.tokens[self.i]
            if len(t) > 1 and t[0] in "01" and not t.startswith(("0.", "1.")):
                flags.append(float(t[0]))
                self.tokens[self.i] = t[1:]
            else:
                flags.append(float(t))
                self.i += 1
        return vals + flags + self._xy()

    def _xy(self) -> List[float]:
        v = [float(self.tokens[self.i]), float(self.tokens[self.i + 1])]
        self.i += 2
        return v

    def commands(self):
        cmd, n = "", len(self.tokens)
        while self.i < n:
            if self.tokens[self.i].isalpha():
                cmd = self.tokens[self.i]
                self.i += 1
                if cmd in "Zz":
                    yield cmd, []
                    continue
            elif cmd in ("M", "m"):
                cmd = "L" if cmd == "M" else "l"
            elif not cmd or cmd in "Zz":
                return
            try:
                yield cmd, self._take(cmd)
            except (ValueError, IndexError):
                return


def _read_path(d: str, ctx: _Ctx, m: Matrix, width: float, layer: str) -> None:
    pos = start = (0.0, 0.0)
    for cmd, v in _PathReader(d).commands():
        rel, up = cmd.islower(), cmd.upper()
        ox, oy = pos if rel else (0.0, 0.0)
        if up == "Z":
            ctx.line(pos, start, m, width, layer)
            pos = start
        elif up == "M":
            pos = start = (ox + v[0], oy + v[1])
        elif up in ("L", "H", "V"):
            end = {"L": (ox + v[0], oy + (v[1] if len(v) > 1 else 0.0)), "H": (ox + v[0], pos[1]), "V": (pos[0], oy + v[0])}[up]
            ctx.line(pos, end, m, width, layer)
            pos = end
        elif up == "A":
            end = (ox + v[5], oy + v[6])
            found = _arc_center(pos, end, abs(v[0]), int(v[3]), int(v[4]))
            if found:
                ctx.arc(found[0], found[1], found[2][0], found[2][1], m, layer)
            pos = end
        else:
            ctx.skipped += 1
            pos = (ox + v[-2], oy + v[-1])


def _stroke_width(st: dict, m: Matrix) -> Optional[float]:
    """The stroke width in the units of the plan, or None when the element is not stroked."""
    if st.get("stroke", "none") in ("none", "transparent") or st.get("display") == "none":
        return None
    w = _nums(st.get("stroke-width", "1"))
    return (w[0] if w else 1.0) * math.sqrt(abs(m[0] * m[3] - m[1] * m[2]))


def _shape(el, tag: str, ctx: _Ctx, m: Matrix, w: float, layer: str) -> None:
    a = el.attrib
    num = lambda k: (_nums(a.get(k, "0")) or [0.0])[0]            # noqa: E731
    if tag == "line":
        ctx.line((num("x1"), num("y1")), (num("x2"), num("y2")), m, w, layer)
    elif tag in ("polyline", "polygon"):
        v = _nums(a.get("points", ""))
        ctx.poly(list(zip(v[0::2], v[1::2])), tag == "polygon", m, w, layer)
    elif tag == "rect":
        x, y, rw, rh = num("x"), num("y"), num("width"), num("height")
        ctx.poly([(x, y), (x + rw, y), (x + rw, y + rh), (x, y + rh)], True, m, w, layer)
    elif tag == "path":
        _read_path(a.get("d", ""), ctx, m, w, layer)


def _text(el, m: Matrix, st: dict) -> Optional[Text]:
    value = "".join(el.itertext()).strip()
    if not value:
        return None
    size = (_nums(st.get("font-size", "0")) or [0.0])[0] * math.sqrt(abs(m[0] * m[3] - m[1] * m[2]))
    return Text(value, _apply(m, (float((_nums(el.attrib.get("x", "0")) or [0.0])[0]), float((_nums(el.attrib.get("y", "0")) or [0.0])[0]))), size)


NAMED = {"black": 0.0, "gray": 0.5, "grey": 0.5, "darkgray": 0.66, "darkgrey": 0.66, "dimgray": 0.41, "dimgrey": 0.41, "white": 1.0}


def _rgb_of(f: str) -> Optional[List[float]]:
    """The red, green and blue of a colour written as #rgb, #rrggbb or rgb(r,g,b); None when it is not one of those."""
    if f.startswith("rgb"):
        return _nums(f)[:3] or None
    if not f.startswith("#") or len(f) not in (4, 7):
        return None
    h = f[1:] if len(f) == 7 else "".join(c * 2 for c in f[1:])
    try:
        return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        return None


def _grey_of(fill: str) -> Optional[float]:
    """The lightness (0 black, 1 white) of a solid colour written as a colour code or a usual name; None for none, a pattern or what is not understood."""
    f = (fill or "").strip().lower()
    if f in NAMED:
        return NAMED[f]
    rgb = _rgb_of(f)
    return (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0 if rgb and len(rgb) == 3 else None


def _dark_fill(st: dict) -> bool:
    """Is the element filled with a colour dark enough to be something drawn (a solid wall) and not the paper or a tint of a floor?"""
    g = _grey_of(st.get("fill", "black" if "fill" not in st else ""))
    return g is not None and g <= 0.85 and st.get("display") != "none"


def _draw(el, tag: str, ctx: _Ctx, m: Matrix, st: dict, layer: str) -> None:
    """What an element draws: its strokes as lines; when it has no stroke but a dark solid fill, its edges as lines kept apart (a wall drawn as a solid shape)."""
    w = _stroke_width(st, m)
    if w is not None:
        _shape(el, tag, ctx, m, w, layer)
    elif tag != "line" and _dark_fill(st):                              # a line has no area to fill
        ctx.target = ctx.filled
        _shape(el, tag, ctx, m, 0.0, layer)
        ctx.target = ctx.prims.lines


def _use(el, ctx: _Ctx, m: Matrix, layer: str, st: dict) -> None:
    """A `<use>` draws again what it points at, moved by its x and y (a symbol, a group of a library: a door, a hatch)."""
    ref = el.attrib.get("{http://www.w3.org/1999/xlink}href") or el.attrib.get("href") or ""
    target = ctx.ids.get(ref[1:]) if ref.startswith("#") else None
    if target is None or ctx.depth >= 8:
        return
    shift = (_nums(el.attrib.get("x", "0")) or [0.0])[0], (_nums(el.attrib.get("y", "0")) or [0.0])[0]
    inner = _mul(m, (1.0, 0.0, 0.0, 1.0, shift[0], shift[1]))
    ctx.depth += 1
    parts = list(target) if target.tag.split("}")[-1] == "symbol" else [target]
    for part in parts:
        _walk(part, ctx, inner, layer, st)
    ctx.depth -= 1


def _walk(el, ctx: _Ctx, m: Matrix, layer: str, inherited: dict) -> None:
    tag = el.tag.split("}")[-1]
    if tag in SKIP:
        return
    props = _style(el, ctx.rules)
    st = {**inherited, **{k: v for k, v in props.items() if k in ("stroke", "stroke-width", "font-size", "display", "fill")}}
    m = _mul(m, parse_transform(el.attrib.get("transform")))
    layer = el.attrib.get("id", layer) if tag == "g" else layer
    if tag == "use":
        _use(el, ctx, m, layer, st)
        return
    if tag == "text":
        t = _text(el, m, {**st, **props})
        if t:
            ctx.prims.texts.append(t)
        return
    if tag != "g":
        _draw(el, tag, ctx, m, st, layer)
    for child in el:
        _walk(child, ctx, m, layer, st)


def _length_mm(v: Optional[str]) -> Optional[float]:
    m = re.match(r"\s*([\d.]+)\s*(mm|cm|in|pt|px)?\s*$", v or "")
    return float(m.group(1)) * LENGTH_MM[m.group(2)] if m and m.group(2) else None


def _written_scale(root, texts: List[Text]) -> Optional[int]:
    declared = root.attrib.get("data-scale")
    if declared and declared.isdigit():
        return int(declared)
    words = " ".join([t.value for t in texts] + ["".join(e.itertext()) for e in root.iter() if e.tag.split("}")[-1] == "title"])
    found = [int(d) for d in re.findall(r"(?<![\d.,])1\s*[:/]\s*(\d{2,4})(?![\d.,])", words) if int(d) in SCALES]
    return max(set(found), key=found.count) if found else None


def _units_per_metre(root, scale: Optional[int]) -> Optional[float]:
    """Plan units per metre: the viewBox units per millimetre of paper, times the 1000/scale millimetres of paper per metre of the building."""
    wmm, box = _length_mm(root.attrib.get("width")), _nums(root.attrib.get("viewBox", ""))
    if not scale or not wmm or len(box) != 4 or not box[2]:
        return None
    return box[2] / wmm * 1000.0 / scale


def read_svg(data: bytes, options: Options) -> Primitives:
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        raise ArchError("err_svg_not_xml")
    prims = Primitives(source="svg", y_up=False, fit=True)
    ctx = _Ctx(prims, root)
    _walk(root, ctx, IDENTITY, "", {})
    outlined = {edge_key(l) for l in prims.lines}
    prims.lines += [l for l in ctx.filled if edge_key(l) not in outlined]       # a shape that is filled and outlined gives its edges twice: once
    prims.arcs = weld_arcs(prims.arcs)
    scale = _written_scale(root, prims.texts)
    prims.scale = scale
    prims.units_per_metre = options.units_per_metre or _units_per_metre(root, scale)
    if prims.units_per_metre and scale and not options.units_per_metre:
        prims.warnings.append(f"svg: the sheet says it is drawn at 1:{scale}; sizes are in metres from that")
    if ctx.skipped:
        prims.warnings.append(f"svg: {ctx.skipped} curves that are not arcs were not read")
    return prims


@register
class SvgReader:
    kind = "svg"

    def read(self, data: bytes, options: Options) -> Primitives:
        return read_svg(data, options)
