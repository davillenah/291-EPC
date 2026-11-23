"""The 3D scene of a project: the building and the services of every discipline together, its files, and the sections cut through all of it.

A scene is plain data (`{"schema_version", "units": "m", "solids": [{"id", "tag", "kind", "discipline", "level", "layer", "mesh": {"vertices", "faces"}}], "box"}`): `epc_plan.solid.scene`
gives the raceways and pipes of a drawing, `epc_arch.model3d.building_scene` the building. This module knows only that data (it imports no other engine):

    merge(scenes)                 -> one scene with the solids of all of them
    groups(scene)                 -> one entry per discipline and layer, with how many solids
    write_obj(scene, path)        -> a Wavefront OBJ (with its groups), which every 3D program opens
    write_dxf(scene, path)        -> a 3D DXF: every face as a 3DFACE on the layer of its solid (the model, to look at in CAD)
    cut(scene, axis, at_m, look)  -> the section of everything by a vertical plane: what the plane cuts, exactly (a tray is its rectangle, a conduit its circle, a wall its thickness), each with
                                     its tag and the level of its middle, and the edges of what lies beyond, up to `depth_m`
    write_section_dxf(section, path) -> that section as a 2D DXF in real metres, to detail at any scale: cut outlines closed and filled, on the layer of each solid, what is beyond as lines,
                                     and the tag and level of every cut service

There is no screen here: the outputs are files for CAD. A section shows what the model holds, with its real sizes and heights. It is as detailed as the model: supports, fixings and
fittings (elbows, tees) are not modelled yet, so a section is the base of a fabrication detail (LOD 400), not the finished detail.
"""
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from epc_plan import core
from epc_plan.core import PlanError

def _box_of(solids: List[Dict[str, Any]]) -> Optional[List[List[float]]]:
    points = [v for s in solids for v in s["mesh"]["vertices"]]
    if not points:
        return None
    return [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]]


def check(scene: Any) -> None:
    """Raises `core.PlanError` when the data is not a scene this module can show."""
    if not isinstance(scene, dict) or scene.get("schema_version") != "1.0" or not isinstance(scene.get("solids"), list):
        raise core.PlanError("err_scene_shape")
    for s in scene["solids"]:
        mesh = s.get("mesh") if isinstance(s, dict) else None
        if not isinstance(mesh, dict) or not isinstance(mesh.get("vertices"), list) or not isinstance(mesh.get("faces"), list):
            raise core.PlanError("err_solid_no_mesh")
        if any(not 0 <= i < len(mesh["vertices"]) for f in mesh["faces"] for i in f):
            raise core.PlanError("err_face_vertex", solid=s.get('id'))


