"""The 3D model of a rooftop photovoltaic plant, raised from the roof planes `epc_pv.plan_roof` placed: a DXF with solid faces that any CAD or BIM program opens.

Each plane is a slab (its slope length, width and tilt), the modules sit on it at the placed cells, parallel to the plane on a low mounting stand-off, and the obstacles stand on it. The planes are drawn side by side
(as in the roof drawings), eave low, in metres, x along the eave, y up the slope in plan, z up: the harness has no building geometry, so the planes are not placed on a building. It calculates nothing: every
dimension is read from the planes; the slab thickness, the stand-off and the obstacle height are drawing conventions, not a structural design (wind uplift and ballast are not calculated).

  write(roof, result, out_dir, name, stamp_date) -> path      `<name>_pv_roof_model_3d.dxf` goes to the 3D folder of the transmittal
"""
import math
from pathlib import Path
from typing import Any, Dict

from epc_drawing import pv_model3d as m3
from epc_drawing.errors import DrawingError

SLAB_M, STANDOFF_M, MODULE_M, OBSTACLE_M, SPACING_M = 0.2, 0.12, 0.035, 1.0, 3.0
LAYER_ROOF = "291-WS-ROOF-N"
LAYERS = {**m3.LAYERS, LAYER_ROOF: 8, "291-WS-OBST-N": 1}


def build(roof: Dict[str, Any], result: Dict[str, Any]):
    """The ezdxf document of the roof model."""
    import ezdxf
    from epc_dxf import new_document
    if not roof.get("planes"):
        raise DrawingError("err_roof_no_planes")
    doc = new_document("R2018", setup=True)
    doc.units = 6
    for name, colour in LAYERS.items():
        doc.layers.add(name, color=colour)
    msp = doc.modelspace()
    x = 0.0
    for p in roof["planes"]:
        t = math.radians(float(p["tilt_deg"]))
        slope, width = float(p["slope_m"]), float(p["width_m"])
        origin = (x, 0.0, slope * math.sin(t))      # the high edge; the plane falls to the eave at y = 0
        m3._add(msp, LAYER_ROOF, m3.tilted_box(origin, t, 0.0, 0.0, -SLAB_M, width, slope, SLAB_M))
        md, mw = float(p["module"]["depth_m"]), float(p["module"]["width_m"])
        for c in p.get("cells", []):
            m3._add(msp, "291-WS-PVMD-N", m3.tilted_box(origin, t, float(c["x"]), slope - float(c["y"]) - md, STANDOFF_M, mw, md, MODULE_M))
        for o in p.get("obstacles", []):
            m3._add(msp, "291-WS-OBST-N", m3.tilted_box(origin, t, float(o["x"]), slope - float(o["y"]) - float(o["depth_m"]), 0.0, float(o["width_m"]), float(o["depth_m"]), OBSTACLE_M))
        x += width + 2.0
    return doc


def write(roof: Dict[str, Any], result: Dict[str, Any], out_dir, name: str, stamp_date=None) -> Path:
    """Writes `<name>_pv_roof_model_3d.dxf` in `out_dir` and returns its path."""
    from epc_dxf import deliverable
    doc = build(roof, result)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}_pv_roof_model_3d.dxf"
    deliverable.finish_draft(doc, path, None, stamp_date, path.stem)
    return path
