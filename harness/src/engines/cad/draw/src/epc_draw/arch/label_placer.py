"""Where the label of each room goes: its name over its area, small, inside the room and touching nothing drawn (walls, doors and their swings, windows, annotations). The sheet is drawn on a
fine grid with everything that is in the way, a little fattened; a label fits where its whole box lies on room floor and on no drawn thing, and of the places it fits the one nearest the room's
own label point is taken. When the two lines do not fit, the area alone is tried; when nothing fits the label stays at the label point."""
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

from epc_draw.arch.drawing import ArcItem, Poly, TextItem, arc_points, load_style, text_width
from epc_draw.arch.model import Room

RES = 2.0                   # grid cells per mm of paper
MARGIN = 0.5                # mm of clear paper left around what is drawn
STYLE = "TXT_18"
LINE = 1.25                 # line spacing, in text heights
ROOM_LAYER = "291-A-AREA"
Pt = Tuple[float, float]


def _extent(items: List[object], rooms: List[List[Tuple[float, float, float, float]]]) -> Tuple[float, float, float, float]:
    xs, ys = [], []
    for r in rooms:
        for x0, y0, x1, y1 in r:
            xs += [x0, x1]
            ys += [y0, y1]
    return min(xs) - 5, min(ys) - 5, max(xs) + 5, max(ys) + 5


def _text_box(t: TextItem, height: float) -> Tuple[float, float, float, float]:
    w = text_width(t.value, height)
    x = t.at[0] - {"start": 0.0, "middle": w / 2, "end": w}[t.anchor]
    return x, t.at[1] - height, x + w, t.at[1]


def _draw_obstacles(draw: ImageDraw.ImageDraw, items: List[object], origin: Pt, style) -> None:
    px = lambda p: ((p[0] - origin[0]) * RES, (p[1] - origin[1]) * RES)                   # noqa: E731
    for it in items:
        if it.layer == ROOM_LAYER:
            continue
        if isinstance(it, TextItem):
            x0, y0, x1, y1 = _text_box(it, style.text_styles[it.style])
            draw.rectangle([px((x0, y0)), px((x1, y1))], fill=1)
            continue
        spec = style.layers[it.layer]
        pts = arc_points(it.c, it.r, it.start, it.end) if isinstance(it, ArcItem) else list(it.points) + ([it.points[0]] if it.closed else [])
        if isinstance(it, Poly) and it.fill:
            draw.polygon([px(p) for p in it.points], fill=1)
        width = max(1, int(round((spec.width + 2 * MARGIN) * RES)))
        draw.line([px(p) for p in pts], fill=1, width=width, joint="curve")


def _grid(items: List[object], rooms: List[Room], m, style):
    boxes = [[tuple(v for v in (m((x0, y0)) + m((x1, y1)))) for x0, y0, x1, y1 in r.rects] for r in rooms]
    flat = [[(a, b, c, d) for a, b, c, d in rs] for rs in boxes]
    x0, y0, x1, y1 = _extent(items, flat)
    size = (int((x1 - x0) * RES) + 2, int((y1 - y0) * RES) + 2)
    obstacle, floor = Image.new("L", size, 0), Image.new("L", size, 0)
    _draw_obstacles(ImageDraw.Draw(obstacle), items, (x0, y0), style)
    return np.asarray(obstacle, bool), flat, (x0, y0)


def _room_floor(rects, shape, origin) -> np.ndarray:
    img = Image.new("L", (shape[1], shape[0]), 0)
    d = ImageDraw.Draw(img)
    for a, b, c, e in rects:
        x0, y0 = (a - origin[0]) * RES, (b - origin[1]) * RES
        d.rectangle([x0, y0, max(x0, (c - origin[0]) * RES - 1), max(y0, (e - origin[1]) * RES - 1)], fill=1)
    return np.asarray(img, bool)


