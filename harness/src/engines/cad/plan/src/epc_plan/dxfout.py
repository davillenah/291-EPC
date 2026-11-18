"""The DXF deliverable, written from the result of `core.process` with ezdxf (MIT). It is never converted from the SVG of the screen: both come from the same model.

Real units: metres or millimetres, as the discipline says. One layer per kind of element, one block per symbol used, real text for the tags.
"""
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import ezdxf
from epc_dxf import deliverable

from epc_plan import core

_UNITS = {"m": (6, 1.0), "mm": (4, 1000.0)}          # DXF $INSUNITS code and the factor from metres


def versions(params: Dict[str, Any] = core.PARAMS) -> List[str]:
    return list(params["dxf"]["versions"])


def _symbol_prims(symbol_id: str, size: float, scale: float) -> List[Dict[str, Any]]:
    out = []
    for p in core.SYMBOLS[symbol_id]["prims"]:
        if p["t"] == "rect":
            w, h = p["w"] * size * scale / 2, p["h"] * size * scale / 2
            out.append({"t": "poly", "pts": [(-w, -h), (w, -h), (w, h), (-w, h)]})
        elif p["t"] == "line":
            out.append({"t": "line", "a": tuple(c * size * scale for c in p["a"]), "b": tuple(c * size * scale for c in p["b"])})
        elif p["t"] == "circle":
            out.append({"t": "circle", "r": p["r"] * size * scale})
    return out


def _define_block(doc, sid: str, size: float, scale: float, height: float) -> str:
    """The block of a symbol (one per symbol used), with an attribute that holds the tag. Returns its name."""
    name = f"SYM_{sid.upper()}"
    if name in doc.blocks:
        return name
    blk = doc.blocks.new(name=name)
    for p in _symbol_prims(sid, size, scale):
        if p["t"] == "poly":
            blk.add_lwpolyline(p["pts"], close=True)
        elif p["t"] == "line":
            blk.add_line(p["a"], p["b"])
        else:
            blk.add_circle((0, 0), p["r"])
    blk.add_attdef("TAG", (size * scale * 0.6, size * scale * 0.6), height=height)
    return name


def _turn(n: Dict[str, Any]) -> Dict[str, float]:
    """The turn of a symbol (`rot_deg` on the node, clockwise on the screen) as the rotation of its block, counter-clockwise as CAD counts it."""
    rot = (n.get("attrs") or {}).get("rot_deg")
    return {"rotation": -float(rot)} if isinstance(rot, (int, float)) and not isinstance(rot, bool) and rot else {}


def _add_nodes(doc, msp, result, node_kinds, cfg, scale: float, height: float, layer) -> int:
    """Placed nodes as block insertions with their tag, junctions as small circles. Returns how many entities were added."""
    count = 0
    for n in result["nodes"]:
        at = (n["x_m"] * scale, n["y_m"] * scale)
        if n["placed"]:
            kind = node_kinds[n["kind"]]
            block = _define_block(doc, kind["simbolo_2d"], cfg["node_symbol_size_m"], scale, height)
            msp.add_blockref(block, at, dxfattribs={"layer": layer(kind["capa_dxf"]), **_turn(n)}).add_auto_attribs({"TAG": n["tag"]})
            count += 1
        elif n["kind"] == "J":
            msp.add_circle(at, 0.05 * scale, dxfattribs={"layer": layer(cfg["junction_layer"])})
            count += 1
    return count


def _label_position(pts):
    """Middle of a polyline (by vertex count) and the angle of its ends, turned so the text is never upside down."""
    half = len(pts) // 2
    mid = pts[half] if len(pts) % 2 else ((pts[half - 1][0] + pts[half][0]) / 2, (pts[half - 1][1] + pts[half][1]) / 2)
    a, b = pts[0], pts[-1]
    angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    return mid, angle + 180 if (angle > 90 or angle < -90) else angle


def _carried(s) -> str:
    """The first circuits a stretch carries and how many more: '[A, B +2]', empty when it carries none."""
    names = [c["circuit"] for c in s.get("carries") or []]
    return f" [{', '.join(names[:2])}{f' +{len(names) - 2}' if len(names) > 2 else ''}]" if names else ""


def _label(s, room: float, height: float) -> str:
    """The text of a stretch label: its tag with the circuits it carries when that fits in the `room` of the stretch, else the tag alone, else nothing: a longer text would run over the next one."""
    return next((t for t in (s["tag"] + _carried(s), s["tag"]) if len(t) * 0.62 * height <= room), "")


def _stacked(mid, angle, height, seen):
    """The place of a label that does not sit on one already written: the labels of stretches that share a line are put one above the other, across the line."""
    key = (round(mid[0] / (4 * height)), round(mid[1] / (4 * height)))
    n = seen[key] = seen.get(key, -1) + 1
    rad = math.radians(angle + 90)
    return (mid[0] + math.cos(rad) * n * 1.4 * height, mid[1] + math.sin(rad) * n * 1.4 * height)


