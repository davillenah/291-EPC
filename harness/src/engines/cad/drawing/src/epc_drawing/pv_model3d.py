"""The 3D model of a photovoltaic plant, generated from its layout: a DXF with solid faces (3DFACE) that any CAD or BIM program opens (FreeCAD, AutoCAD, Revit import).

The person gives the structure in 2D (the site or the roof, the tables the layout engine placed); this module raises it: the tilted modules of every table, the rails and posts under them, the inverter
pads, the station and the ground, in metres, x east, y north, z up. It only draws what `epc_pv.plan_layout` placed and `epc_pv.run` counted; it calculates nothing, and the posts, rails and station
box are reference geometry (their sections are drawing conventions, not a structural design: wind and ballast are not calculated).

  write(geometry, result, out_dir, name, stamp_date, parts, level) -> path   `<name>_pv_model_3d.dxf` goes to the 3D folder of the transmittal

With `parts` (the module and inverter records of `epc_pv/data`, see `pv_parts`) the modules get frame, junction box and cells and the inverters their enclosure and terminals, on `PV-3D-REF-*` layers by data status.
"""
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from epc_drawing import pv_parts

Point = Tuple[float, float, float]
LAYERS = {"PV-3D-SUELO": 8, "PV-3D-MODULOS": 5, "PV-3D-ESTRUCTURA": 9, "PV-3D-CIMENTACION": 30, "PV-3D-INVERSORES": 7, "PV-3D-ESTACION": 4, "PV-3D-VALLADO": 1, **pv_parts.REF_LAYERS}
POST_M, RAIL_M, RAIL_DEPTH_M, SPACING_M = 0.1, 0.08, 0.06, 4.0
STATION_HEIGHT_M, PAD_HEIGHT_M, SOIL_M, MODULE_M = 2.6, 0.9, 0.15, 0.03
PLINTH_M = 0.3


def _add(msp, layer: str, faces: List[Tuple[Point, Point, Point, Point]]) -> None:
    for face in faces:
        msp.add_3dface(list(face), dxfattribs={"layer": layer})


def box(x: float, y: float, z: float, dx: float, dy: float, dz: float) -> List[Tuple[Point, Point, Point, Point]]:
    """The six faces of an axis-aligned box with its lowest corner at (x, y, z)."""
    p = [(x + i * dx, y + j * dy, z + k * dz) for k in (0, 1) for j in (0, 1) for i in (0, 1)]
    return [(p[0], p[1], p[3], p[2]), (p[4], p[5], p[7], p[6]), (p[0], p[1], p[5], p[4]), (p[2], p[3], p[7], p[6]), (p[0], p[2], p[6], p[4]), (p[1], p[3], p[7], p[5])]


def tilted_box(origin: Point, tilt_rad: float, u: float, s: float, w: float, du: float, ds: float, dw: float) -> List[Tuple[Point, Point, Point, Point]]:
    """A box in the plane of a table: `u` along x, `s` down the slope from the high (south) edge, `w` normal to the plane; the plane falls to the north by `tilt_rad`."""
    ox, oy, oz = origin
    c, sn = math.cos(tilt_rad), math.sin(tilt_rad)

    def at(du_, ds_, dw_):
        return (ox + u + du_, oy + (s + ds_) * c + dw_ * sn, oz - (s + ds_) * sn + dw_ * c)
    return [tuple(at(*q) for q in f) for f in ((( 0, 0, 0), (du, 0, 0), (du, ds, 0), (0, ds, 0)), ((0, 0, dw), (du, 0, dw), (du, ds, dw), (0, ds, dw)), ((0, 0, 0), (du, 0, 0), (du, 0, dw), (0, 0, dw)),
                                                         ((0, ds, 0), (du, ds, 0), (du, ds, dw), (0, ds, dw)), ((0, 0, 0), (0, ds, 0), (0, ds, dw), (0, 0, dw)), ((du, 0, 0), (du, ds, 0), (du, ds, dw), (du, 0, dw)))]


