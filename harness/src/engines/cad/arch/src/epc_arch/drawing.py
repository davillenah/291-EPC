"""The common drawing: the one list of primitives (polygons, arcs, texts), each with its layer already assigned, from which SVG, DXF, PNG and PDF are all written (see `export/`).

Coordinates are paper millimetres of the sheet, y down. A line's width, dash and a text's height come from the style (`epc_style.json`) through the layer, never from an exporter. The DXF
exporter is the only one that leaves paper space: it writes model metres (`mm * scale / 1000`, y up) so that the file is read back in metres."""
import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from epc_arch.geometry import axis_of
from epc_arch.model import Architecture, Opening, Wall
from epc_arch.svgout import _clean_walls, _extent, _joined, _unit

Pt = Tuple[float, float]
PAPER = "#FFFFFF"
STYLE_PATH = Path(__file__).with_name("epc_style.json")
NOTE_KINDS = (("axes", "A-GRID"), ("dimensions", "A-DIM"), ("labels", "A-ANNO"))


@dataclass(frozen=True)
class LayerSpec:
    name: str
    pen: Optional[str]
    width: float                          # paper mm (0 = the layer draws no outline)
    linetype: str
    aci: int
    hex: str


@dataclass(frozen=True)
class Style:
    layers: Dict[str, LayerSpec]
    pens: Dict[str, float]
    linetypes: Dict[str, List[float]]
    text_styles: Dict[str, float]
    font: dict
    sheet: dict


PEN_RANGE = (0.05, 3.0)                  # mm: what a pen may be
TEXT_RANGE = (0.8, 10.0)                 # mm: capital height of a text style


def _style_of(raw: dict) -> Style:
    layers = {d["name"]: LayerSpec(d["name"], d["pen"], raw["pens"].get(d["pen"], 0.0), d["linetype"], d["aci"], d["hex"]) for d in raw["layers"]}
    return Style(layers, raw["pens"], raw["linetypes"], raw["text_styles"], raw["font"], raw["sheet"])


@lru_cache(maxsize=1)
def load_style() -> Style:
    return _style_of(json.loads(STYLE_PATH.read_text(encoding="utf-8")))


def _range_errors(overrides: dict, name: str, known: dict, limits: Tuple[float, float]) -> Dict[str, str]:
    given = overrides.get(name) or {}
    if not isinstance(given, dict):
        return {name: "an object"}
    lo, hi = limits
    errors: Dict[str, str] = {}
    for k, v in given.items():
        if k not in known:
            errors[f"{name}.{k}"] = "unknown: " + ", ".join(known)
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not lo <= v <= hi:
            errors[f"{name}.{k}"] = f"a number from {lo:g} to {hi:g} mm"
    return errors


def _layer_errors(overrides: dict, raw: dict) -> Dict[str, str]:
    layers = {d["name"] for d in raw["layers"]}
    errors: Dict[str, str] = {}
    for k, v in (overrides.get("layer_pens") or {}).items():
        if k not in layers:
            errors[f"layer_pens.{k}"] = "unknown layer"
        elif v not in raw["pens"]:
            errors[f"layer_pens.{k}"] = "one of " + ", ".join(raw["pens"])
    return errors


def style_errors(overrides: Optional[dict]) -> Dict[str, str]:
    """What is wrong with the changes an organization makes to the style of its drawings, field by field (empty when they are fine)."""
    if overrides is None:
        return {}
    if not isinstance(overrides, dict):
        return {"style": "an object"}
    raw = json.loads(STYLE_PATH.read_text(encoding="utf-8"))
    errors = {k: "unknown: pens, layer_pens, text_styles" for k in overrides if k not in ("pens", "layer_pens", "text_styles")}
    errors.update(_range_errors(overrides, "pens", raw["pens"], PEN_RANGE))
    errors.update(_range_errors(overrides, "text_styles", raw["text_styles"], TEXT_RANGE))
    errors.update(_layer_errors(overrides, raw))
    return errors


def style_with(overrides: Optional[dict]) -> Style:
    """The style of the engine with what an organization changed: the width of each pen, the pen each layer draws with and the height of each text style. Raises ValueError when a change is not valid."""
    if not overrides:
        return load_style()
    errors = style_errors(overrides)
    if errors:
        raise ValueError("; ".join(f"{k}: {v}" for k, v in errors.items()))
    raw = json.loads(STYLE_PATH.read_text(encoding="utf-8"))
    raw["pens"] = {**raw["pens"], **(overrides.get("pens") or {})}
    raw["text_styles"] = {**raw["text_styles"], **(overrides.get("text_styles") or {})}
    chosen = overrides.get("layer_pens") or {}
    raw["layers"] = [{**d, "pen": chosen.get(d["name"], d["pen"])} for d in raw["layers"]]
    return _style_of(raw)


