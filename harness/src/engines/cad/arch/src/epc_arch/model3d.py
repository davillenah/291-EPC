"""The building in three dimensions, from the plan of each floor and the heights the person gives (ADR-0032: the 3D is drawn from the same model as the plans; nothing is guessed).

A wall is a box of its thickness and the height of the floor, left open where it has a door (the wall goes on above the door head) or a window (under the sill and above the head, with the
glass between). Each floor has its slab under it and the slab above. Rooms are thin plates on the floor, so a viewer can name and tint them.

    building_solids(arch, heights) -> [{"id", "tag", "kind": wall | slab | glass | room, "discipline": "arquitectura", "level", "layer", "mesh": {"vertices", "faces"}}]
    building_scene([(arch, heights), ...]) -> {"schema_version", "units": "m", "solids": [...], "box": [[x, y, z], [x, y, z]]}

The scene is the same plain data `epc_plan.solid.scene` gives for the raceways and pipes (quads by vertex number), in the same frame: metres, x to the right of the plan, y up as in CAD
(the plan's y turned over, as the DXF of the services does with its backdrop), z from the level of the project (`elevation_m` of each floor). So both are shown together with no conversion.
The heights are those of `epc_arch.sections` (`heights_errors`). Limits: walls along the two directions of the plan; one height per floor; the slab is the box of the floor."""
from typing import Any, Dict, List, Optional, Tuple

from epc_arch.model import Architecture, Level, Opening, Wall
from epc_arch.sections import _W, _checked, _cut_pieces, _minus, _plan_in_metres

LAYERS = {"wall": "A-WALL-CUT", "slab": "A-WALL-FILL", "glass": "A-WINDOW-GLASS", "room": "A-ROOM"}
ROOM_PLATE = 0.01                          # metres: the thickness of the plate that marks a room on the floor
Box = Tuple[float, float, float, float, float, float]      # x0, y0, z0, x1, y1, z1 in the plan frame (y down)


def box_mesh(box: Box) -> Dict[str, Any]:
    """The eight corners and six faces of a box, in the frame of the scene (y up: the plan's y with its sign changed)."""
    x0, y0, z0, x1, y1, z1 = box
    ya, yb = -y1, -y0
    v = [[round(x, 4), round(y, 4), round(z, 4)] for z in (z0, z1) for x, y in ((x0, ya), (x1, ya), (x1, yb), (x0, yb))]
    return {"vertices": v, "faces": [[3, 2, 1, 0], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]}


def _wall_box(w: _W, a: float, b: float, z0: float, z1: float) -> Box:
    """The box of a stretch `a`..`b` of a wall between two heights."""
    if w.along == "x":
        return (a, w.pos - w.t / 2, z0, b, w.pos + w.t / 2, z1)
    return (w.pos - w.t / 2, a, z0, w.pos + w.t / 2, b, z1)


def _wall_boxes(w: _W, gaps: List[Tuple[str, float, float]], h: Dict[str, float]) -> List[Tuple[str, Box]]:
    """A wall as boxes: its solid stretches whole, and at each opening what is left of the wall above (and, for a window, under) it, with the glass of a window."""
    H = h["wall_height_m"]
    out = [("wall", _wall_box(w, a, b, 0.0, H)) for a, b in _minus([(w.a, w.b)], [(g0, g1) for _, g0, g1 in gaps])]
    for kind, g0, g1 in gaps:
        out += [("wall", _wall_box(w, g0, g1, z0, z1)) for z0, z1 in _cut_pieces(kind, h) if z1 - z0 > 1e-6]
        if kind == "window":
            thin = _W(w.id, w.along, w.pos, w.a, w.b, min(w.t, 0.02))
            out.append(("glass", _wall_box(thin, g0, g1, h["window_sill_m"], h["window_head_m"])))
    return out


def _extent(walls: List[_W]) -> Tuple[float, float, float, float]:
    xs = [v for w in walls for v in ((w.a, w.b) if w.along == "x" else (w.pos - w.t / 2, w.pos + w.t / 2))]
    ys = [v for w in walls for v in ((w.a, w.b) if w.along == "y" else (w.pos - w.t / 2, w.pos + w.t / 2))]
    return min(xs), min(ys), max(xs), max(ys)