def _modules(geometry: Dict[str, Any], table: Dict[str, Any], tilt: float, rear_h: float) -> List[Any]:
    """Every module of a table, laid out in the rows and columns of the table (portrait or landscape)."""
    dims, gap = geometry["module"]["dimensions_mm"], geometry["module"]["gap_m"]
    long_m, short_m = dims[0] / 1000.0, dims[1] / 1000.0
    along, across = (short_m, long_m) if geometry["table"]["orientation"] == "portrait" else (long_m, short_m)
    per_row, faces = int(geometry["table"]["modules_per_row"]), []
    for i in range(int(table["modules"])):
        r, c = divmod(i, per_row)
        faces += tilted_box((table["x"], table["y"], rear_h), tilt, c * (along + gap), r * (across + gap), 0.0, along, across, MODULE_M)
    return faces


def embedment_m(geometry: Dict[str, Any]) -> float:
    """The depth of the posts below the surface: the embedment the structure record states (`geometry["foundation"]["embedment_m"]`), else 0. Nothing is assumed: a roof or a structure without
    a stated depth has no part below the surface, and a ground plant with embedded piles draws them on their own layer (`PV-3D-CIMENTACION`) so they are never mistaken for posts under the floor by error."""
    return float((geometry.get("foundation") or {}).get("embedment_m") or 0.0)


def _post(section: Optional[Dict[str, Any]], x: float, y: float, z0: float, height: float) -> List[Any]:
    """One post from its section (centred on x, y) or, without a section, the reference square post."""
    if section is None:
        return box(x - POST_M / 2, y - POST_M / 2, z0, POST_M, POST_M, height)
    return [f for poly in section["polygons"] for f in pv_parts.prism(poly, x, y, z0, height)]


def _supports(table: Dict[str, Any], slope: float, tilt: float, rear_h: float, embed: float = 0.0, section: Optional[Dict[str, Any]] = None) -> Tuple[List[Any], List[Any], List[Any]]:
    """(rails, posts, buried parts) of a table: two rails along x at a quarter and three quarters of the slope, posts every `SPACING_M` under each rail; the part of each post below the surface (`embed`) is separate.
    With a `section` (from the structure record) the posts have that profile; the caller puts them on the layer of its status."""
    rails, posts, buried = [], [], []
    n = max(int(math.ceil(table["width_m"] / SPACING_M)) + 1, 2)
    for f in (0.25, 0.75):
        s = slope * f
        rails += tilted_box((table["x"], table["y"], rear_h), tilt, 0.0, s - RAIL_M / 2, -RAIL_DEPTH_M - MODULE_M, table["width_m"], RAIL_M, RAIL_DEPTH_M)
        top = rear_h - s * math.sin(tilt) - RAIL_DEPTH_M - MODULE_M
        y = table["y"] + s * math.cos(tilt)
        for k in range(n):
            x = table["x"] + POST_M / 2 + k * (table["width_m"] - POST_M) / (n - 1)
            posts += _post(section, x, y, 0.0, max(top, 0.0))
            if embed > 0:
                buried += _post(section, x, y, -embed, embed)
    return rails, posts, buried


def _plane_point(origin: Point, tilt: float, u: float, s: float, w: float) -> Point:
    """The point at (u, s, w) of a table plane (same frame as `tilted_box`)."""
    c, sn = math.cos(tilt), math.sin(tilt)
    return (origin[0] + u, origin[1] + s * c + w * sn, origin[2] - s * sn + w * c)


def _module_details(geometry: Dict[str, Any], table: Dict[str, Any], tilt: float, rear_h: float, record, level: str) -> Dict[str, List[Any]]:
    """Frame, junction box and cells of every module of a table (layer -> faces), from the module record."""
    dims, gap = geometry["module"]["dimensions_mm"], geometry["module"]["gap_m"]
    long_m, short_m = dims[0] / 1000.0, dims[1] / 1000.0
    portrait = geometry["table"]["orientation"] == "portrait"
    along, across = (short_m, long_m) if portrait else (long_m, short_m)
    detail = pv_parts.module_detail(record, long_m, short_m, MODULE_M, level)       # u across the short side, s along the long side
    per_row, out = int(geometry["table"]["modules_per_row"]), {}
    for i in range(int(table["modules"])):
        r, c = divmod(i, per_row)
        u0, s0 = c * (along + gap), r * (across + gap)
        for layer, faces in detail.items():
            for f in faces:
                pts = [(p[1], p[0], p[2]) if not portrait else p for p in f]            # landscape: the long side runs along x
                out.setdefault(layer, []).append(tuple(_plane_point((table["x"], table["y"], rear_h), tilt, u0 + p[0], s0 + p[1], p[2]) for p in pts))
    return out


