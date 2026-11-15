"""The raceways and pipes of a drawing in three dimensions (ADR-0032, decision 7 and "Exports": simple and light geometry, the route as a sweep of its size).

Everything comes from the footprint of the drawing (`footprint.footprints`: plan points in metres, width, and the heights each element spans from the floor of the project), so the 3D
never disagrees with the plan or with the clash detection. A line (a tray, a conduit, a duct, a pipe) becomes a path at its height and a section swept along it: a rectangle (width x height)
or a circle (its width as diameter). A node (a board, a chamber, an equipment) becomes a box. A vertical element (a shaft, a riser: `vertical` in its kind) rises from its bottom to its top.

    solids(document, sheet)      -> [{"id", "tag", "kind", "discipline", "level", "layer", "shape": "run" | "box", "section": "rect" | "round", "width_m", "height_m", "path": [[x, y, z], ...]}]
    mesh(solid)                  -> {"vertices": [[x, y, z]], "faces": [[i, j, k, l]]}        # quads; what a 3D viewer or an exporter draws
    scene(solids)                -> the solids with their meshes and the box of all of them, JSON-able (the data of the 3D view of the browser)
    isometric(solids)            -> the edges of every solid projected to a 2D isometric view, in metres: a drawing for a sheet
    write_dxf_3d(solids, path)   -> a 3D DXF: each path as a 3D polyline and each solid as a mesh of faces, on the layer of its kind

Sizes are those of the kind in the profile of the discipline unless the person wrote others on the element (`ancho_m`, `alto_m`, `z_m`): nothing is calculated here.
Whether a kind is round or rectangular is data: `geom.seccion` of the kind in its profile ("round" or "rect"), else the pattern `solid.round_layers` of `params.json` on its layer.
Fittings (elbows, tees, reducers) are not generated: at a bend the two stretches simply meet.
"""
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from epc_plan import core, footprint

P3 = Tuple[float, float, float]
SECTIONS = ("round", "rect")


def _section(kind: Dict[str, Any], params: Dict[str, Any]) -> str:
    given = (kind.get("geom") or {}).get("seccion")
    if given in SECTIONS:
        return given
    return "round" if re.search(params["solid"]["round_layers"], kind.get("capa_dxf", ""), re.I) else "rect"


def _path(item: Dict[str, Any], vertical: bool) -> List[List[float]]:
    """The axis of an element: a line at the middle of its heights; a node or a vertical element from its bottom to its top."""
    if item["shape"] == "line" and not vertical:
        z = round((item["z0"] + item["z1"]) / 2, 4)
        return [[round(x, 4), round(y, 4), z] for x, y in item["points"]]
    x, y = item["points"][0]
    return [[round(x, 4), round(y, 4), item["z0"]], [round(x, 4), round(y, 4), item["z1"]]]


