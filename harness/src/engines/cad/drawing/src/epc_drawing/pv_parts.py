"""Detail of PV equipment for the 3D model, read from the equipment records (`epc_pv/data/pv_modules`, `pv_inverters`): module frame, cells and junction box, inverter enclosure and its terminals.

Nothing here invents a value. A dimension comes from the record, with the status the record gives it (`unverified`, `typical`, `not_found`); where the record has no value a simple reference
dimension is used and the part goes to the fallback layer, so the person can tell sourced geometry from a drawing convention. The records are handed in by the caller (this engine does not import `epc_pv`):

  find_record(data_dir, record_id) -> dict | None     the JSON record whose `id` is `record_id`, searched under `data_dir`
  layer_for(status) -> str                            `PV-3D-REF-UNVERIFIED`, `PV-3D-REF-TYPICAL` or `PV-3D-REF-FALLBACK`
  module_detail(record, length_m, width_m, thick_m, level) -> dict      parts of one module in its own frame (u along the short side, s along the long, w normal)
  post_section(record) -> dict | None                                   the section of the post of a mounting structure record, as polygons in metres, with its layer
  inverter_detail(record, level) -> dict                                parts of one inverter in metres (x width, y height, z depth; wall at z=0)
"""
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

Quad = Tuple[Tuple[float, float, float], ...]
LEVELS = ("low", "standard", "full")
FRAME_WIDTH_M = 0.035          # reference frame face width when the record gives no section
JBOX_M = (0.12, 0.07, 0.02)    # reference junction box (along, across, depth) when the record gives none
CONNECTOR_M = 0.05             # reference length of a terminal hanging under an inverter
STATUS_LAYER = {"unverified": "PV-3D-REF-UNVERIFIED", "typical": "PV-3D-REF-TYPICAL"}
FALLBACK_LAYER = "PV-3D-REF-FALLBACK"
REF_LAYERS = {"PV-3D-REF-UNVERIFIED": 40, "PV-3D-REF-TYPICAL": 30, "PV-3D-REF-FALLBACK": 6}
_cache: Dict[Tuple[str, str], Optional[Dict[str, Any]]] = {}


def layer_for(status: Optional[str]) -> str:
    return STATUS_LAYER.get(status or "", FALLBACK_LAYER)


def find_record(data_dir, record_id: str) -> Optional[Dict[str, Any]]:
    """The record whose `id` is `record_id` under `data_dir` (any depth); None when there is none or `data_dir` is missing."""
    root = Path(data_dir) if data_dir else None
    if root is None or not root.is_dir() or not record_id:
        return None
    key = (str(root), record_id)
    if key not in _cache:
        found = None
        for path in sorted(root.rglob(f"{record_id}.json")):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if rec.get("id") == record_id:
                found = rec
                break
        _cache[key] = found
    return _cache[key]


def _box(x: float, y: float, z: float, dx: float, dy: float, dz: float) -> List[Quad]:
    p = [(x + i * dx, y + j * dy, z + k * dz) for k in (0, 1) for j in (0, 1) for i in (0, 1)]
    return [(p[0], p[1], p[3], p[2]), (p[4], p[5], p[7], p[6]), (p[0], p[1], p[5], p[4]), (p[2], p[3], p[7], p[6]), (p[0], p[2], p[6], p[4]), (p[1], p[3], p[7], p[5])]


def _part(record: Dict[str, Any], kind: str) -> Optional[Dict[str, Any]]:
    return next((p for p in record.get("parts", []) if p.get("type") == kind), None)


def cell_grid(record: Optional[Dict[str, Any]]) -> Optional[Tuple[int, int]]:
    """(columns across the short side, rows along the long side) read from a printed hint such as "2 x (9 x 6)"; None when the record does not print it."""
    part = _part(record or {}, "cell_string")
    m = re.search(r"(\d+)\s*x\s*\(\s*(\d+)\s*x\s*(\d+)\s*\)", (part or {}).get("geometry_hint", ""))
    if not m:
        return None
    halves, a, b = (int(g) for g in m.groups())
    return (min(a, b), max(a, b) * halves)


def frame_width(record) -> Tuple[float, str]:
    """(face width in metres, layer) of the module frame: the section of the record when it gives one, else the reference width on the fallback layer."""
    frame = _part(record or {}, "frame_profile")
    sec = (frame or {}).get("dimensions_mm") or {}
    if sec.get("width"):
        return float(sec["width"]) / 1000.0, layer_for(frame.get("status"))
    return FRAME_WIDTH_M, FALLBACK_LAYER


