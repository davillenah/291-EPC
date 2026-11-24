"""The plan as the person drew it, for a vector PDF: the pictures of its page, cut to the frame of the recognized plan and put in an SVG of that frame, so that what is shown is the sheet itself (its fills, its colours, its tags)
and the walls, doors and windows found lie over it exactly. The page is drawn once for each layer (the walls, the doors, the windows, the axes, the dimensions, the labels and, in `291-A-ANNO-REFR`, all the rest), each from the
objects of the page that belong to it, so that a layer can be hidden by taking its group out. The page and the plan space are tied by the texts both have (a text that is once in the page and once in the plan says where a point
of the page went); when they cannot be tied well enough the plan is shown as the engine draws it."""
import base64
import io
import math
from typing import Callable, Dict, List, Optional, Set, Tuple

import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as raw

from epc_arch.model import Architecture, Options, Text
from epc_arch.model import Primitives
from epc_arch.sources.pdf import _path_geometry, page_texts

PIXELS_PER_POINT = 3.0                                    # of the page picture: 216 dpi
MIN_PAIRS = 4
MAX_MISFIT = 0.004                                        # of the side of the plan: how far a text may lie from where the fit puts it


def _once(texts: List[Text]) -> Dict[str, Text]:
    """The texts whose value is written once (the others cannot tell which is which)."""
    seen: Dict[str, List[Text]] = {}
    for t in texts:
        seen.setdefault(t.value.strip(), []).append(t)
    return {v: ts[0] for v, ts in seen.items() if len(ts) == 1 and v}


def _marks_texts(arch: Architecture) -> List[Text]:
    return [t for marks in arch.annotations.values() for t in marks.texts]


def fit(page: List[Text], plan: List[Text], side: float) -> Optional[Tuple[float, float, float]]:
    """`(k, tx, ty)` with `X = k·x + tx` and `Y = ty − k·y` from the page (y up) to the plan space (y down), or None when the texts do not agree on one."""
    a, b = _once(page), _once(plan)
    pairs = [(a[v].at, b[v].at) for v in a if v in b]
    if len(pairs) < MIN_PAIRS:
        return None
    rows, rhs = [], []
    for (x, y), (X, Y) in pairs:
        rows += [[x, 1.0, 0.0], [-y, 0.0, 1.0]]
        rhs += [X, Y]
    (k, tx, ty), *_ = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)
    if k <= 0:
        return None
    worst = max(max(abs(k * x + tx - X), abs(ty - k * y - Y)) for (x, y), (X, Y) in pairs)
    return (float(k), float(tx), float(ty)) if worst <= MAX_MISFIT * side else None


Tie = Tuple[float, float, float]
LAYERS = (("291-A-ANNO-REFR", "arq.background"), ("291-A-WALL-FULL-N", "arq.wall"), ("291-A-DOOR-N", "arq.door"), ("291-A-GLAZ-N", "arq.window"), ("291-A-WALL-JAMB-N", "arq.opening"),
          ("291-A-GRID", "arq.axes"), ("291-A-ANNO-DIMS", "arq.dimension"), ("291-A-ANNO-IDEN", "arq.label"))
NOTE_OF = (("axes", "291-A-GRID"), ("dimensions", "291-A-ANNO-DIMS"), ("labels", "291-A-ANNO-IDEN"))        # in the order a stroke is given to one of them
GRID = 0.5                                                  # points: how near the ends of a stroke of the page must be to those of a mark
MATCHED = 0.5                                               # of the elements of an object that have to be those of a mark


def _to_page(tie: Tie) -> Callable[[Tuple[float, float]], Tuple[float, float]]:
    k, tx, ty = tie
    return lambda p: ((p[0] - tx) / k, (ty - p[1]) / k)


def _cell(p: Tuple[float, float]) -> Tuple[int, int]:
    return (int(round(p[0] / GRID)), int(round(p[1] / GRID)))


