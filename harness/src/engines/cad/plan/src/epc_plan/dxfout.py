"""The DXF deliverable, written from the result of `core.process` with ezdxf (MIT). It is never converted from the SVG of the screen: both come from the same model.

Real units: metres or millimetres, as the discipline says. One layer per kind of element, one block per symbol used, real text for the tags.
"""
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import ezdxf
from epc_dxf import new_document
from epc_dxf import deliverable, textstyle

from epc_plan import core, tray_draw
from epc_plan.core import PlanError

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


def _define_block(doc, sid: str, size: float, scale: float, height: float, style: str = "Standard") -> str:
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
    blk.add_attdef("TAG", (size * scale * 0.6, size * scale * 0.6), height=height, dxfattribs={"style": style})
    return name


def _turn(n: Dict[str, Any]) -> Dict[str, float]:
    """The turn of a symbol (`rot_deg` on the node, clockwise on the screen) as the rotation of its block, counter-clockwise as CAD counts it."""
    rot = (n.get("attrs") or {}).get("rot_deg")
    return {"rotation": -float(rot)} if isinstance(rot, (int, float)) and not isinstance(rot, bool) and rot else {}


def _add_nodes(doc, msp, result, node_kinds, cfg, scale: float, height: float, layer, style: str = "Standard") -> int:
    """Placed nodes as block insertions with their tag, junctions as small circles. Returns how many entities were added."""
    count = 0
    for n in result["nodes"]:
        at = (n["x_m"] * scale, n["y_m"] * scale)
        if n["placed"]:
            kind = node_kinds[n["kind"]]
            block = _define_block(doc, kind["simbolo_2d"], cfg["node_symbol_size_m"], scale, height, style)
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


def _add_label(target, s, pts, height, cfg, layer, seen, style: str = "Standard", origin=(0.0, 0.0), lift: float = 0.0) -> int:
    """Write the label of a stretch when it fits, into the model space or into a block (`origin`: where the block is inserted); returns the entities added (0 or 1)."""
    text = _label(s, sum(math.dist(p, q) for p, q in zip(pts, pts[1:])), height)
    if not text:
        return 0
    mid, angle = _label_position(pts)
    x, y = _stacked(mid, angle, height, seen)
    x, y = x + math.cos(math.radians(angle + 90)) * lift, y + math.sin(math.radians(angle + 90)) * lift       # clear of a ladder drawn with its width
    target.add_text(text, height=height, rotation=angle, dxfattribs={"layer": layer(cfg["tag_layer"]), "style": style}).set_placement((x - origin[0], y - origin[1]), align=ezdxf.enums.TextEntityAlignment.BOTTOM_CENTER)
    return 1


def _block_name(doc, prefix: str, tag: str) -> str:
    """A block name for a tray: the prefix and its tag without the characters DXF forbids; a repeated tag gets a number."""
    base = prefix + "".join("_" if c in '<>/\\":;?*|=`,' or c.isspace() else c for c in tag)
    name, n = base, 1
    while name in doc.blocks:
        n += 1
        name = f"{base}_{n}"
    return name


def _tray_width_mm(s) -> float:
    """The width written on a tray (`ancho_mm` in its attributes), 0 when it has none or it is not a number."""
    try:
        return float((s.get("attrs") or {}).get("ancho_mm") or 0)
    except (TypeError, ValueError):
        return 0.0


TRAY_SIZES = {"lip": "lip_mm", "rung_pitch": "rung_pitch_mm", "rung_width": "rung_width_mm", "slot_pitch": "slot_pitch_mm", "slot_length": "slot_length_mm",
              "wire_pitch": "wire_pitch_mm", "radius": "radius_mm", "joint_pitch": "joint_length_mm"}


def _tray_kind(s, trays: Dict[str, Any]) -> str:
    """The kind of tray written on a stretch (`tipo_bandeja`), the configured default when it has none; an unknown kind is an error."""
    kind = str((s.get("attrs") or {}).get("tipo_bandeja") or trays["default_kind"])
    if kind not in tray_draw.KINDS:
        raise core.PlanError("err_tray_kind", kind=kind, kinds=", ".join(tray_draw.KINDS))
    return kind


def _add_tray_detail(blk, s, pts, origin, scale: float, trays: Dict[str, Any], line_layer: str) -> None:
    """A tray that has a width (`ancho_mm` in its attributes) is drawn as what it is (ladder, perforated, solid or wire mesh) with its rails, joints and bends;
    without a width it stays a line."""
    width_mm = _tray_width_mm(s)
    if width_mm <= 0 or len(pts) < 2:
        return
    unit = scale / 1000.0                                          # drawing units per millimetre
    sizes = {key: float(trays[name]) * unit for key, name in TRAY_SIZES.items()}
    for a, b in tray_draw.tray_lines(pts, _tray_kind(s, trays), width_mm * unit, sizes):
        blk.add_line((a[0] - origin[0], a[1] - origin[1]), (b[0] - origin[0], b[1] - origin[1]), dxfattribs={"layer": line_layer})


