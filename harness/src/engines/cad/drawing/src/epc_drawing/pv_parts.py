"""Detail of PV equipment for the 3D model, read from the equipment records (`epc_pv/data/pv_modules`, `pv_inverters`): module frame, cells and junction box, inverter enclosure and its terminals.

Nothing here invents a value. A dimension comes from the record, with the status the record gives it (`unverified`, `typical`, `not_found`); where the record has no value a simple reference
dimension is used and the part goes to the fallback layer, so the person can tell sourced geometry from a drawing convention. The records are handed in by the caller (this engine does not import `epc_pv`):

  find_record(data_dir, record_id) -> dict | None     the JSON record whose `id` is `record_id`, searched under `data_dir`
  layer_for(status) -> str                            `PV-3D-REF-UNVERIFIED`, `PV-3D-REF-TYPICAL` or `PV-3D-REF-FALLBACK`
  module_detail(record, length_m, width_m, thick_m, level) -> dict      parts of one module in its own frame (u along the short side, s along the long, w normal)
  inverter_detail(record, level) -> dict                                parts of one inverter in metres (x width, y height, z depth; wall at z=0)
"""
import json
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


def _frame(record, length_m: float, width_m: float, thick_m: float) -> Tuple[str, List[Quad], float]:
    """(layer, faces, face width) of the module frame: the section of the record when it gives one, else the reference width."""
    frame = _part(record or {}, "frame_profile")
    sec = (frame or {}).get("dimensions_mm") or {}
    fw = float(sec["width"]) / 1000.0 if sec.get("width") else FRAME_WIDTH_M
    layer = layer_for(frame.get("status")) if frame and sec.get("width") else FALLBACK_LAYER
    e, h = 0.002, thick_m + 0.004   # the frame stands 2 mm proud of the laminate faces so the two do not coincide
    faces = (_box(0, 0, -e, width_m, fw, h) + _box(0, length_m - fw, -e, width_m, fw, h)
             + _box(0, fw, -e, fw, length_m - 2 * fw, h) + _box(width_m - fw, fw, -e, fw, length_m - 2 * fw, h))
    return layer, faces, fw


def _junction_box(record, length_m: float, width_m: float, fw: float) -> Tuple[str, List[Quad]]:
    jb = _part(record or {}, "junction_box")
    jd = (jb or {}).get("dimensions_mm") or {}
    sourced = all(k in jd for k in ("length", "width", "thickness"))
    jl, jw, jt = (float(jd[k]) / 1000.0 for k in ("length", "width", "thickness")) if sourced else JBOX_M
    layer = layer_for(jb.get("status")) if jb and sourced else FALLBACK_LAYER
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