def _near(cells: Set[Tuple[int, int]], p: Tuple[float, float]) -> bool:
    cx, cy = _cell(p)
    return any((cx + dx, cy + dy) in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1))


def _marks_on_page(arch: Architecture, to_page) -> Dict[str, Tuple[Set, Set, List]]:
    """For each kind of annotation: the cells of the ends of its strokes and of the centres of its arcs, and where its texts start, all on the page."""
    out = {}
    for kind, _ in NOTE_OF:
        marks = arch.annotations.get(kind)
        if marks is None:
            continue
        ends = {_cell(to_page(e)) for l in marks.lines for e in (l.a, l.b)}
        centres = {_cell(to_page(a.c)) for a in marks.arcs}
        out[kind] = (ends, centres, [to_page(t.at) for t in marks.texts])
    return out


def _stroke_kind(part: Primitives, marks) -> Optional[str]:
    """The kind of annotation an object is, when most of its strokes are those of the marks of that kind."""
    total = len(part.lines) + len(part.arcs)
    if not total:
        return None
    for kind, layer in NOTE_OF:
        if kind not in marks:
            continue
        ends, centres, _ = marks[kind]
        hit = sum(1 for l in part.lines if _near(ends, l.a) and _near(ends, l.b)) + sum(1 for a in part.arcs if _near(centres, a.c))
        if hit >= MATCHED * total:
            return layer
    return None


def _text_kind(bounds: Tuple[float, float, float, float], marks) -> Optional[str]:
    l, b, r, t = bounds
    for kind, layer in NOTE_OF:
        if kind in marks and any(l - 1 <= x <= r + 1 and b - 1 <= y <= t + 1 for x, y in marks[kind][2]):
            return layer
    return None


def _opening_layer(arch: Architecture, c: Tuple[float, float], size: float) -> Optional[str]:
    """A small object near a door, a window or an opening is that one's (the swing, the leaf, the frame, the glass)."""
    layer_of = {"door": "291-A-DOOR-N", "window": "291-A-GLAZ-N"}
    for o in arch.openings:
        if size <= 1.4 * o.width and math.hypot(c[0] - o.at[0], c[1] - o.at[1]) <= 0.85 * o.width:
            return layer_of.get(o.kind, "291-A-WALL-JAMB-N")
    return None


def _in_wall(arch: Architecture, c: Tuple[float, float], thin: Optional[float] = None) -> bool:
    """Whether a point is on a wall; with `thin`, only on a wall at least that thick (a solid piece is as thick as a wall, a stroke is not)."""
    for w in arch.walls:
        if thin is not None and w.thickness < thin:
            continue
        ux, uy = w.b[0] - w.a[0], w.b[1] - w.a[1]
        length = math.hypot(ux, uy) or 1.0
        ux, uy = ux / length, uy / length
        along = (c[0] - w.a[0]) * ux + (c[1] - w.a[1]) * uy
        across = -(c[0] - w.a[0]) * uy + (c[1] - w.a[1]) * ux
        if -0.5 * w.thickness <= along <= length + 0.5 * w.thickness and abs(across) <= 0.7 * w.thickness:
            return True
    return False


def _centre_and_sizes(bounds, tie: Tie) -> Tuple[Tuple[float, float], float, float]:
    k, tx, ty = tie
    l, b, r, t = bounds
    return (k * (l + r) / 2 + tx, ty - k * (b + t) / 2), k * max(r - l, t - b), k * min(r - l, t - b)


def _solid_wall(arch: Architecture, bounds, tie: Tie) -> bool:
    """A solid piece of a wall: on a wall and as thick as it (so not an axis, a dimension or a tag that runs along it)."""
    c, _, thin = _centre_and_sizes(bounds, tie)
    return thin >= 0.4 * (arch.wall_thickness or 1.0) and _in_wall(arch, c)


def _building_layer(arch: Architecture, bounds, tie: Tie) -> str:
    c, size, _ = _centre_and_sizes(bounds, tie)
    return _opening_layer(arch, c, size) or ("291-A-WALL-FULL-N" if _in_wall(arch, c) else "291-A-ANNO-REFR")


