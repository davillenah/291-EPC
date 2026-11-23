"""A library of 3D parts regenerated from their descriptions: any equipment record with a `geometry` (inverters, accessories, module formats and technologies, mounting structures), used by the PV engine or not.

The record is the description: its `geometry.elements` give each element (a box by `size_mm`, or a profile run by `profile_or_accessory_id` and `length_mm`) with its position and rotation, and the optional
`features` list gives the small details that make a part recognisable (the dot at a corner, a label field, a hole): `{id, kind: dot|box|hole, on: element id, face: front|back|left|right|top|bottom, position_mm: [u, v],
size_mm: [w, h], depth_mm, status}`; `position_mm` is measured on the face from its lower-left corner seen from outside. Nothing is invented: an element without a size is skipped and listed, a feature without a
position is skipped, and every solid takes the layer of the status of its datum (`PV-3D-REF-*`), so a viewer sees at once what is verified. Units: metres in the model, millimetres in the records.

  faces(record) -> {"faces": {layer: [quad]}, "skipped": [ids]}      the model of one record, in the frame of the record seen with z up
  write(records, out_dir, name, stamp_date) -> {"dxf": path, "freecad": path, "parts": n, "skipped": {record id: [ids]}}      every record as one block, side by side
"""
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from epc_drawing import pv_parts

Quad = Tuple[Tuple[float, float, float], ...]
LAYER_FEATURE = "PV-3D-LIB-FEATURE"
LAYER_CUT = "PV-3D-LIB-CUT"
LAYERS = {**pv_parts.REF_LAYERS, LAYER_FEATURE: 2, LAYER_CUT: 1}
FACES = ("front", "back", "left", "right", "top", "bottom")
BLOCK_GAP_M = 0.5


def _rotate(point, angles_deg, origin):
    """The point turned about `origin` by the Euler angles (x, then y, then z), in degrees."""
    x, y, z = (point[i] - origin[i] for i in range(3))
    ax, ay, az = (math.radians(a) for a in angles_deg)
    y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
    x, z = x * math.cos(ay) + z * math.sin(ay), -x * math.sin(ay) + z * math.cos(ay)
    x, y = x * math.cos(az) - y * math.sin(az), x * math.sin(az) + y * math.cos(az)
    return (x + origin[0], y + origin[1], z + origin[2])


def _box(o, size) -> List[Quad]:
    x, y, z = o
    dx, dy, dz = size
    p = [(x + i * dx, y + j * dy, z + k * dz) for k in (0, 1) for j in (0, 1) for i in (0, 1)]
    return [(p[0], p[1], p[3], p[2]), (p[4], p[5], p[7], p[6]), (p[0], p[1], p[5], p[4]), (p[2], p[3], p[7], p[6]), (p[0], p[2], p[6], p[4]), (p[1], p[3], p[7], p[5])]


def _mm(values) -> Tuple[float, ...]:
    return tuple(float(v) / 1000.0 for v in values)


def _turn(faces: List[Quad], element: Dict[str, Any]) -> List[Quad]:
    o, ang = _mm(element.get("position_mm") or (0, 0, 0)), element.get("rotation_deg") or (0, 0, 0)
    return [tuple(_rotate(p, ang, o) for p in f) for f in faces] if any(ang) else faces


def _profile_faces(element: Dict[str, Any], profiles: Dict[str, Any]) -> Optional[List[Quad]]:
    """A profile run: the section of the profile extruded along x for `length_mm` from the element position."""
    prof = profiles.get(element.get("profile_or_accessory_id"))
    if not prof or not element.get("length_mm"):
        return None
    polys = pv_parts._section_polygons(prof.get("section_type"), prof.get("dimensions_mm") or {})
    if not polys:
        return None
    ox, oy, oz = _mm(element.get("position_mm") or (0, 0, 0))
    length, out = float(element["length_mm"]) / 1000.0, []
    for poly in polys:
        for f in pv_parts.prism(poly, 0.0, 0.0, 0.0, length):
            out.append(tuple((ox + p[2], oy + p[0], oz + p[1]) for p in f))      # section (x, y) -> (y, z); the run goes along x
    return out


def _feature_faces(feature: Dict[str, Any], host: Tuple[Tuple[float, float, float], Tuple[float, float, float]]) -> Optional[List[Quad]]:
    """The solid of a feature on a face of its host box ((origin), (size) in metres); None when the feature gives no position, size or a known face."""
    face, pos, size = feature.get("face"), feature.get("position_mm"), feature.get("size_mm")
    if face not in FACES or not pos or not size:
        return None
    (x, y, z), (dx, dy, dz) = host
    u, v = float(pos[0]) / 1000.0, float(pos[1]) / 1000.0
    w, h = float(size[0]) / 1000.0, float(size[1]) / 1000.0 if len(size) > 1 else float(size[0]) / 1000.0
    depth = float(feature.get("depth_mm") or 0.5) / 1000.0
    out = abs(depth)
    # (origin of the solid, its size) per face; u, v run right and up on the face seen from outside
    places = {"top": ((x + u, y + v, z + dz), (w, h, out)), "bottom": ((x + u, y + v, z - out), (w, h, out)), "front": ((x + u, y - out, z + v), (w, out, h)),
              "back": ((x + dx - u - w, y + dy, z + v), (w, out, h)), "left": ((x - out, y + dy - u - w, z + v), (out, w, h)), "right": ((x + dx, y + u, z + v), (out, w, h))}
    o, s = places[face]
    if depth < 0:      # a recess: drawn as a solid sunk into the host
        o = tuple(o[i] + (out * (1 if face in ("bottom", "front", "left") else -1) if i == {"top": 2, "bottom": 2, "front": 1, "back": 1, "left": 0, "right": 0}[face] else 0) for i in range(3))
    return _box(o, s)