def _add_tray_block(doc, msp, s, pts, line_layer: str, cfg, height: float, layer, seen, style: str, trays: Dict[str, Any], scale: float = 1.0) -> None:
    """One block per tray: its outline (a ladder with its rails and rungs when it has a width) and its text inside, inserted at the first point so the CAD moves everything together."""
    ox, oy = pts[0]
    blk = doc.blocks.new(name=_block_name(doc, trays["block_prefix"], s["tag"]))
    blk.add_lwpolyline([(x - ox, y - oy) for x, y in pts], dxfattribs={"layer": line_layer})
    _add_tray_detail(blk, s, pts, (ox, oy), scale, trays, line_layer)
    lift = _tray_width_mm(s) / 2000.0 * scale
    _add_label(blk, s, pts, height, cfg, layer, seen, style, (ox, oy), lift)
    msp.add_blockref(blk.name, (ox, oy), dxfattribs={"layer": line_layer})


def _add_stretch(doc, msp, s, line_kinds, cfg, scale: float, height: float, layer, seen, style: str, trays: Dict[str, Any]) -> int:
    """One stretch: a block when its kind is drawn as one (the tray), else a loose outline and its label. Returns how many entities of the model space were added."""
    pts = [(x * scale, y * scale) for x, y in s["points_m"]]
    line_layer = layer(line_kinds[s["kind"]]["capa_dxf"])
    if doc is not None and trays.get("as_block") and s["kind"] in trays.get("kinds", []):
        _add_tray_block(doc, msp, s, pts, line_layer, cfg, height, layer, seen, style, trays, scale)
        return 1
    msp.add_lwpolyline(pts, dxfattribs={"layer": line_layer})
    return 1 + _add_label(msp, s, pts, height, cfg, layer, seen, style)


def _add_stretches(msp, result, line_kinds, cfg, scale: float, height: float, layer, doc=None, style: str = "Standard", trays: Optional[Dict[str, Any]] = None) -> int:
    seen: Dict[Any, int] = {}
    return sum(_add_stretch(doc, msp, s, line_kinds, cfg, scale, height, layer, seen, style, trays or {}) for s in result["stretches"])