def junction_size(record) -> Tuple[Tuple[float, float, float], str]:
    """((along the long side, across, depth) in metres, layer) of the junction box: the record's when it gives all three, else the reference box on the fallback layer."""
    jb = _part(record or {}, "junction_box")
    jd = (jb or {}).get("dimensions_mm") or {}
    if all(k in jd for k in ("length", "width", "thickness")):
        return tuple(float(jd[k]) / 1000.0 for k in ("length", "width", "thickness")), layer_for(jb.get("status"))
    return JBOX_M, FALLBACK_LAYER


def _frame(record, length_m: float, width_m: float, thick_m: float) -> Tuple[str, List[Quad], float]:
    """(layer, faces, face width) of the module frame (see `frame_width`)."""
    fw, layer = frame_width(record)
    e, h = 0.002, thick_m + 0.004   # the frame stands 2 mm proud of the laminate faces so the two do not coincide
    faces = (_box(0, 0, -e, width_m, fw, h) + _box(0, length_m - fw, -e, width_m, fw, h)
             + _box(0, fw, -e, fw, length_m - 2 * fw, h) + _box(width_m - fw, fw, -e, fw, length_m - 2 * fw, h))
    return layer, faces, fw


def _junction_box(record, length_m: float, width_m: float, fw: float) -> Tuple[str, List[Quad]]:
    (jl, jw, jt), layer = junction_size(record)
    return layer, _box(width_m / 2 - jw / 2, length_m - fw - jl - 0.05, -0.002 - jt, jw, jl, jt)


def _cells(record, length_m: float, width_m: float, thick_m: float, fw: float) -> Tuple[str, List[Quad]]:
    """One flat face per cell, when the record prints the cell grid; none otherwise."""
    grid = cell_grid(record)
    if not grid:
        return FALLBACK_LAYER, []
    cols, rows = grid
    gu, gs, z = (width_m - 2 * fw) / cols, (length_m - 2 * fw) / rows, thick_m + 0.002
    faces = []
    for r in range(rows):
        for c in range(cols):
            u0, s0 = fw + c * gu + 0.001, fw + r * gs + 0.001
            faces.append(((u0, s0, z), (u0 + gu - 0.002, s0, z), (u0 + gu - 0.002, s0 + gs - 0.002, z), (u0, s0 + gs - 0.002, z)))
    return layer_for((_part(record, "cell_string") or {}).get("status")), faces


def module_detail(record: Optional[Dict[str, Any]], length_m: float, width_m: float, thick_m: float, level: str = "standard") -> Dict[str, List[Quad]]:
    """Layer name -> faces of the frame, the cell block and the junction box of one module, in its frame: u across the short side (0..width), s along the long side (0..length), w normal (0..thick).
    At level `low` nothing is added; `full` adds one face per cell when the record prints the cell grid."""
    out: Dict[str, List[Quad]] = {}
    if level == "low":
        return out
    layer, faces, fw = _frame(record, length_m, width_m, thick_m)
    out.setdefault(layer, []).extend(faces)
    layer, faces = _junction_box(record, length_m, width_m, fw)
    out.setdefault(layer, []).extend(faces)
    if level == "full":
        layer, faces = _cells(record, length_m, width_m, thick_m, fw)
        if faces:
            out.setdefault(layer, []).extend(faces)
    return out


CONNECTORS = ("dc_input", "ac_terminal", "mppt_input", "comm_port", "gland")
FRONT_PARTS = ("display", "led_indicator", "dc_switch")
ENCLOSURES = ("enclosure", "enclosure_body")


def _inverter_part(e: Dict[str, Any], depth: float, level: str) -> Optional[Tuple[str, List[Quad]]]:
    """(layer, faces) of one terminal or front part of an inverter record, in the record frame; None for a part that is not drawn."""
    x, y, z = (float(v) / 1000.0 for v in e.get("position_mm", (0, 0, 0)))
    sx, sy, sz = (max(float(v) / 1000.0, 0.004) for v in e["size_mm"])
    kind, layer = e.get("kind"), layer_for(e.get("status"))
    if kind in CONNECTORS:
        return layer, _box(x, -CONNECTOR_M, depth - z - sz / 2, sx, CONNECTOR_M, sz)       # hangs under the enclosure, at its depth position
    if kind in FRONT_PARTS:
        return layer, _box(x, y, depth, sx, sy, 0.012)                                      # on the front cover
    if kind == "fan" and level == "full":
        return layer, _box(x, 0, depth, sx, sy, 0.01)
    return None


def _inverter_parts(elements: List[Dict[str, Any]], depth: float, level: str) -> List[Tuple[str, List[Quad]]]:
    drawn = (_inverter_part(e, depth, level) for e in elements if e.get("size_mm") and e.get("kind") not in ENCLOSURES)
    return [p for p in drawn if p]