def _element_solid(e: Dict[str, Any], profiles: Dict[str, Any]):
    """(faces, host box or None) of one element: a box by `size_mm` (turned by its rotation) or a profile run; None faces when it gives too little."""
    if not e.get("size_mm"):
        return _profile_faces(e, profiles), None
    size, o = _mm(e["size_mm"]), _mm(e.get("position_mm") or (0, 0, 0))
    return _turn(_box(o, size), e), (o, size)


def _features(record: Dict[str, Any], hosts: Dict[str, Any], layers: Dict[str, List[Quad]], skipped: List[str]) -> None:
    default_host = next(iter(hosts.values()), None)
    for f in record.get("features", []):
        host = hosts.get(f.get("on"), default_host)
        solid = _feature_faces(f, host) if host else None
        if solid:
            layers.setdefault(LAYER_CUT if (f.get("depth_mm") or 0) < 0 else LAYER_FEATURE, []).extend(solid)
        else:
            skipped.append(f.get("id", "feature"))


def faces(record: Dict[str, Any]) -> Dict[str, Any]:
    """The model of one record: {"faces": {layer: [quad]}, "skipped": [ids of elements or features that give too little to draw]}."""
    profiles = {p["id"]: p for p in record.get("profiles", [])}
    layers: Dict[str, List[Quad]] = {}
    skipped: List[str] = []
    hosts: Dict[str, Any] = {}
    for e in (record.get("geometry") or {}).get("elements", []):
        solid, host = _element_solid(e, profiles)
        if host:
            hosts[e["id"]] = host
        if solid:
            layers.setdefault(pv_parts.layer_for(e.get("status")), []).extend(solid)
        else:
            skipped.append(e["id"])
    _features(record, hosts, layers, skipped)
    return {"faces": layers, "skipped": skipped}


def _extent(layers: Dict[str, List[Quad]]) -> Tuple[float, float, float, float]:
    pts = [p for fs in layers.values() for f in fs for p in f]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)) if pts else (0.0, 0.0, 0.0, 0.0)


def build(records: List[Dict[str, Any]]):
    """(ezdxf document, {record id: skipped ids}): one block per record that has something to draw, laid out in a row."""
    import ezdxf
    from epc_dxf import new_document
    doc = new_document("R2018", setup=True)
    doc.units = 6
    for name, colour in LAYERS.items():
        doc.layers.add(name, color=colour)
    msp, x, skipped = doc.modelspace(), 0.0, {}
    for record in records:
        made = faces(record)
        skipped[record["id"]] = made["skipped"]
        if not made["faces"]:
            continue
        x0, y0, x1, _ = _extent(made["faces"])
        block = doc.blocks.new("PV-PART-" + record["id"].replace(" ", "_"))
        for layer, quads in made["faces"].items():
            for q in quads:
                block.add_3dface(list(q), dxfattribs={"layer": layer})
        msp.add_blockref(block.name, (x - x0, -y0, 0.0), dxfattribs={"layer": pv_parts.FALLBACK_LAYER})
        x += (x1 - x0) + BLOCK_GAP_M
    return doc, skipped


def write(records: List[Dict[str, Any]], out_dir, name: str, stamp_date=None) -> Dict[str, Any]:
    """Writes `<name>_part_library.dxf` and `<name>_part_library_freecad.FCMacro` in `out_dir`."""
    from epc_dxf import deliverable
    from epc_drawing import pv_freecad
    doc, skipped = build(records)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dxf = out / f"{name}_part_library.dxf"
    deliverable.finish_draft(doc, dxf, None, stamp_date, dxf.stem)
    macro = out / f"{name}_part_library_freecad.FCMacro"
    pv_freecad.write_document(doc, macro, f"{name}_library", {k: v for k, v in pv_parts_colours().items()})
    return {"dxf": dxf, "freecad": macro, "parts": sum(1 for b in doc.blocks if b.name.startswith("PV-PART-")), "skipped": {k: v for k, v in skipped.items() if v}}


def pv_parts_colours() -> Dict[str, Tuple[float, float, float]]:
    from epc_drawing import pv_freecad
    return {layer: pv_freecad.ACI_RGB.get(aci, (0.6, 0.6, 0.6)) for layer, aci in LAYERS.items()}