def _fits(bad: np.ndarray, w: int, h: int) -> np.ndarray:
    """True where a w x h box with its corner there covers no `bad` cell (by integral image)."""
    s = np.pad(bad.astype(np.int32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    total = s[h:, w:] - s[:-h, w:] - s[h:, :-w] + s[:-h, :-w]
    return total == 0


def _best(free: np.ndarray, w: int, h: int, want: Pt) -> Optional[Tuple[int, int]]:
    ys, xs = np.nonzero(free)
    if not len(xs):
        return None
    i = int(np.argmin((xs + w / 2 - want[0]) ** 2 + (ys + h / 2 - want[1]) ** 2))
    return int(xs[i]), int(ys[i])


def _tag_line(room: Room, tagged: bool) -> str:
    """The line under the name: the area, with the code of the room before it ("PB-01 · 16,0 m²": the tag a reader finds again) when the room has one and no tag of the source says it."""
    area = f"{room.area_m2:.1f} m²".replace(".", ",") if room.area_m2 else ""
    if not room.code or tagged:
        return area
    return f"{room.code} · {area}" if area else room.code


def _lines_of(room: Room, index: int, tagged: bool) -> List[str]:
    return [t for t in ("" if tagged else room.name, _tag_line(room, tagged) or str(index + 1)) if t]


def _place(lines: List[str], height: float, obstacle: np.ndarray, floor: np.ndarray, origin: Pt, want: Pt) -> Optional[Pt]:
    """The centre of the block of lines at the nearest place where it fits, in paper mm."""
    w = int(max(text_width(t, height) for t in lines) * RES) + 1
    h = int(len(lines) * LINE * height * RES) + 1
    if h >= obstacle.shape[0] or w >= obstacle.shape[1]:
        return None
    hit = _best(_fits(obstacle | ~floor, w, h), w, h, ((want[0] - origin[0]) * RES, (want[1] - origin[1]) * RES))
    return None if hit is None else (origin[0] + (hit[0] + w / 2) / RES, origin[1] + (hit[1] + h / 2) / RES)


def _texts(lines: List[str], centre: Pt, height: float, layer: str) -> List[TextItem]:
    n = len(lines)
    return [TextItem(t, (centre[0], centre[1] + (i - (n - 1) / 2) * LINE * height + 0.35 * height), STYLE, layer, "middle") for i, t in enumerate(lines)]


def place_room_labels(rooms: List[Room], items: List[object], m, tagged: set = frozenset(), layer: str = "291-A-AREA-IDEN") -> List[TextItem]:
    style = load_style()
    if not rooms:
        return []
    height = style.text_styles[STYLE]
    obstacle, flat, origin = _grid(items, rooms, m, style)
    out: List[TextItem] = []
    for i, r in enumerate(rooms):
        floor = _room_floor(flat[i], obstacle.shape, origin)
        want = m(r.at)
        lines = _lines_of(r, i, i in tagged)
        for attempt in (lines, lines[-1:]):                                   # the name and the area, else the area alone
            centre = _place(attempt, height, obstacle, floor, origin, want)
            if centre:
                out += _texts(attempt, centre, height, layer)
                break
        else:
            out += _texts(lines[-1:], want, height, layer)
    return out


def _circle_groups(items: List[object]) -> dict:
    """The arcs of the annotations that make a circle, by centre and radius."""
    groups: dict = {}
    for it in items:
        if isinstance(it, ArcItem) and it.layer == "291-A-ANNO":
            groups.setdefault((round(it.c[0], 1), round(it.c[1], 1), round(it.r, 1)), []).append(it)
    return groups


def _is_round_tag(arcs: List[ArcItem], cx: float, cy: float, r: float, leaders: List[Poly]) -> bool:
    """A small whole circle with no leader hanging from it."""
    sweep = sum((a.end - a.start) % 360.0 or 360.0 for a in arcs)
    hung = any(min(((p[0] - cx) ** 2 + (p[1] - cy) ** 2) ** 0.5 for p in l.points) < 1.3 * r for l in leaders)
    return sweep >= 330.0 and r <= 6.0 and not hung


def _notes_in(notes: List[TextItem], cx: float, cy: float, r: float) -> List[TextItem]:
    return [t for t in notes if abs(t.at[0] - cx) <= r and abs(t.at[1] - cy) <= r]


def _circles(items: List[object]) -> List[Tuple[List[ArcItem], List[TextItem], Pt, float]]:
    """The round tags of the annotations (a circle drawn as arcs, with the text inside it) that no leader hangs from: (arcs, texts, centre, radius) each. Those with a leader stay where they are."""
    leaders = [it for it in items if isinstance(it, Poly) and it.layer == "291-A-ANNO" and len(it.points) == 2]
    notes = [t for t in items if isinstance(t, TextItem) and t.layer == "291-A-ANNO"]
    out = []
    for (cx, cy, r), arcs in _circle_groups(items).items():
        if _is_round_tag(arcs, cx, cy, r, leaders):
            out.append((arcs, _notes_in(notes, cx, cy, r), (cx, cy), r))
    return out


def _shifted(it, dx: float, dy: float):
    if isinstance(it, ArcItem):
        return ArcItem((it.c[0] + dx, it.c[1] + dy), it.r, it.start, it.end, it.layer, it.linetype)
    return TextItem(it.value, (it.at[0] + dx, it.at[1] + dy), it.style, it.layer, it.anchor, it.bold)


def _free_spot(obstacle: np.ndarray, floor: np.ndarray, centre: Pt, r: float, origin: Pt) -> Optional[Pt]:
    """Where a round tag goes instead of where it is: the nearest place on a floor where it touches nothing, or None when it is fine where it is or has nowhere to go."""
    side = int((2 * r + 2 * MARGIN) * RES) + 1
    want = ((centre[0] - origin[0]) * RES, (centre[1] - origin[1]) * RES)
    hit = _best(_fits(obstacle | ~floor, side, side), side, side, want)
    if hit is None or (abs(hit[0] + side / 2 - want[0]) <= 1.0 and abs(hit[1] + side / 2 - want[1]) <= 1.0):
        return None
    return origin[0] + (hit[0] + side / 2) / RES, origin[1] + (hit[1] + side / 2) / RES


def _free_spot(obstacle: np.ndarray, floor: np.ndarray, centre: Pt, r: float, origin: Pt) -> Optional[Pt]:
    """Where a round tag goes instead of where it is: the nearest place on a floor where it touches nothing, or None when it is fine where it is or has nowhere to go."""
    side = int((2 * r + 2 * MARGIN) * RES) + 1
    want = ((centre[0] - origin[0]) * RES, (centre[1] - origin[1]) * RES)
    hit = _best(_fits(obstacle | ~floor, side, side), side, side, want)
    if hit is None or (abs(hit[0] + side / 2 - want[0]) <= 1.0 and abs(hit[1] + side / 2 - want[1]) <= 1.0):
        return None
    return origin[0] + (hit[0] + side / 2) / RES, origin[1] + (hit[1] + side / 2) / RES


def _floor_union(flat, shape, origin: Pt) -> np.ndarray:
    floor = np.zeros(shape, bool)
    for rects in flat:
        floor |= _room_floor(rects, shape, origin)
    return floor


def _relocate(tags, obstacle: np.ndarray, floor: np.ndarray, origin: Pt) -> dict:
    """The new item for each item of each round tag that has to move, by the id of the old one."""
    replace: dict = {}
    for arcs, texts, (cx, cy), r in tags:
        spot = _free_spot(obstacle, floor, (cx, cy), r, origin)
        if spot is None:
            continue
        replace.update({id(x): _shifted(x, spot[0] - cx, spot[1] - cy) for x in arcs + texts})
        _stamp(obstacle, spot, r + MARGIN, origin)
    return replace


def move_round_tags(items: List[object], rooms: List[Room], m) -> List[object]:
    """Round tags (a door's number, say) drawn on a wall hide its edges: each is moved to the nearest place on a room's floor where it touches nothing."""
    tags = _circles(items)
    if not tags or not rooms:
        return items
    moving = {id(x) for arcs, texts, _, _ in tags for x in arcs + texts}
    obstacle, flat, origin = _grid([it for it in items if id(it) not in moving], rooms, m, load_style())
    replace = _relocate(tags, obstacle, _floor_union(flat, obstacle.shape, origin), origin)
    return [replace.get(id(it), it) for it in items]


def _stamp(obstacle: np.ndarray, centre: Pt, radius: float, origin: Pt) -> None:
    x0, y0 = int((centre[0] - radius - origin[0]) * RES), int((centre[1] - radius - origin[1]) * RES)
    x1, y1 = int((centre[0] + radius - origin[0]) * RES) + 1, int((centre[1] + radius - origin[1]) * RES) + 1
    obstacle[max(y0, 0):y1, max(x0, 0):x1] = True