def merge(scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The solids of several scenes (the building, each discipline, each floor) as one scene, in the order given."""
    for sc in scenes:
        check(sc)
    solids = [s for sc in scenes for s in sc["solids"]]
    return {"schema_version": "1.0", "units": "m", "solids": solids, "box": _box_of(solids)}


def group_of(solid: Dict[str, Any]) -> str:
    return f"{solid.get('discipline') or '-'} / {solid.get('layer') or solid.get('kind') or '-'}"


def groups(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One entry per discipline and layer, in the order they first appear: `{"group", "discipline", "layer", "solids", "color", "opacity"}`."""
    check(scene)
    look = core.PARAMS["scene"]
    out: Dict[str, Dict[str, Any]] = {}
    for s in scene["solids"]:
        g = group_of(s)
        if g not in out:
            color = look["layer_colors"].get(s.get("layer", ""), look["discipline_colors"].get(s.get("discipline", ""), look["default_color"]))
            out[g] = {"group": g, "discipline": s.get("discipline", ""), "layer": s.get("layer", ""), "solids": 0, "color": color, "opacity": look["layer_opacity"].get(s.get("layer", ""), 1.0)}
        out[g]["solids"] += 1
    return list(out.values())


# ---------------------------------------------------------------- files
def write_obj(scene: Dict[str, Any], path: Path) -> int:
    """A Wavefront OBJ of the scene in metres (z up): one object per solid, grouped by discipline and layer. Returns how many faces were written."""
    check(scene)
    lines = ["# EPC-291 3D scene, metres, z up"]
    offset, faces = 1, 0
    for s in scene["solids"]:
        lines += [f"o {s.get('tag') or s.get('id')}", f"g {group_of(s).replace(' / ', '_').replace(' ', '_')}"]
        lines += [f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}" for v in s["mesh"]["vertices"]]
        for f in s["mesh"]["faces"]:
            ids = [i for n, i in enumerate(f) if n == 0 or i != f[n - 1]]          # a triangle repeats its last vertex
            lines.append("f " + " ".join(str(i + offset) for i in ids))
            faces += 1
        offset += len(s["mesh"]["vertices"])
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return faces


def _save(doc, path: Path, stamp_date: Optional[str]) -> None:
    """Save a DXF as the other deliverables are saved: with `stamp_date` (an ISO date) the file carries that date and identifiers derived from it, so the same model gives the same bytes."""
    from epc_dxf import deliverable
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    deliverable.finish_draft(doc, path, None, stamp_date)


def write_dxf(scene: Dict[str, Any], path: Path, version: str = "", params: Dict[str, Any] = core.PARAMS, stamp_date: Optional[str] = None) -> int:
    """A 3D DXF of the scene in metres: every face as a 3DFACE on the layer of its solid. Returns how many faces were written."""
    import ezdxf
    from epc_dxf import new_document
    from epc_plan.dxfout import _dxf_version
    check(scene)
    doc = new_document(_dxf_version(params["dxf"], version), setup=True)
    doc.units = 6
    msp = doc.modelspace()
    faces = 0
    for s in scene["solids"]:
        layer = s.get("layer") or "0"
        if layer not in doc.layers:
            doc.layers.add(layer)
        for f in s["mesh"]["faces"]:
            msp.add_3dface([tuple(s["mesh"]["vertices"][i]) for i in f], dxfattribs={"layer": layer})
            faces += 1
    _save(doc, path, stamp_date)
    return faces


# ---------------------------------------------------------------- sections through everything
LOOKS = ("+", "-")
EPS = 1e-7


def _plane_frame(axis: str, look: str):
    """For a vertical plane on `axis` seen towards `look`: the index of the axis, the index of the other horizontal axis and the sign that turns it into `u` (left to right for the viewer)."""
    if axis not in ("x", "y") or look not in LOOKS:
        raise core.PlanError("err_section_plane")
    i = 0 if axis == "x" else 1
    sign = 1.0 if (axis == "y") == (look == "+") else -1.0
    return i, 1 - i, sign


def _crossing(a, b, i: int, at: float):
    """Where the edge a-b meets the plane (None when it does not cross it)."""
    da, db = a[i] - at, b[i] - at
    if (da > EPS and db > EPS) or (da < -EPS and db < -EPS) or abs(da - db) < EPS:
        return None
    t = da / (da - db)
    return [a[k] + (b[k] - a[k]) * t for k in range(3)]


def _face_segment(points, i: int, at: float):
    """The stretch of a face that lies in the plane: its two crossing points (None when the face does not cross it)."""
    hits: List[List[float]] = []
    for a, b in zip(points, points[1:] + points[:1]):
        p = _crossing(a, b, i, at) if a != b else None
        if p is not None and not any(math.dist(p, q) < 1e-6 for q in hits):
            hits.append(p)
    return hits[:2] if len(hits) >= 2 else None


def _grow(loop: List[List[float]], left: List[List[List[float]]]) -> bool:
    """Add to the outline the segment that starts where it ends. False when none does."""
    for n, (a, b) in enumerate(left):
        at_a, at_b = math.dist(loop[-1], a) < 1e-5, math.dist(loop[-1], b) < 1e-5
        if at_a or at_b:
            loop.append(b if at_a else a)
            left.pop(n)
            return True
    return False


def _loops(segments: List[List[List[float]]]) -> List[List[List[float]]]:
    """Segments joined end to end into outlines (a convex solid gives one closed outline)."""
    left = [list(s) for s in segments]
    loops = []
    while left:
        loop = left.pop()
        while _grow(loop, left):
            pass
        loops.append(loop[:-1] if len(loop) > 2 and math.dist(loop[0], loop[-1]) < 1e-5 else loop)
    return loops


def _cut_loops(mesh: Dict[str, Any], i: int, j: int, sign: float, at: float) -> List[List[List[float]]]:
    """The outlines the plane cuts out of a mesh, as (u, z) points."""
    v = mesh["vertices"]
    segs = [seg for f in mesh["faces"] for seg in [_face_segment([v[k] for k in f], i, at)] if seg]
    flat = [[[round(p[j] * sign, 4), round(p[2], 4)] for p in seg] for seg in segs]
    return [loop for loop in _loops(flat) if len(loop) >= 3]


def _described(s: Dict[str, Any]) -> Dict[str, Any]:
    return {key: s.get(key, "") for key in ("id", "tag", "kind", "discipline", "layer")}


def _box2(points: List[List[float]]) -> Optional[List[float]]:
    if not points:
        return None
    return [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]


def _reaches(mesh: Dict[str, Any], i: int, at: float) -> bool:
    """Does the plane pass through the box of the mesh? Most solids of a project are far from any one plane: they are left out before their faces are looked at."""
    values = [v[i] for v in mesh["vertices"]]
    return bool(values) and min(values) - EPS <= at <= max(values) + EPS


def _measured(loops: List[List[List[float]]]) -> Dict[str, Any]:
    """What a cut outline measures: its middle, the levels of its bottom and its top and its size as it is ordered (a diameter for a round one, width by height for the rest), in millimetres."""
    us, zs = [p[0] for loop in loops for p in loop], [p[1] for loop in loops for p in loop]
    centre = [round(sum(us) / len(us), 4), round(sum(zs) / len(zs), 4)]
    width, height = round(max(us) - min(us), 4), round(max(zs) - min(zs), 4)
    is_round = len(loops[0]) > 4 and abs(width - height) < 1e-3
    size = f"D{round(width * 1000)}" if is_round else f"{round(width * 1000)}x{round(height * 1000)}"
    return {"centre": centre, "level_m": centre[1], "bottom_m": round(min(zs), 4), "top_m": round(max(zs), 4), "size": size}


def _cut_solid(s: Dict[str, Any], i: int, j: int, sign: float, at: float) -> Optional[Dict[str, Any]]:
    loops = _cut_loops(s["mesh"], i, j, sign, at) if _reaches(s["mesh"], i, at) else []
    if not loops:
        return None
    return dict(_described(s), loops=loops, **_measured(loops))


def _beyond(p, i: int, at: float, direction: float, depth: Optional[float]) -> bool:
    d = (p[i] - at) * direction
    return d > EPS and (depth is None or d <= depth)


def _edges(mesh: Dict[str, Any]) -> List[Tuple[int, int]]:
    """Every edge of a mesh once, by its two vertex numbers."""
    done = set()
    for f in mesh["faces"]:
        done |= {(min(a, b), max(a, b)) for a, b in zip(f, f[1:] + f[:1]) if a != b}
    return sorted(done)


def _seen_solid(s: Dict[str, Any], i: int, j: int, sign: float, at: float, direction: float, depth: Optional[float]) -> Optional[Dict[str, Any]]:
    """The edges of a solid that lie wholly beyond the plane (within the depth), projected on it. Nothing is hidden: what is behind the cut is read as a wireframe."""
    v = s["mesh"]["vertices"]
    edges: List[List[List[float]]] = []
    for a, b in _edges(s["mesh"]):
        if _beyond(v[a], i, at, direction, depth) and _beyond(v[b], i, at, direction, depth):
            e = sorted([[round(v[a][j] * sign, 4), round(v[a][2], 4)], [round(v[b][j] * sign, 4), round(v[b][2], 4)]])
            if e[0] != e[1] and e not in edges:
                edges.append(e)
    return {"id": s.get("id", ""), "tag": s.get("tag", ""), "discipline": s.get("discipline", ""), "layer": s.get("layer", ""), "edges": edges} if edges else None


def _points_of(cuts: List[Dict[str, Any]], seen: List[Dict[str, Any]]) -> List[List[float]]:
    """Every point a section draws: those of its cut outlines and those of the edges seen beyond."""
    return [p for c in cuts for loop in c["loops"] for p in loop] + [p for e in seen for edge in e["edges"] for p in edge]


def cut(scene: Dict[str, Any], axis: str, at_m: float, look: str = "+", depth_m: Optional[float] = None) -> Dict[str, Any]:
    """The section of the whole scene by the vertical plane `axis` = `at_m` (metres of the scene), seen towards `look` (+ or - of that axis), with what lies up to `depth_m` beyond it
    (everything when None). `{"cut": [...], "seen": [...], "box": [u0, z0, u1, z1]}` in metres: `u` to the right, `z` up."""
    check(scene)
    if not isinstance(at_m, (int, float)) or isinstance(at_m, bool):
        raise core.PlanError("err_section_position")
    i, j, sign = _plane_frame(axis, look)
    direction = 1.0 if look == "+" else -1.0
    cuts = list(filter(None, (_cut_solid(s, i, j, sign, at_m) for s in scene["solids"])))
    seen = list(filter(None, (_seen_solid(s, i, j, sign, at_m, direction, depth_m) for s in scene["solids"])))
    box = _box2(_points_of(cuts, seen))
    return {"schema_version": "1.0", "kind": "section", "units": "m", "plane": {"axis": axis, "at_m": at_m, "look": look, "depth_m": depth_m}, "cut": cuts, "seen": seen, "box": box}


def _layer(doc, name: str) -> str:
    name = name or "0"
    if name not in doc.layers:
        doc.layers.add(name)
    return name


def _is_service(c: Dict[str, Any]) -> bool:
    """A cut element that carries a tag worth writing: anything but the building itself."""
    return bool(c["tag"]) and c["discipline"] != "arquitectura"


def _add_seen(doc, msp, section: Dict[str, Any]) -> int:
    n = 0
    for e in section["seen"]:
        layer = _layer(doc, e["layer"])
        for a, b in e["edges"]:
            msp.add_line(a, b, dxfattribs={"layer": layer})
            n += 1
    return n


def _add_cut(doc, msp, c: Dict[str, Any], params: Dict[str, Any]) -> Tuple[int, int]:
    """The outlines of one cut element, closed and filled, and its tag with its level when it is a service. Returns (outlines, tags)."""
    import ezdxf
    layer = _layer(doc, c["layer"])
    for loop in c["loops"]:
        msp.add_lwpolyline(loop, close=True, dxfattribs={"layer": layer})
        msp.add_hatch(dxfattribs={"layer": layer}).paths.add_polyline_path(loop, is_closed=True)
    if not _is_service(c):
        return len(c["loops"]), 0
    height = params["scene"]["detail_text_m"]
    top = max(p[1] for loop in c["loops"] for p in loop)
    text = msp.add_text(f"{c['tag']} {c['size']} {c['level_m']:+.2f} (BOT {c['bottom_m']:+.2f})", height=height, dxfattribs={"layer": _layer(doc, params["dxf"]["tag_layer"])})
    text.set_placement((c["centre"][0], top + height / 2), align=ezdxf.enums.TextEntityAlignment.BOTTOM_CENTER)
    return len(c["loops"]), 1


def dimension_points(section: Dict[str, Any]) -> List[float]:
    """The places a chain of dimensions across a section measures between: the two ends of what the building is cut at (when it is) and the middle of every cut service, left to right."""
    services = [c["centre"][0] for c in section["cut"] if _is_service(c)]
    walls = [p[0] for c in section["cut"] if not _is_service(c) for loop in c["loops"] for p in loop]
    ends = [min(walls), max(walls)] if walls and services else []
    return sorted({round(u, 3) for u in services + ends})


def _add_dimensions(doc, msp, section: Dict[str, Any], params: Dict[str, Any]) -> int:
    """A chain of horizontal dimensions over the section, between the places of `dimension_points`. Returns how many were drawn."""
    points = dimension_points(section)
    if len(points) < 2 or not section.get("box"):
        return 0
    h = params["scene"]["detail_text_m"]
    y = section["box"][3] + 6 * h
    look = {"dimtxt": h, "dimasz": h, "dimexe": h / 2, "dimexo": h / 2, "dimgap": h / 4, "dimdec": 2}
    layer = _layer(doc, params["dxf"]["dimension_layer"])
    for a, b in zip(points, points[1:]):
        msp.add_linear_dim(base=(a, y), p1=(a, section["box"][3]), p2=(b, section["box"][3]), dimstyle="EZDXF", override=look, dxfattribs={"layer": layer}).render()
    return len(points) - 1


def write_section_dxf(section: Dict[str, Any], path: Path, version: str = "", params: Dict[str, Any] = core.PARAMS, stamp_date: Optional[str] = None) -> Dict[str, int]:
    """The section as a 2D DXF in real metres: each cut outline closed and filled on the layer of its solid, what is beyond as lines on the same layers, and by every cut service its tag, its
    size, the level of its middle and the one of its bottom ("BN-001 300x100 +2.60 (BOT +2.55)"), and over it all a chain of dimensions between the services and the ends of the building.
    Returns how many outlines, lines, tags and dimensions were written."""
    import ezdxf
    from epc_dxf import new_document
    from epc_plan.dxfout import _dxf_version
    if not isinstance(section, dict) or section.get("kind") != "section":
        raise core.PlanError("err_section_not_cut")
    doc = new_document(_dxf_version(params["dxf"], version), setup=True)
    doc.units = 6
    msp = doc.modelspace()
    count = {"outlines": 0, "lines": _add_seen(doc, msp, section), "tags": 0, "dimensions": _add_dimensions(doc, msp, section, params)}
    for c in section["cut"]:
        outlines, tags = _add_cut(doc, msp, c, params)
        count["outlines"] += outlines
        count["tags"] += tags
    _save(doc, path, stamp_date)
    return count
