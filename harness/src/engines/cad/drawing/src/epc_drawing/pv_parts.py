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


def module_detail(record: Optional[Dict[str, Any]], length_m: float, width_m: float, thick_m: float, level: str = "standard") -> Dict[str, List[Quad]]:
    """Layer name -> faces of the frame, the cell block and the junction box of one module, in its frame: u across the short side (0..width), s along the long side (0..length), w normal (0..thick).
    At level `low` nothing is added; `full` adds one face per cell when the record prints the cell grid."""
    out: Dict[str, List[Quad]] = {}
    if level == "low":
        return out
    frame = _part(record or {}, "frame_profile")
    sec = (frame or {}).get("dimensions_mm") or {}
    fw = float(sec["width"]) / 1000.0 if sec.get("width") else FRAME_WIDTH_M
    frame_layer = layer_for(frame.get("status")) if frame and sec.get("width") else FALLBACK_LAYER
    e = 0.002   # the frame stands 2 mm proud of the laminate faces so the two do not coincide
    out.setdefault(frame_layer, []).extend(
        _box(0, 0, -e, width_m, fw, thick_m + 2 * e) + _box(0, length_m - fw, -e, width_m, fw, thick_m + 2 * e)
        + _box(0, fw, -e, fw, length_m - 2 * fw, thick_m + 2 * e) + _box(width_m - fw, fw, -e, fw, length_m - 2 * fw, thick_m + 2 * e))
    jb = _part(record or {}, "junction_box")
    jd = (jb or {}).get("dimensions_mm") or {}
    jl, jw, jt = (float(jd[k]) / 1000.0 for k in ("length", "width", "thickness")) if all(k in jd for k in ("length", "width", "thickness")) else JBOX_M
    jb_layer = layer_for(jb.get("status")) if jb and jd else FALLBACK_LAYER
    out.setdefault(jb_layer, []).extend(_box(width_m / 2 - jw / 2, length_m - fw - jl - 0.05, -e - jt, jw, jl, jt))
    grid = cell_grid(record)
    cells = (_part(record or {}, "cell_string") or {})
    if level == "full" and grid:
        cols, rows = grid
        gu, gs = (width_m - 2 * fw) / cols, (length_m - 2 * fw) / rows
        layer = layer_for(cells.get("status"))
        for r in range(rows):
            for c in range(cols):
                u0, s0, z = fw + c * gu + 0.001, fw + r * gs + 0.001, thick_m + e
                out.setdefault(layer, []).append(((u0, s0, z), (u0 + gu - 0.002, s0, z), (u0 + gu - 0.002, s0 + gs - 0.002, z), (u0, s0 + gs - 0.002, z)))
    return out


def inverter_detail(record: Optional[Dict[str, Any]], level: str = "standard") -> Optional[Dict[str, Any]]:
    """{'size': (W, H, D) metres, 'status', 'parts': [(layer, faces)]} of an inverter record: the enclosure size and its terminals (DC and AC inputs, communication, glands hang under the enclosure;
    display, indicators and the DC switch sit on the front face). None when the record gives no enclosure size."""
    el = next((e for e in (record or {}).get("geometry", {}).get("elements", []) if e.get("kind") in ("enclosure", "enclosure_body") and e.get("size_mm")), None)
    if el is None:
        return None
    w, h, d = (float(v) / 1000.0 for v in el["size_mm"])
    parts: List[Tuple[str, List[Quad]]] = []
    if level != "low":
        for e in record["geometry"]["elements"]:
            if e is el or not e.get("size_mm") or e.get("kind") in ("enclosure", "enclosure_body"):
                continue
            x, y, z = (float(v) / 1000.0 for v in e.get("position_mm", (0, 0, 0)))
            sx, sy, sz = (max(float(v) / 1000.0, 0.004) for v in e["size_mm"])
            kind, layer = e.get("kind"), layer_for(e.get("status"))
            if kind in ("dc_input", "ac_terminal", "mppt_input", "comm_port", "gland"):
                parts.append((layer, _box(x, -CONNECTOR_M, d - z - sz / 2, sx, CONNECTOR_M, sz)))        # hangs under the enclosure, at its depth position
            elif kind in ("display", "led_indicator", "dc_switch"):
                parts.append((layer, _box(x, y, d, sx, sy, 0.012)))                                      # on the front cover
            elif kind == "fan" and level == "full":
                parts.append((layer, _box(x, 0, d, sx, sy, 0.01)))
    return {"size": (w, h, d), "status": el.get("status"), "parts": parts}