@dataclass(frozen=True)
class Poly:
    """A polyline or polygon. `fill` is None (no fill), "layer" (the colour of its layer) or a hex colour; `stroke` draws the outline with the pen of its layer."""
    points: Tuple[Pt, ...]
    layer: str
    closed: bool = False
    fill: Optional[str] = None
    stroke: bool = True
    linetype: Optional[str] = None
    width: Optional[float] = None         # paper mm; None takes the pen of the layer (a title block sheet says its own widths)


@dataclass(frozen=True)
class ArcItem:
    """An arc of a circle, by the angles (degrees) of y-down paper space, going from `start` to `end` in the direction of growing angle."""
    c: Pt
    r: float
    start: float
    end: float
    layer: str
    linetype: Optional[str] = None
    width: Optional[float] = None


@dataclass(frozen=True)
class TextItem:
    value: str
    at: Pt                                # the baseline point
    style: str
    layer: str
    anchor: str = "start"                 # start, middle or end
    bold: bool = False
    size: Optional[float] = None          # paper mm; None takes the height of its text style
    rotation: float = 0.0                 # degrees clockwise on the paper, about `at`


@dataclass(frozen=True)
class ImageItem:
    """A picture (a logo) on the sheet: PNG or JPEG bytes and the box it fills, in paper mm."""
    data: bytes
    x: float
    y: float
    w: float
    h: float
    layer: str = "A-TITLE"


@dataclass
class Drawing:
    sheet: str
    size: Tuple[float, float]             # paper mm
    scale: int
    items: List[object] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    title: str = ""
    document: str = ""                   # the file the plan came from, for the title block
    template: Optional[str] = None       # the title block the sheet came from, when it was given (its name)

    def of(self, layer: str) -> List[object]:
        return [i for i in self.items if i.layer == layer]

    def layers_used(self) -> List[str]:
        used = {i.layer for i in self.items}
        return [n for n in load_style().layers if n in used]


def pen_width(it, style: "Style") -> float:
    """The width in paper mm an item is drawn with: its own when it says one, else the pen of its layer."""
    own = getattr(it, "width", None)
    return style.layers[it.layer].width if own is None else own


def text_height(it: "TextItem", style: "Style") -> float:
    return style.text_styles[it.style] if it.size is None else it.size


def arc_points(c: Pt, r: float, start: float, end: float, step: float = 4.0) -> List[Pt]:
    span = (end - start) % 360.0 or 360.0
    n = max(2, int(math.ceil(span / step)) + 1)
    return [(c[0] + r * math.cos(math.radians(start + span * i / (n - 1))), c[1] + r * math.sin(math.radians(start + span * i / (n - 1)))) for i in range(n)]


class _Dasher:
    """Walks a polyline with a dash pattern, collecting the pieces that are 'on'."""

    def __init__(self, pattern: List[float], start: Pt):
        self.pattern, self.i, self.on = pattern, 0, True
        self.left = pattern[0]
        self.piece: List[Pt] = [start]
        self.done: List[List[Pt]] = []

    def _flip(self, p: Pt) -> None:
        if self.on:
            self.piece.append(p)
            self.done.append(self.piece)
        self.i, self.on = self.i + 1, not self.on
        self.left = self.pattern[self.i % len(self.pattern)]
        self.piece = [p] if self.on else []

    def segment(self, a: Pt, b: Pt) -> None:
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        pos = 0.0
        while seg - pos > self.left:
            pos += self.left
            self._flip((a[0] + (b[0] - a[0]) * pos / seg, a[1] + (b[1] - a[1]) * pos / seg))
        self.left -= seg - pos
        if self.on:
            self.piece.append(b)

    def finish(self) -> List[List[Pt]]:
        return self.done + ([self.piece] if self.on and len(self.piece) > 1 else [])


def dashes(points: List[Pt], pattern: List[float], closed: bool = False) -> Iterator[List[Pt]]:
    """The 'on' pieces of a polyline drawn with a dash pattern (mm: on, off, on, off...). An empty pattern is a continuous line."""
    pts = list(points) + ([points[0]] if closed else [])
    if not pattern or len(pts) < 2:
        yield pts
        return
    d = _Dasher(pattern, pts[0])
    for a, b in zip(pts, pts[1:]):
        d.segment(a, b)
    yield from d.finish()