def _solid(item: Dict[str, Any], kind: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    vertical = bool(kind.get("vertical"))
    run = item["shape"] == "line" and not vertical
    height = round(item["z1"] - item["z0"], 4)
    return {"id": item["id"], "tag": item["tag"], "kind": item["kind"], "discipline": item["discipline"], "level": item["level"], "sheet": item["sheet"], "layer": kind.get("capa_dxf", ""),
            "shape": "run" if run else "box", "section": _section(kind, params) if run else "rect", "width_m": item["width_m"],
            "height_m": height if run else item["width_m"], "path": _path(item, vertical)}


def solids(document: Dict[str, Any], sheet: str, story_height_m: Optional[float] = None, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Every line and node of one drawing as a solid in metres (x, y of the plan with y up as in CAD, z from the floor of the project). A drawing without scale gives none; an element
    with no size (width 0) gives none either: it has no body to draw."""
    params = params or core.PARAMS
    items = footprint.footprints(document, sheet, story_height_m, params)
    if not items:
        return []
    line_kinds, node_kinds = core._kinds(core.load_profile(document.get("discipline", "")))
    kinds = {"line": line_kinds, "node": node_kinds}
    return [_solid(it, kinds[it["shape"]][it["kind"]], params) for it in items if it["width_m"] > 0 and it["z1"] > it["z0"]]


# ---------------------------------------------------------------- meshes
def _frame(a: P3, b: P3) -> Tuple[P3, P3]:
    """Two unit vectors square to the stretch a-b and to each other: `side` (horizontal when the stretch is not vertical) and `up`."""
    d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    flat = math.hypot(d[0], d[1])
    if flat < 1e-9:                                         # a vertical stretch: its section lies in the plan
        return (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
    side = (-d[1] / flat, d[0] / flat, 0.0)
    n = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
    u = (d[0] / n, d[1] / n, d[2] / n)
    up = (u[1] * side[2] - u[2] * side[1], u[2] * side[0] - u[0] * side[2], u[0] * side[1] - u[1] * side[0])
    return side, (up if up[2] >= 0 else (-up[0], -up[1], -up[2]))


def _ring(solid: Dict[str, Any], sides: int) -> List[Tuple[float, float]]:
    """The section as points (across, up) around the axis: a circle of the width as diameter, or the rectangle width x height."""
    w, h = solid["width_m"] / 2, solid["height_m"] / 2
    if solid["section"] == "round":
        return [(w * math.cos(2 * math.pi * k / sides), w * math.sin(2 * math.pi * k / sides)) for k in range(sides)]
    return [(-w, -h), (w, -h), (w, h), (-w, h)]


def _stretch(a: P3, b: P3, ring: List[Tuple[float, float]], vertices: List[List[float]], faces: List[List[int]]) -> None:
    """One straight stretch as a closed prism: its section at each end, the sides between them and the two caps."""
    side, up = _frame(a, b)
    base = len(vertices)
    n = len(ring)
    for p in (a, b):
        vertices += [[round(p[i] + s * side[i] + u * up[i], 4) for i in range(3)] for s, u in ring]
    faces += [[base + k, base + (k + 1) % n, base + n + (k + 1) % n, base + n + k] for k in range(n)]
    if n == 4:
        faces += [[base + 3, base + 2, base + 1, base], [base + 4, base + 5, base + 6, base + 7]]
    else:
        centre = len(vertices)
        vertices += [[round(c, 4) for c in a], [round(c, 4) for c in b]]
        faces += [[centre, base + (k + 1) % n, base + k, centre] for k in range(n)] + [[centre + 1, base + n + k, base + n + (k + 1) % n, centre + 1] for k in range(n)]


def mesh(solid: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The faces of a solid: one prism (or cylinder of `solid.sides` sides) per straight stretch of its path. A face is four vertex numbers (a triangle repeats its last one)."""
    sides = (params or core.PARAMS)["solid"]["sides"]
    ring = _ring(solid, sides)
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    path = [tuple(p) for p in solid["path"]]
    for a, b in zip(path, path[1:]):
        if a != b:
            _stretch(a, b, ring, vertices, faces)                    # type: ignore[arg-type]
    return {"vertices": vertices, "faces": faces}


def _box_of(points: List[List[float]]) -> Optional[List[List[float]]]:
    if not points:
        return None
    return [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]]


def scene(items: List[Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The solids with their meshes and the box that holds them all: what a 3D viewer needs, as plain data (stable order, fixed precision)."""
    done = [dict(s, mesh=mesh(s, params)) for s in items]
    return {"schema_version": "1.0", "units": "m", "solids": done, "box": _box_of([v for s in done for v in s["mesh"]["vertices"]])}


# ---------------------------------------------------------------- isometric drawing
def _iso(p: List[float]) -> List[float]:
    """A point of space on the isometric picture plane (x to the right and down, y to the right and up as it goes away, z up), in metres."""
    c, s = math.cos(math.radians(30.0)), math.sin(math.radians(30.0))
    return [round((p[0] + p[1]) * c, 4), round((p[1] - p[0]) * s + p[2], 4)]


def isometric(items: List[Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Each solid as the edges of its mesh in an isometric view: `{"id", "tag", "layer", "edges": [[[u, v], [u, v]], ...], "axis": [[u, v], ...]}` in metres, for a sheet at a scale."""
    out = []
    for s in items:
        m = mesh(s, params)
        seen = set()
        edges = []
        for f in m["faces"]:
            for a, b in zip(f, f[1:] + f[:1]):
                key = (min(a, b), max(a, b))
                if a != b and key not in seen:
                    seen.add(key)
                    edges.append([_iso(m["vertices"][a]), _iso(m["vertices"][b])])
        out.append({"id": s["id"], "tag": s["tag"], "layer": s["layer"], "edges": edges, "axis": [_iso(p) for p in s["path"]]})
    return out


# ---------------------------------------------------------------- 3D DXF
def _add_solid(msp, s: Dict[str, Any], layer, params) -> int:
    """The axis of a solid as a 3D polyline and its body as faces. Returns how many entities were added."""
    attribs = {"layer": layer(s["layer"])} if s["layer"] else {}
    msp.add_polyline3d([tuple(p) for p in s["path"]], dxfattribs=attribs)
    m = mesh(s, params)
    for f in m["faces"]:
        msp.add_3dface([tuple(m["vertices"][i]) for i in f], dxfattribs=attribs)
    return 1 + len(m["faces"])


def write_dxf_3d(items: List[Dict[str, Any]], path: Path, version: str = "", params: Dict[str, Any] = core.PARAMS, layers_file=None) -> List[str]:
    """Write the solids as a 3D DXF in metres: the axis of each as a 3D polyline and its body as a mesh of faces, on the layer of its kind (named by its role, as the 2D deliverable does).
    Returns the warnings (audit findings, read-back differences)."""
    import ezdxf
    from epc_dxf import deliverable
    from epc_plan.dxfout import _dxf_version
    doc = ezdxf.new(dxfversion=_dxf_version(params["dxf"], version), setup=True)
    doc.units = 6
    msp = doc.modelspace()
    layer = lambda base: "plan." + base                          # noqa: E731
    for base in sorted({s["layer"] for s in items if s["layer"]}):
        doc.layers.add(layer(base))
    expected = sum(_add_solid(msp, s, layer, params) for s in items)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    warnings = [f"DXF audit: {e.message}" for e in doc.audit().errors]
    deliverable.finish_draft(doc, path, layers_file)
    back = len(ezdxf.readfile(str(path)).modelspace())
    if back != expected:
        warnings.append(f"DXF read back has {back} entities, expected {expected}")
    return warnings