def classify(page, arch: Architecture, tie: Tie) -> Dict[int, str]:
    """The layer of each object of the page (by its place in `get_objects`)."""
    marks = _marks_on_page(arch, _to_page(tie))
    out: Dict[int, str] = {}
    for i, obj in enumerate(page.get_objects()):
        bounds = obj.get_bounds()
        if obj.type == raw.FPDF_PAGEOBJ_TEXT:
            out[i] = _text_kind(bounds, marks) or "291-A-ANNO-REFR"
        elif obj.type == raw.FPDF_PAGEOBJ_PATH:
            part = Primitives(source="pdf")
            _path_geometry(obj.raw, part, [])
            out[i] = "291-A-WALL-FULL-N" if _solid_wall(arch, bounds, tie) else _stroke_kind(part, marks) or _building_layer(arch, bounds, tie)
        else:
            out[i] = "291-A-ANNO-REFR"
    return out


def _layer_picture(data: bytes, index: int, keep: Set[int], tie: Tie, size: Tuple[float, float]):
    """The PNG (transparent where the layer draws nothing) of the objects `keep`, cut to what they draw, and where it goes in the plan frame: `(png, x, y, w, h)`; None when the layer draws nothing."""
    from PIL import Image

    page = pdfium.PdfDocument(data)[index]
    for i, obj in enumerate(list(page.get_objects())):
        if i not in keep:
            page.remove_obj(obj)
    page.gen_content()
    k, tx, ty = tie
    W, H = size
    s = PIXELS_PER_POINT
    bitmap = page.render(scale=s, fill_color=(255, 255, 255, 0)).to_pil().convert("RGBA")
    height = page.get_height()
    box = (int(round(-tx / k * s)), int(round((height - ty / k) * s)), int(round((W - tx) / k * s)), int(round((height - (ty - H) / k) * s)))
    canvas = Image.new("RGBA", (max(box[2] - box[0], 1), max(box[3] - box[1], 1)), (255, 255, 255, 0))
    canvas.paste(bitmap, (-box[0], -box[1]))
    drawn = canvas.getchannel("A").getbbox()
    if drawn is None:
        return None
    out = io.BytesIO()
    canvas.crop(drawn).save(out, "PNG", optimize=True)
    cw, ch = canvas.size
    return out.getvalue(), drawn[0] / cw * W, drawn[1] / ch * H, (drawn[2] - drawn[0]) / cw * W, (drawn[3] - drawn[1]) / ch * H


def _group(layer: str, role: str, picture) -> str:
    png, x, y, w, h = picture
    return (f'<g id="{layer}" data-layer="{role}"><image x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" preserveAspectRatio="none" '
            f'href="data:image/png;base64,{base64.b64encode(png).decode("ascii")}"/></g>')


def svg_of(arch: Architecture, data: bytes, options: Options) -> Optional[str]:
    """The SVG of the plan as drawn in the PDF (the frame of the plan, origin at 0,0), one group for each layer, or None when the page cannot be tied to the plan."""
    try:
        page = pdfium.PdfDocument(data)[options.page]
        tie = fit(page_texts(page), _marks_texts(arch), max(arch.size))
        if tie is None:
            return None
        layer_of = classify(page, arch, tie)
        groups = []
        for layer, role in LAYERS:
            picture = _layer_picture(data, options.page, {i for i, l in layer_of.items() if l == layer}, tie, arch.size)
            if picture:
                groups.append(_group(layer, role, picture))
    except Exception:                                      # noqa: BLE001 - whatever the page is, the plan is still shown as the engine draws it
        return None
    W, H = arch.size
    return "\n".join([f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}" height="{H:.2f}" viewBox="0 0 {W:.2f} {H:.2f}" data-source="{arch.source}">',
                      f'<rect x="0" y="0" width="{W:.2f}" height="{H:.2f}" fill="#ffffff"/>', *groups, "</svg>", ""])