def _inverters(msp, geometry: Dict[str, Any], records: Dict[str, Any], level: str) -> None:
    """The inverters: the enclosure of the record on a reference plinth (its terminals under and on it), or the plain pad when the record is missing."""
    for inv in geometry["inverters"]:
        if inv.get("x") is None:
            continue
        det = pv_parts.inverter_detail(records.get(inv.get("catalog_id") or inv.get("id")), level)
        if det is None:
            _add(msp, "PV-3D-INVERSORES", box(inv["x"] - inv["width_m"] / 2, inv["y"] - inv["depth_m"] / 2, 0, inv["width_m"], inv["depth_m"], PAD_HEIGHT_M))
            continue
        w, h, d = det["size"]
        x0, y0 = inv["x"] - w / 2, inv["y"] - d / 2
        _add(msp, "PV-3D-REF-FALLBACK", box(x0, y0, 0, w, d, PLINTH_M))
        _add(msp, "PV-3D-INVERSORES", box(x0, y0, PLINTH_M, w, d, h))
        for layer, faces in det["parts"]:       # record frame: x width, y height, z depth (wall at 0); the front looks south
            _add(msp, layer, [tuple((x0 + p[0], y0 + d - p[2], PLINTH_M + p[1]) for p in f) for f in faces])


def build(geometry: Dict[str, Any], result: Dict[str, Any], parts: Optional[Dict[str, Any]] = None, level: str = "standard"):
    """The ezdxf document of the plant (see the module docstring); raises ValueError when the layout has no modules.
    `parts` are the equipment records, `{"module": record, "inverters": {id: record}}`; without them the plain boxes are drawn. `level` is `low` (no detail), `standard` or `full` (one face per cell)."""
    parts = parts or {}
    import ezdxf
    if not geometry.get("tables"):
        raise ValueError("the layout has no tables to raise in 3D")
    doc = ezdxf.new("R2018", setup=True)
    doc.units = 6
    for name, colour in LAYERS.items():
        doc.layers.add(name, color=colour)
    msp = doc.modelspace()
    slope = float(geometry["table"]["slope_m"])
    front = float(geometry["module"]["front_clearance_m"] or 0.0)
    site = geometry["site"]
    _add(msp, "PV-3D-SUELO", box(0, 0, -SOIL_M, site["width_m"], site["length_m"], SOIL_M))
    s = site["setback_m"]
    msp.add_polyline3d([(s, s, 0), (site["width_m"] - s, s, 0), (site["width_m"] - s, site["length_m"] - s, 0), (s, site["length_m"] - s, 0)], close=True, dxfattribs={"layer": "PV-3D-VALLADO"})
    for table in geometry["tables"]:
        tilt = math.radians(float(geometry["tilts_deg"][table["array"]]))
        rear_h = front + slope * math.sin(tilt)
        _add(msp, "PV-3D-MODULOS", _modules(geometry, table, tilt, rear_h))
        if parts.get("module") is not None:
            for layer, faces in _module_details(geometry, table, tilt, rear_h, parts["module"], level).items():
                _add(msp, layer, faces)
        section = pv_parts.post_section(parts.get("structure"))
        rails, posts, buried = _supports(table, slope, tilt, rear_h, embedment_m(geometry), section)
        _add(msp, "PV-3D-ESTRUCTURA", rails + ([] if section else posts))
        if section:
            _add(msp, section["layer"], posts)
        _add(msp, "PV-3D-CIMENTACION", buried)
    _inverters(msp, geometry, parts.get("inverters") or {}, level)
    st = geometry["station"]
    _add(msp, "PV-3D-ESTACION", box(st["x"], st["y"], 0, st["width_m"], st["depth_m"], STATION_HEIGHT_M))
    return doc


def write(geometry: Dict[str, Any], result: Dict[str, Any], out_dir, name: str, stamp_date=None, parts: Optional[Dict[str, Any]] = None, level: str = "standard") -> Path:
    """Writes `<name>_pv_model_3d.dxf` under `out_dir` (the stem keeps the `_model_3d` mark that sends it to the 3D folder of the transmittal)."""
    from epc_dxf import deliverable
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}_pv_model_3d.dxf"
    deliverable.finish_draft(build(geometry, result, parts, level), path, None, stamp_date, f"{name}_pv_model_3d")
    return path