def _wall_corners(a, b, thickness: float):
    """The four corners of a wall (its axis a-b and its thickness, all in metres)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return None
    nx, ny = -dy / length * thickness / 2, dx / length * thickness / 2
    return [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)]


def _add_backdrop(doc, msp, backdrop: Dict[str, Any], cfg, scale: float, height: float, layer, style: str = "Standard") -> int:
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
        msp.add_text(r["name"], height=height, dxfattribs={"layer": room_layer, "style": style}).set_placement((r["at"][0] * scale, -r["at"][1] * scale), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        count += 1
    return count


def _rgb(color: str) -> int:
    return ezdxf.colors.rgb2int(tuple(int(color[k:k + 2], 16) for k in (1, 3, 5)))


def _solid(msp, rect, scale: float, color: str, layer: str) -> None:
    x0, y0, x1, y1 = (v * scale for v in rect)
    msp.add_solid([(x0, -y0), (x1, -y0), (x0, -y1), (x1, -y1)], dxfattribs={"layer": layer, "true_color": _rgb(color)})


def _add_luxbar(msp, bar: Dict[str, Any], scale: float, height: float, cells_layer: str, text_layer: str, style: str) -> int:
    """The colour bar of the lux map: its cells, the text of each tick and the caption; returns how many entities were added."""
    left = ezdxf.enums.TextEntityAlignment.MIDDLE_LEFT
    for c in bar["cells"]:
        _solid(msp, c["rect"], scale, c["color"], cells_layer)
    for t in bar["ticks"]:
        msp.add_text(t["text"], height=height, dxfattribs={"layer": text_layer, "style": style}).set_placement(((t["at"][0] + 0.15) * scale, -t["at"][1] * scale), align=left)
    caption = bar["caption"]["en"] if isinstance(bar["caption"], dict) else bar["caption"]
    msp.add_text(caption, height=height, dxfattribs={"layer": text_layer, "style": style}).set_placement((bar["at"][0] * scale, -bar["at"][1] * scale), align=left)
    return len(bar["cells"]) + len(bar["ticks"]) + 1


def _add_luxmap(doc, msp, luxmap: Dict[str, Any], scale: float, height: float, layer, style: str = "Standard") -> int:
    """The lux map under the luminaires, from the map the discipline gives in metres (y down, like the nodes): `rooms` with `cells` ({rect, color}) as a smooth colour field, `curves` (lines of equal level,
    {points, level_lux, color, weight}) with their value in lux, a reading of each room and a colour bar (`bar`: cells, ticks, caption, at). Returns how many entities were added."""
    count = 0
    cells_layer, curves_layer, text_layer = layer("ELEC-LUX-MAPA"), layer("ELEC-LUX-CURVAS"), layer("ELEC-LUX-TEXTO")
    for name in (cells_layer, curves_layer, text_layer):
        if name not in doc.layers:
            doc.layers.add(name)
    middle = ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
    for room in luxmap["rooms"]:
        for c in room["cells"]:
            _solid(msp, c["rect"], scale, c["color"], cells_layer)
            count += 1
        for curve in room["curves"]:
            msp.add_lwpolyline([(x * scale, -y * scale) for x, y in curve["points"]], dxfattribs={"layer": curves_layer, "true_color": _rgb(curve["color"]), "lineweight": int(curve["weight"] * 100)})
            mid = curve["points"][len(curve["points"]) // 2]
            msp.add_text(f"{curve['level_lux']:g}", height=height, dxfattribs={"layer": text_layer, "style": style, "true_color": _rgb(curve["color"])}).set_placement((mid[0] * scale, -mid[1] * scale), align=middle)
            count += 2
        x0, y0, x1, y1 = room["box"]
        msp.add_text(f"{room['target_lux']:g} lx / {room['stats']['avg_lux']:g}", height=height, dxfattribs={"layer": text_layer, "style": style}).set_placement(((x0 + x1) / 2 * scale, -(y1 - 0.3) * scale), align=middle)
        count += 1
    count += _add_luxbar(msp, luxmap["bar"], scale, height, cells_layer, text_layer, style) if luxmap.get("bar") else 0
    return count


def _dxf_version(cfg, version):
    """The DXF version asked for (the default when empty); refuses one the configuration does not list."""
    version = version or cfg["default_version"]
    if version not in cfg["versions"]:
        raise core.PlanError("err_dxf_version", version=version, versions=', '.join(cfg['versions']))
    return version


def _sizes(look: Dict[str, Any], cfg: Dict[str, Any], scale: float, paper_scale: Optional[int]):
    """(height of the text, size of the node symbols) in the units of the drawing. With the scale of the sheet the plan will be printed at (`paper_scale`, the N of 1:N) both are paper sizes
    (`plan_text_mm`, `plan_symbol_mm` of `harness/config/dxf/text.json`) turned into real size at that scale, so they look the same on paper at every scale; without it they are the real sizes
    (`plan_text_m`, `node_symbol_size_m`)."""
    if paper_scale:
        return float(look["heights"]["plan_text_mm"]) * paper_scale / 1000.0 * scale, float(look["heights"]["plan_symbol_mm"]) * paper_scale / 1000.0
    return float(look["heights"]["plan_text_m"]) * scale, cfg["node_symbol_size_m"]


def write_dxf(result: Dict[str, Any], path: Path, version: str = "", params: Dict[str, Any] = core.PARAMS, layers_file=None, backdrop: Optional[Dict[str, Any]] = None, paper_scale: Optional[int] = None, luxmap: Optional[Dict[str, Any]] = None) -> List[str]:
    """Write the DXF of a result to `path`; returns the warnings (audit findings, read-back differences). `backdrop`: the walls and room names of the building under the services (see `_add_backdrop`).
    `paper_scale`: the scale of the sheet it will be placed on, so that text and symbols are sized for it (see `_sizes`). `luxmap`: the lux map of the floor (see `_add_luxmap`), drawn under the services."""
    cfg = params["dxf"]
    version = _dxf_version(cfg, version)
    profile = core.load_profile(result["discipline"])
    line_kinds, node_kinds = core._kinds(profile)
    code, scale = _UNITS[profile.get("unidades_salida", cfg["default_units"])]
    doc = new_document(version, setup=True)
    doc.units = code
    doc.styles.get("Standard").dxf.font = "arial.ttf"                    # one typeface for every text of the drawing
    msp = doc.modelspace()
    layer = lambda base: "plan." + base                          # noqa: E731 - the draft names a layer by its ROLE; the deliverable service gives it its name and look (the catalog the MASTER edits)
    for base in sorted({k["capa_dxf"] for k in list(line_kinds.values()) + list(node_kinds.values())} | {cfg["tag_layer"], cfg["junction_layer"]}):
        doc.layers.add(layer(base))
    look = textstyle.load()                                      # typeface, text height and tray blocks: harness/config/dxf/text.json
    textstyle.add_styles(doc)
    style = look["font"]["style"]
    height, symbol = _sizes(look, cfg, scale, paper_scale)
    expected = _add_luxmap(doc, msp, luxmap, scale, height, layer, style) if luxmap else 0
    expected += _add_nodes(doc, msp, result, node_kinds, dict(cfg, node_symbol_size_m=symbol), scale, height, layer, style) + _add_stretches(msp, result, line_kinds, cfg, scale, height, layer, doc, style, look["trays"])
    if backdrop:
        expected += _add_backdrop(doc, msp, backdrop, cfg, scale, height, layer, style)

    path.parent.mkdir(parents=True, exist_ok=True)
    warnings = [f"DXF audit: {e.message}" for e in doc.audit().errors]
    deliverable.finish_draft(doc, path, layers_file)
    back = len(ezdxf.readfile(str(path)).modelspace())
    if back != expected:
        warnings.append(f"DXF read back has {back} entities, expected {expected}")
    return warnings
