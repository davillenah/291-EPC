"""The 3D model of a photovoltaic plant as a FreeCAD macro, written by the harness from the same parts as the 3D DXF (`pv_model3d`).

FreeCAD is a program the harness does not run; what it writes is the macro that FreeCAD runs to build the model (File > Macro > Execute, or `exec(open(path).read())` in its Python console). The macro is
parametric in the way a CAD assembly is: every distinct table (modules, width, tilt) and every inverter type is built once as a part (`App::Part` with one solid group per layer), and every table or
inverter of the plant is an `App::Link` to that part with its own placement. The ground, the station and the fence are single objects. The macro is written part by part (one sector at a time), so a
big plant is not held in memory, and it carries no number of its own: every dimension is read from the faces the 3D engine drew.

  write(geometry, result, out_dir, name, stamp_date, parts, level, sector_modules) -> {"macro": path, "blocks": n, "instances": n}   `<name>_pv_model_3d_freecad.FCMacro`
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional

from epc_drawing import pv_model3d

# ACI colour index of each layer -> RGB (0..1); a layer of the reference status family not listed here is drawn grey.
ACI_RGB = {1: (0.9, 0.1, 0.1), 4: (0.0, 0.8, 0.8), 5: (0.1, 0.1, 0.85), 7: (0.85, 0.85, 0.85), 8: (0.45, 0.45, 0.45), 9: (0.65, 0.65, 0.65), 30: (0.8, 0.45, 0.1)}
HEADER = '''# FreeCAD macro written by the EPC-291 harness: 3D model of a photovoltaic plant (metres in the model, millimetres in FreeCAD). Run it in FreeCAD: File > Macro > Execute macro.
# Every distinct table and inverter is one part (B); every table or inverter of the plant is a link to it (I) with its own placement; ground, station and fence are single objects (F, P).
import FreeCAD as App
import Part
V = App.Vector
K = 1000.0
doc = App.newDocument("{title}")
COLOURS = {colours}
LAYERS = {{}}
BASES = {{}}
COUNT = {{"blocks": 0, "instances": 0, "faces": 0}}


def _group(layer):
    if layer not in LAYERS:
        LAYERS[layer] = doc.addObject("App::DocumentObjectGroup", layer.replace("-", "_"))
    return LAYERS[layer]


def _face(pts):
    pts = [V(p[0] * K, p[1] * K, p[2] * K) for p in pts]
    try:
        return Part.Face(Part.makePolygon(pts + [pts[0]]))
    except Exception:
        return None


def _paint(obj, layer):
    if App.GuiUp:
        obj.ViewObject.ShapeColor = COLOURS.get(layer, (0.6, 0.6, 0.6))


def _solid(name, layer, faces):
    shapes = [s for s in (_face(f) for f in faces) if s is not None]
    COUNT["faces"] += len(shapes)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = Part.makeCompound(shapes)
    _paint(obj, layer)
    return obj


def B(name, by_layer):
    """A part: one solid group per layer, kept as a container the instances link to."""
    part = doc.addObject("App::Part", name.replace("-", "_"))
    for layer, faces in by_layer.items():
        part.addObject(_solid(name.replace("-", "_") + "_" + layer[-8:].replace("-", "_"), layer, faces))
    BASES[name] = part
    COUNT["blocks"] += 1


def I(name, x, y, z, layer):
    link = doc.addObject("App::Link", "L_" + name.replace("-", "_"))
    link.LinkedObject = BASES[name]
    link.Placement = App.Placement(V(x * K, y * K, z * K), App.Rotation())
    _group(layer).addObject(link)
    COUNT["instances"] += 1


def F(layer, faces):
    _group(layer).addObject(_solid("F_" + layer.replace("-", "_"), layer, faces))


def P(layer, pts, closed):
    pts = [V(p[0] * K, p[1] * K, p[2] * K) for p in pts] + ([V(pts[0][0] * K, pts[0][1] * K, pts[0][2] * K)] if closed else [])
    obj = doc.addObject("Part::Feature", "P_" + layer.replace("-", "_"))
    obj.Shape = Part.makePolygon(pts)
    _group(layer).addObject(obj)

'''
FOOTER = '''
doc.recompute()
if App.GuiUp:
    import FreeCADGui
    FreeCADGui.SendMsgToActiveView("ViewFit")
    FreeCADGui.activeDocument().activeView().viewIsometric()
print("EPC-291 PV model:", COUNT["blocks"], "parts,", COUNT["instances"], "links,", COUNT["faces"], "faces")
'''


def _pts(entity):
    pts = [tuple(round(c, 4) for c in entity.dxf.get(f"vtx{i}")) for i in range(4)]
    out = [p for k, p in enumerate(pts) if k == 0 or p != pts[k - 1]]
    return out[:-1] if len(out) > 1 and out[0] == out[-1] else out


def _faces(entities):
    by_layer: Dict[str, list] = {}
    for e in entities:
        if e.dxftype() == "3DFACE":
            pts = _pts(e)
            if len(pts) >= 3:
                by_layer.setdefault(e.dxf.layer, []).append(pts)
    return by_layer


def _emit(fh, doc, used: set, stats: Dict[str, int]) -> None:
    """Writes the macro lines of one DXF document: its blocks (not yet written), then its modelspace."""
    for block in doc.blocks:
        if block.name.startswith("*") or block.name in used or not block.name.startswith("PV-"):
            continue
        used.add(block.name)
        fh.write(f"B({json.dumps(block.name)}, {json.dumps(_faces(block))})\n")
        stats["blocks"] += 1
    msp = doc.modelspace()
    faces = _faces(msp)
    for layer, quads in faces.items():
        fh.write(f"F({json.dumps(layer)}, {json.dumps(quads)})\n")
    for e in msp:
        if e.dxftype() == "INSERT":
            x, y, z = e.dxf.insert
            fh.write(f"I({json.dumps(e.dxf.name)}, {x:.4f}, {y:.4f}, {z:.4f}, {json.dumps(e.dxf.layer)})\n")
            stats["instances"] += 1
        elif e.dxftype() == "POLYLINE":
            fh.write(f"P({json.dumps(e.dxf.layer)}, {json.dumps([[round(c, 4) for c in v.dxf.location] for v in e.vertices])}, {str(bool(e.is_closed)).title()})\n")


def write_document(doc, path, title: str, colours: Dict[str, Any]) -> Path:
    """The macro of any ezdxf document made of `PV-` blocks and inserts (the part library uses it)."""
    stats = {"blocks": 0, "instances": 0}
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEADER.format(title=title.replace('"', ""), colours=json.dumps(colours)))
        _emit(fh, doc, set(), stats)
        fh.write(FOOTER)
    return Path(path)


def write(geometry: Dict[str, Any], result: Dict[str, Any], out_dir, name: str, stamp_date=None, parts: Optional[Dict[str, Any]] = None, level: str = "standard",
          sector_modules: int = pv_model3d.SECTOR_MODULES) -> Dict[str, Any]:
    """Writes `<name>_pv_model_3d_freecad.FCMacro` in `out_dir`. Returns {"macro": path, "blocks": n, "instances": n}."""
    if not geometry.get("tables"):
        raise ValueError("the layout has no tables to raise in 3D")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}_pv_model_3d_freecad.FCMacro"
    colours = {layer: ACI_RGB.get(aci, (0.6, 0.6, 0.6)) for layer, aci in pv_model3d.LAYERS.items()}
    stats = {"blocks": 0, "instances": 0}
    used: set = set()
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEADER.format(title=f"{name}_PV".replace('"', ""), colours=json.dumps(colours)))
        _emit(fh, pv_model3d.build_common(geometry, parts, level), used, stats)
        for tables in pv_model3d.sectors(geometry, sector_modules):
            _emit(fh, pv_model3d.build_sector(geometry, tables, parts, level), used, stats)
        fh.write(FOOTER)
    return {"macro": path, "blocks": stats["blocks"], "instances": stats["instances"]}
