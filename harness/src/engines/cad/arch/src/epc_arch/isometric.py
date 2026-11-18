"""The isometric view of a building: every floor as solids (`epc_arch.model3d`, the same model as the plans, the sections and the 3D), seen from the south-east and from above, on an IRAM sheet.

True length along the three axes (the conventional isometric drawing), so the graphic scale of the sheet is valid along them. The roof of the top floor is left out (a cutaway, so that the rooms are seen). The faces are painted from the farthest to the nearest and only
those that face the viewer are drawn: there is no hidden-line removal beyond that. The shades and the width of the lines come from `epc_style.json` (`presentation`).
    isometric_drawing([(arch, heights, (dx_m, dy_m)), ...]) -> Drawing       # the offset puts the floors of one building in one frame (metres)
"""
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from epc_arch import drawing as D
from epc_arch.drawing import Drawing, Poly, TextItem
from epc_arch.model import ArchError, Architecture
from epc_arch.model3d import LAYERS, building_solids
from epc_arch.presentation import settings

VIEWER = (1.0, -1.0, 1.0)                  # towards the viewer: east, south and up (the scene's y is the north)
PAINT_ORDER = {"slab": 0, "room": 1, "wall": 2, "glass": 3}
LINE_MM = 0.18
Vec = Tuple[float, float, float]


def _sub(a: Sequence[float], b: Sequence[float]) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _centre(points: Sequence[Sequence[float]]) -> Vec:
    n = float(len(points))
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n, sum(p[2] for p in points) / n)


def _shifted(solid: Dict[str, Any], offset: Tuple[float, float]) -> List[List[float]]:
    return [[v[0] + offset[0], v[1] + offset[1], v[2]] for v in solid["mesh"]["vertices"]]


def _shade(n: Vec, kind: str, fills: Dict[str, str]) -> str:
    """The grey of a face: its own for glass, rooms and slabs; walls are lighter on top, mid on the south side and darker on the east side."""
    if kind in ("glass", "room", "slab"):
        return fills[kind]
    return fills["wall_lit"] if n[2] > 0.5 else fills["wall"] if n[1] < -0.5 else fills["wall_dark"]


def _faces(solid: Dict[str, Any], offset: Tuple[float, float], fills: Dict[str, str]) -> List[Tuple[Tuple[float, int], List[Vec], str, str]]:
    """The faces of a solid that look towards the viewer: (sort key, corners, fill, layer)."""
    verts = _shifted(solid, offset)
    middle = _centre(verts)
    out = []
    for face in solid["mesh"]["faces"]:
        pts = [verts[i] for i in face]
        n = _cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[0]))
        c = _centre(pts)
        n = n if _dot(n, _sub(c, middle)) >= 0 else (-n[0], -n[1], -n[2])
        length = math.sqrt(_dot(n, n)) or 1.0
        n = (n[0] / length, n[1] / length, n[2] / length)
        if _dot(n, VIEWER) > 1e-9:
            out.append(((_dot(c, VIEWER), PAINT_ORDER[solid["kind"]]), pts, _shade(n, solid["kind"], fills), solid["layer"]))
    return out


def _project(p: Sequence[float], angle: float) -> Tuple[float, float]:
    """Metres of the scene to metres on the screen (x to the right, up): the east to the lower right, the north to the upper right, the height straight up."""
    return ((p[0] + p[1]) * math.cos(math.radians(angle)), p[2] + (p[1] - p[0]) * math.sin(math.radians(angle)))


def _paper(box: Tuple[float, float, float, float], free, scale: int):
    cx, cy = (free[0] + free[2]) / 2, (free[1] + free[3]) / 2
    k = 1000.0 / scale
    mid = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    return lambda s: (cx + (s[0] - mid[0]) * k, cy - (s[1] - mid[1]) * k)           # noqa: E731


def _level_labels(floors, per_floor, at, angle: float, right: float) -> List[object]:
    """The name and level of each floor, at the right of the view, at the height of that floor on the screen."""
    out = []
    for (arch, heights, off), faces in zip(floors, per_floor):
        ys = [_project(v, angle)[1] for f in faces for v in f[1]]
        x, y = at((right, (min(ys) + max(ys)) / 2))
        out.append(TextItem(f"{arch.level.name if arch.level else '-'}  +{heights['elevation_m']:.2f} m", (x + 4.0, y), "TXT_25", "A-ANNO", bold=True))
    return out


def isometric_drawing(floors: List[Tuple[Architecture, Dict[str, float], Tuple[float, float]]], style=None, sheet: Optional[str] = None, scale: Optional[int] = None, template=None,
                      fields: Optional[dict] = None, title: str = "ISOMÉTRICO / ISOMETRIC") -> Drawing:
    """The building as an isometric view on a sheet, at the smallest standard scale denominator that fits it unless `scale` is given."""
    if not floors:
        raise ArchError("no floors to draw")
    style = style or D.load_style()
    p = settings()
    angle = float(p["iso_angle_deg"])
    top = max(h["elevation_m"] for _, h, _ in floors)
    per_floor = [[f for s in building_solids(arch, heights) if not (heights["elevation_m"] == top and s["id"].endswith(":slab:top")) for f in _faces(s, off, p["iso_fill"])] for arch, heights, off in floors]
    faces = sorted((f for fs in per_floor for f in fs), key=lambda f: f[0])
    pts = [_project(v, angle) for f in faces for v in f[1]]
    box = (min(q[0] for q in pts), min(q[1] for q in pts), max(q[0] for q in pts), max(q[1] for q in pts))
    name, size, free = D._sheet_of(style, sheet, template)
    d = Drawing(name, size, 0)
    area = (free[0], free[1] + 4.0, free[2] - p["panel_mm"] / 2, free[3] - 12.0)
    d.scale, changed = D._scale_for(((box[2] - box[0]) * 1000.0, (box[3] - box[1]) * 1000.0), (area[2] - area[0], area[3] - area[1]), scale or style.sheet["scales"][0], style)
    if changed and scale:
        d.warnings.append(f"the view does not fit sheet {d.sheet} at the requested scale: drawn at 1:{d.scale}")
    at = _paper(box, area, d.scale)
    for _, corners, fill, layer in faces:
        d.items.append(Poly(tuple(at(_project(v, angle)) for v in corners), layer, closed=True, fill=fill, width=LINE_MM))
    d.items += _level_labels(floors, per_floor, at, angle, box[2])
    d.title, d.document = title, floors[0][0].source
    d.warnings.append("isometric view: true length along the axes / vista isométrica: longitudes reales sobre los ejes")
    D._frame_the_sheet(d, floors[0][0], style, free, template, dict({"denominacion": title}, **(fields or {})))
    return d