def inverter_detail(record: Optional[Dict[str, Any]], level: str = "standard") -> Optional[Dict[str, Any]]:
    """{'size': (W, H, D) metres, 'status', 'parts': [(layer, faces)]} of an inverter record: the enclosure size and its terminals (DC and AC inputs, communication, glands hang under the enclosure;
    display, indicators and the DC switch sit on the front face). None when the record gives no enclosure size."""
    elements = (record or {}).get("geometry", {}).get("elements", [])
    el = next((e for e in elements if e.get("kind") in ENCLOSURES and e.get("size_mm")), None)
    if el is None:
        return None
    w, h, d = (float(v) / 1000.0 for v in el["size_mm"])
    return {"size": (w, h, d), "status": el.get("status"), "parts": [] if level == "low" else _inverter_parts(elements, d, level)}


SIDES_ROUND = 12


def _rect(x: float, y: float, w: float, h: float) -> List[Tuple[float, float]]:
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def _round(m: Dict[str, float]) -> List[List[Tuple[float, float]]]:
    r = m["outer_diameter"] / 2
    return [[(r * math.cos(2 * math.pi * i / SIDES_ROUND), r * math.sin(2 * math.pi * i / SIDES_ROUND)) for i in range(SIDES_ROUND)]]


def _h_beam(m: Dict[str, float]) -> List[List[Tuple[float, float]]]:
    w, h, tf, tw = m["width"], m["height"], m["flange_thickness"], m["web_thickness"]
    return [_rect(-w / 2, -h / 2, w, tf), _rect(-w / 2, h / 2 - tf, w, tf), _rect(-tw / 2, -h / 2 + tf, tw, h - 2 * tf)]


def _c_section(m: Dict[str, float]) -> List[List[Tuple[float, float]]]:
    w, h, t, lip = m["width"], m["height"], m["thickness_max"], m.get("lip", 0.0)
    lips = [_rect(w / 2 - t, -h / 2, t, lip), _rect(w / 2 - t, h / 2 - lip, t, lip)] if lip else []
    return [_rect(-w / 2, -h / 2, t, h), _rect(-w / 2, -h / 2, w, t), _rect(-w / 2, h / 2 - t, w, t)] + lips


# profile type -> (dimensions it needs, builder of its section polygons)
SECTIONS = {"rect_tube": (("width", "height"), lambda m: [_rect(-m["width"] / 2, -m["height"] / 2, m["width"], m["height"])]),
            "round_tube": (("outer_diameter",), _round),
            "H_beam": (("width", "height", "flange_thickness", "web_thickness"), _h_beam),
            "C": (("width", "height", "thickness_max"), _c_section)}


def _section_polygons(kind: str, d: Dict[str, float]) -> List[List[Tuple[float, float]]]:
    """The section polygons (metres, centred on the origin, x along the table row, y across it) of a profile of a given type, from its dimensions in mm; [] for a type or dimensions the record does not give."""
    needs, build = SECTIONS.get(kind, ((), None))
    m = {k: float(v) / 1000.0 for k, v in d.items() if isinstance(v, (int, float))}
    return build(m) if build and set(needs) <= m.keys() else []


def post_section(record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """{'polygons': [...], 'layer': ..., 'profile': id} of the first post of a mounting structure record whose profile gives its dimensions (rectangular or round tube, H beam, C section); None when
    the record has no such post, and the caller keeps the reference square post."""
    profiles = {p["id"]: p for p in (record or {}).get("profiles", [])}
    for e in (record or {}).get("geometry", {}).get("elements", []):
        p = profiles.get(e.get("profile_or_accessory_id"))
        polys = _section_polygons(p["section_type"], p.get("dimensions_mm") or {}) if p and e.get("kind") == "post" else []
        if polys:
            return {"polygons": polys, "layer": layer_for(p.get("status")), "profile": p["id"]}
    return None


def prism(polygon: List[Tuple[float, float]], cx: float, cy: float, z0: float, height: float) -> List[Quad]:
    """The faces of a polygon extruded up from z0 by height, centred on (cx, cy); the caps are fans of quads (a triangle repeats a vertex)."""
    pts = [(cx + x, cy + y) for x, y in polygon]
    n, faces = len(pts), []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        faces.append(((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z0 + height), (a[0], a[1], z0 + height)))
    for z in (z0, z0 + height):
        faces += [((pts[0][0], pts[0][1], z), (pts[i][0], pts[i][1], z), (pts[i + 1][0], pts[i + 1][1], z), (pts[i + 1][0], pts[i + 1][1], z)) for i in range(1, n - 1)]
    return faces