def hex_grey(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def text_width(value: str, height: float) -> float:
    """Width in mm of a text of the given height. Arial is about 0.55 of its height per character; used only for anchoring where the exporter cannot do it itself."""
    return 0.55 * height * len(value)


class _Map:
    """Plan units to paper millimetres."""

    def __init__(self, k: float, ox: float, oy: float):
        self.k, self.ox, self.oy = k, ox, oy

    def __call__(self, p: Pt) -> Pt:
        return (self.ox + self.k * p[0], self.oy + self.k * p[1])


def _poly(m: _Map, pts, layer: str, **kw) -> Poly:
    return Poly(tuple(m(p) for p in pts), layer, **kw)


def _gaps(w: Wall, openings: List[Opening]) -> List[Tuple[float, float]]:
    """Where the openings of a wall interrupt it: the spans along the wall from its start, in plan units, in order."""
    ux, uy = _unit(w)
    return sorted((((o.at[0] - w.a[0]) * ux + (o.at[1] - w.a[1]) * uy) - o.width / 2, ((o.at[0] - w.a[0]) * ux + (o.at[1] - w.a[1]) * uy) + o.width / 2)
                   for o in openings if o.wall == w.id)


def _solid_pieces(t0: float, t1: float, gaps: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """The stretches of a wall from `t0` to `t1` that are left once the gaps are taken out."""
    out, at = [], t0
    for g0, g1 in gaps:
        if g0 > at:
            out.append((at, min(g0, t1)))
        at = max(at, g1)
    if at < t1:
        out.append((at, t1))
    return [(x, y) for x, y in out if y - x > 1e-6]


def _wall_items(w: Wall, others: List[Wall], m: _Map, gaps: Optional[List[Tuple[float, float]]] = None) -> List[Poly]:
    """The wall as solid pieces (filled, with their outline): where a door, a window or an opening interrupts it there is no piece, so nothing has to be painted over it."""
    ja, jb = _joined(w, others, 0.75 * w.thickness)
    ux, uy = _unit(w)
    ox, oy = -uy * w.thickness / 2, ux * w.thickness / 2
    length = math.hypot(w.b[0] - w.a[0], w.b[1] - w.a[1])
    t0, t1 = -(w.thickness / 2 if ja else 0.0), length + (w.thickness / 2 if jb else 0.0)
    out: List[Poly] = []
    for s0, s1 in _solid_pieces(t0, t1, gaps or []):
        a = (w.a[0] + ux * s0, w.a[1] + uy * s0)
        b = (w.a[0] + ux * s1, w.a[1] + uy * s1)
        quad = [(a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), (b[0] - ox, b[1] - oy), (a[0] - ox, a[1] - oy)]
        out += [_poly(m, quad, "A-WALL-FILL", closed=True, fill="layer", stroke=False), _poly(m, quad, "A-WALL-CUT", closed=True)]
    return out


def _door_items(o: Opening, T: float, m: _Map) -> List[object]:
    out: List[object] = []
    ax = axis_of(o.angle)
    if o.hinge and o.swing:
        hx, hy = o.hinge
        r = math.hypot(o.swing[0] - hx, o.swing[1] - hy) or o.width
        sign = 1.0 if (o.at[0] - hx) * ax.ux + (o.at[1] - hy) * ax.uy >= 0 else -1.0
        closed = (hx + ax.ux * sign * r, hy + ax.uy * sign * r)
        a0 = math.degrees(math.atan2(closed[1] - hy, closed[0] - hx))
        a1 = math.degrees(math.atan2(o.swing[1] - hy, o.swing[0] - hx))
        cross = (closed[0] - hx) * (o.swing[1] - hy) - (closed[1] - hy) * (o.swing[0] - hx)
        start, end = (a0, a1) if cross > 0 else (a1, a0)
        out.append(ArcItem(m((hx, hy)), r * m.k, start, end, "A-DOOR-SWING"))
        tk = min(T * 0.35, r * 0.05)
        sx, sy = ax.ux * sign * tk, ax.uy * sign * tk
        out.append(_poly(m, [(hx, hy), o.swing, (o.swing[0] + sx, o.swing[1] + sy), (hx + sx, hy + sy)], "A-DOOR", closed=True))
    for s_ in (-1, 1):
        c = (o.at[0] + ax.ux * s_ * o.width / 2, o.at[1] + ax.uy * s_ * o.width / 2)
        out.append(_poly(m, [(c[0] + ax.nx * T / 2, c[1] + ax.ny * T / 2), (c[0] - ax.nx * T / 2, c[1] - ax.ny * T / 2)], "A-DOOR"))
    return out


def _window_items(o: Opening, T: float, m: _Map) -> List[object]:
    ax = axis_of(o.angle)
    hw = o.width / 2
    at = lambda t, n: (o.at[0] + ax.ux * t + ax.nx * n, o.at[1] + ax.uy * t + ax.ny * n)          # noqa: E731
    frame = [at(-hw, T / 2), at(hw, T / 2), at(hw, -T / 2), at(-hw, -T / 2)]
    out: List[object] = [_poly(m, frame, "A-WINDOW", closed=True)]
    for n in (T * 0.12, -T * 0.12):
        out.append(_poly(m, [at(-hw, n), at(hw, n)], "A-WINDOW-GLASS"))
    return out


def _hole_items(o: Opening, T: float, m: _Map) -> List[Poly]:
    ax = axis_of(o.angle)
    hw = o.width / 2
    a, b = (o.at[0] - ax.ux * hw, o.at[1] - ax.uy * hw), (o.at[0] + ax.ux * hw, o.at[1] + ax.uy * hw)
    out = [_poly(m, [(a[0] + ax.nx * n, a[1] + ax.ny * n), (b[0] + ax.nx * n, b[1] + ax.ny * n)], "A-OPENING") for n in (T / 2, -T / 2)]
    out += [_poly(m, [(p[0] + ax.nx * T / 2, p[1] + ax.ny * T / 2), (p[0] - ax.nx * T / 2, p[1] - ax.ny * T / 2)], "A-OPENING", linetype="CONTINUOUS") for p in (a, b)]
    return out


def _opening_items(arch: Architecture, T: float, m: _Map) -> List[object]:
    out: List[object] = []
    for o in arch.openings:
        out += {"door": _door_items, "window": _window_items}.get(o.kind, _hole_items)(o, T, m)
    return out


def _room_items(arch: Architecture, m: _Map) -> List[object]:
    out: List[object] = []
    for i, r in enumerate(arch.rooms):
        for x0, y0, x1, y1 in r.rects:
            out.append(_poly(m, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "A-ROOM", closed=True, fill="layer", stroke=False))
    return out


def _note_items(arch: Architecture, m: _Map, drop: set) -> List[object]:
    out: List[object] = []
    for kind, layer in NOTE_KINDS:
        marks = arch.annotations.get(kind)
        if marks is None:
            continue
        out += [_poly(m, [l.a, l.b], layer) for l in marks.lines]
        out += [ArcItem(m(a.c), a.r * m.k, a.start, a.end, layer) for a in marks.arcs]
        out += [TextItem(t.value, m(t.at), "TXT_18", "A-ANNO") for t in marks.texts if id(t) not in drop]
    return out


def _mover(rooms, items, m):
    from epc_arch.label_placer import move_round_tags
    return move_round_tags(items, rooms, m)


def _placer(rooms, items, m, tagged):
    from epc_arch.label_placer import place_room_labels as place
    return place(rooms, items, m, tagged)


def _name_sources(arch: Architecture) -> Tuple[set, set]:
    """The texts of the source that gave a room its name. A text that is only the name is dropped (the room label says it); a tag that carries more (a code, the area the designer wrote, after a dot)
    stays as drawn and its room's label does not repeat the name. Returns the ids of the texts to drop and the indices of the rooms whose name is already on a tag."""
    from epc_arch.recognizers.room_names import _centre, _clean, _inside
    marks = arch.annotations.get("labels")
    drop: set = set()
    tagged: set = set()
    for i, r in enumerate(arch.rooms):
        for t in (marks.texts if marks else []):
            word = _clean(t.value)
            if r.name and word and word in r.name and _inside(r, _centre(t)):
                (tagged if "·" in t.value else drop).add(i if "·" in t.value else id(t))
    return drop, tagged


def building_items(arch: Architecture, m: _Map) -> List[object]:
    T = arch.wall_thickness or 1.0
    walls = _clean_walls(arch)
    out: List[object] = _room_items(arch, m)
    for w in walls:
        out += _wall_items(w, walls, m, _gaps(w, arch.openings))
    drop, tagged = _name_sources(arch)
    out = out + _opening_items(arch, T, m) + _note_items(arch, m, drop)
    out = _mover(arch.rooms, out, m)
    return out + _placer(arch.rooms, out, m, tagged)


def _scale_for(side_mm: float, free: Tuple[float, float], requested: Optional[int], style: Style) -> Tuple[int, bool]:
    """The requested scale (1:100 by default) if the building fits the free area of the sheet, else the next standard scale that does. `side_mm` is the building at 1:1."""
    scales = style.sheet["scales"]
    first = requested or style.sheet["default_scale"]
    for s in [x for x in scales if x >= first] or [first]:
        if side_mm[0] / s <= free[0] and side_mm[1] / s <= free[1]:
            return s, s != first
    return scales[-1], True


def _sheet_of(style: Style, sheet: Optional[str], template) -> Tuple[str, Tuple[float, float], Tuple[float, float, float, float]]:
    """The name, the size and the free area (mm) of the sheet: the IRAM sheet given, or one of the standard sizes with the frame of the engine."""
    if template:
        return template.name, (float(template.size[0]), float(template.size[1])), template.free
    name = sheet or style.sheet["default"]
    W, H = style.sheet["sizes_mm"][name]
    return name, (float(W), float(H)), free_area(style, name)


def _place(arch: Architecture, d: Drawing, free, requested: Optional[int], style: Style) -> "_Map":
    """Choose the scale and map the plan to the middle of the free area."""
    x0, y0, x1, y1 = _extent(arch, _clean_walls(arch))
    m_per_unit = 1.0 / arch.units_per_metre if arch.units_per_metre else 20.0 / (max(arch.size) or 1.0)
    if not arch.units_per_metre:
        d.warnings.append("the units of the plan are unknown: drawn to a nominal 20 m side, not to scale")
    box_mm = ((x1 - x0) * m_per_unit * 1000.0, (y1 - y0) * m_per_unit * 1000.0)
    d.scale, changed = _scale_for(box_mm, (free[2] - free[0], free[3] - free[1]), requested or arch.drawing_scale, style)
    if changed:
        d.warnings.append(f"the plan does not fit sheet {d.sheet} at the requested scale: drawn at 1:{d.scale}")
    k = m_per_unit * 1000.0 / d.scale
    cx, cy = (free[0] + free[2]) / 2, (free[1] + free[3]) / 2
    return _Map(k, cx - k * (x0 + x1) / 2, cy - k * (y0 + y1) / 2)


def _frame_the_sheet(d: Drawing, arch: Architecture, style: Style, free, template, fields: Optional[dict]) -> None:
    from epc_arch.export.sheet_layout import add_scale_bar, add_sheet

    if not template:
        add_sheet(d, arch, style, free)
        return
    d.items += template.filled(_title_values(template, d, fields or {}))
    d.template = template.name
    add_scale_bar(d, arch, free[0] + 5.0, free[3] - 8.0)


def build_drawing(arch: Architecture, style: Optional[Style] = None, sheet: Optional[str] = None, scale: Optional[int] = None, document: str = "", template=None, fields: Optional[dict] = None) -> Drawing:
    """The plan as a Drawing on a sheet: the building at a standard scale, centred in the free area, then the frame and title block (`export.sheet_layout`). `document` is the name of the file the plan was read from, for the title block. With `template` (a `sheet_iram.SheetTemplate`) the sheet is that IRAM sheet and the plan goes in its free area; `fields` are values for its title block fields, over those the engine gives (`escala`, and `denominacion` when the sheet has only a sample)."""
    style = style or load_style()
    name, size, free = _sheet_of(style, sheet, template)
    d = Drawing(name, size, 0)
    m = _place(arch, d, free, scale, style)
    d.items = building_items(arch, m)
    d.title = arch.level.name.upper() if arch.level else "PLANTA ARQUITECTÓNICA"
    d.document = document
    _frame_the_sheet(d, arch, style, free, template, fields)
    return d


def _title_values(template, d: "Drawing", given: dict) -> dict:
    """The values for the fields of the title block: the scale the plan is drawn at, the name of the plan when the sheet has only a sample in its place, and what the caller says over both."""
    values = {"escala": f"1:{d.scale}"}
    sample = template.placeholders.get("denominacion", "")
    if not sample or sample.startswith("{") or sample == d.title:
        values["denominacion"] = d.title
    values.update({k: str(v) for k, v in given.items()})
    return values


def free_area(style: Style, sheet: str) -> Tuple[float, float, float, float]:
    """The part of the sheet inside the frame that the title block leaves free: (x0, y0, x1, y1) in mm."""
    W, H = style.sheet["sizes_mm"][sheet]
    mg = style.sheet["margin_mm"]
    bw, bh = style.sheet["block_mm"] if W >= 420 else style.sheet["block_min_mm"]
    return (mg["left"] + 5.0, mg["other"] + 5.0, W - mg["other"] - 5.0, H - mg["other"] - bh - 5.0)