def _solid(ident: str, tag: str, kind: str, level: str, box: Box, base: float) -> Dict[str, Any]:
    x0, y0, z0, x1, y1, z1 = box
    return {"id": ident, "tag": tag, "kind": kind, "discipline": "arquitectura", "level": level, "layer": LAYERS[kind], "mesh": box_mesh((x0, y0, z0 + base, x1, y1, z1 + base))}


def _rooms(arch: Architecture, k: float, level: str, base: float) -> List[Dict[str, Any]]:
    out = []
    for r in arch.rooms:
        for n, (x0, y0, x1, y1) in enumerate(r.rects, 1):
            out.append(_solid(f"{level}:{r.id}:{n}", r.code or r.name or r.id, "room", level, (x0 * k, y0 * k, 0.0, x1 * k, y1 * k, ROOM_PLATE), base))
    return out


def building_solids(arch: Architecture, heights: Dict[str, float]) -> List[Dict[str, Any]]:
    """The walls (open at their doors and windows), the glass of the windows, the two slabs and the rooms of one floor, as solids with their mesh. An `ArchError` when the heights are
    not valid or the plan does not know its units."""
    k = _checked(arch, heights)
    walls, gaps = _plan_in_metres(arch, k, [])
    level = arch.level.name if arch.level else ""
    base, H, slab = heights["elevation_m"], heights["wall_height_m"], heights["slab_m"]
    out = []
    for w in walls:
        for n, (kind, box) in enumerate(_wall_boxes(w, gaps.get(w.id, []), heights), 1):
            out.append(_solid(f"{level}:{w.id}:{n}", w.id, kind, level, box, base))
    x0, y0, x1, y1 = _extent(walls)
    out.append(_solid(f"{level}:slab:floor", "slab", "slab", level, (x0, y0, -slab, x1, y1, 0.0), base))
    out.append(_solid(f"{level}:slab:top", "slab", "slab", level, (x0, y0, H, x1, y1, H + slab), base))
    return out + _rooms(arch, k, level, base)


def from_backdrop(backdrop: Dict[str, Any], level: str = "") -> Architecture:
    """An architecture from the walls (`{a, b, thickness_m}`) and openings (`{kind, at, width_m, angle}`) of a floor given in metres of its plan (what the platform keeps of a recognised
    floor): enough for its sections and its 3D. Rooms are not carried (they have no floor here)."""
    walls = [Wall(f"w{i}", tuple(w["a"]), tuple(w["b"]), w["thickness_m"], 1.0, "given") for i, w in enumerate(backdrop.get("walls", []), 1)]
    openings = [Opening(f"o{i}", o["kind"], tuple(o["at"]), o["width_m"], o["angle"], "", 1.0, "given") for i, o in enumerate(backdrop.get("openings", []), 1)]
    size = (max((c for w in walls for c in (w.a[0], w.b[0])), default=0.0), max((c for w in walls for c in (w.a[1], w.b[1])), default=0.0))
    thickness = max((w.thickness for w in walls), default=None)
    return Architecture(source=level, size=size, units_per_metre=1.0, scale_hint=None, wall_thickness=thickness, walls=walls, openings=openings,
                        level=Level(level, None, "text") if level else None)


def _box_of(solids: List[Dict[str, Any]]) -> Optional[List[List[float]]]:
    points = [v for s in solids for v in s["mesh"]["vertices"]]
    if not points:
        return None
    return [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]]


def building_scene(floors: List[Tuple[Architecture, Dict[str, float]]]) -> Dict[str, Any]:
    """The floors of a building as one scene (each at its `elevation_m`). The floors must share one frame, as the plans of one sheet do."""
    solids = [s for arch, heights in floors for s in building_solids(arch, heights)]
    return {"schema_version": "1.0", "units": "m", "solids": solids, "box": _box_of(solids)}