def _add_label(msp, s, pts, height, cfg, layer, seen) -> int:
    """Write the label of a stretch when it fits; returns the entities added (0 or 1)."""
    text = _label(s, sum(math.dist(p, q) for p, q in zip(pts, pts[1:])), height)
    if not text:
        return 0
    mid, angle = _label_position(pts)
    msp.add_text(text, height=height, rotation=angle, dxfattribs={"layer": layer(cfg["tag_layer"])}).set_placement(_stacked(mid, angle, height, seen), align=ezdxf.enums.TextEntityAlignment.BOTTOM_CENTER)
    return 1


def _add_stretches(msp, result, line_kinds, cfg, scale: float, height: float, layer) -> int:
    seen: Dict[Any, int] = {}
    count = 0
    for s in result["stretches"]:
        pts = [(x * scale, y * scale) for x, y in s["points_m"]]
        msp.add_lwpolyline(pts, dxfattribs={"layer": layer(line_kinds[s["kind"]]["capa_dxf"])})
        count += 1 + _add_label(msp, s, pts, height, cfg, layer, seen)
    return count


def _wall_corners(a, b, thickness: float):
    """The four corners of a wall (its axis a-b and its thickness, all in metres)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return None
    nx, ny = -dy / length * thickness / 2, dx / length * thickness / 2
    return [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)]


def _add_backdrop(doc, msp, backdrop: Dict[str, Any], cfg, scale: float, height: float, layer) -> int:
    """The building under the services, from the architecture the caller gives in metres: `walls` ({a, b, thickness_m}) as closed outlines and `rooms` ({name, at}) as text, in the frame of the plan on the screen (y down, like the nodes of the drawing: the DXF turns y up). Returns how many entities were added."""
    count = 0
    wall_layer, room_layer = layer(cfg["wall_layer"]), layer(cfg["room_layer"])
    for name in (wall_layer, room_layer):
        if name not in doc.layers:
            doc.layers.add(name)
    for w in backdrop.get("walls", []):
        corners = _wall_corners(w["a"], w["b"], w["thickness_m"])
        if corners:
            msp.add_lwpolyline([(x * scale, -y * scale) for x, y in corners], close=True, dxfattribs={"layer": wall_layer})
            count += 1
    for r in backdrop.get("rooms", []):
        msp.add_text(r["name"], height=height, dxfattribs={"layer": room_layer}).set_placement((r["at"][0] * scale, -r["at"][1] * scale), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        count += 1
    return count


def _dxf_version(cfg, version):
    """The DXF version asked for (the default when empty); refuses one the configuration does not list."""
    version = version or cfg["default_version"]
    if version not in cfg["versions"]:
        raise core.PlanError(f"DXF version {version!r} is not available: choose one of {', '.join(cfg['versions'])}")
    return version


def write_dxf(result: Dict[str, Any], path: Path, version: str = "", params: Dict[str, Any] = core.PARAMS, layers_file=None, backdrop: Optional[Dict[str, Any]] = None) -> List[str]:
    """Write the DXF of a result to `path`; returns the warnings (audit findings, read-back differences). `backdrop`: the walls and room names of the building under the services (see `_add_backdrop`)."""
    cfg = params["dxf"]
    version = _dxf_version(cfg, version)
    profile = core.load_profile(result["discipline"])
    line_kinds, node_kinds = core._kinds(profile)
    code, scale = _UNITS[profile.get("unidades_salida", cfg["default_units"])]
    doc = ezdxf.new(dxfversion=version, setup=True)
    doc.units = code
    doc.styles.get("Standard").dxf.font = "arial.ttf"                    # one typeface for every text of the drawing
    msp = doc.modelspace()
    layer = lambda base: "plan." + base                          # noqa: E731 - the draft names a layer by its ROLE; the deliverable service gives it its name and look (the catalog the MASTER edits)
    for base in sorted({k["capa_dxf"] for k in list(line_kinds.values()) + list(node_kinds.values())} | {cfg["tag_layer"], cfg["junction_layer"]}):
        doc.layers.add(layer(base))
    height = cfg["text_height_m"] * scale
    expected = _add_nodes(doc, msp, result, node_kinds, cfg, scale, height, layer) + _add_stretches(msp, result, line_kinds, cfg, scale, height, layer)
    if backdrop:
        expected += _add_backdrop(doc, msp, backdrop, cfg, scale, height, layer)

    path.parent.mkdir(parents=True, exist_ok=True)
    warnings = [f"DXF audit: {e.message}" for e in doc.audit().errors]
    deliverable.finish_draft(doc, path, layers_file)
    back = len(ezdxf.readfile(str(path)).modelspace())
    if back != expected:
        warnings.append(f"DXF read back has {back} entities, expected {expected}")
    return warnings
