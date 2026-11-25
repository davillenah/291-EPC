"""The library of parts of a tray system, all by code: every kind of tray (straight, elbows, vertical bend, tee, cross, reducer, end cap, divider, splice plate, cover), the supports (wall bracket,
heavy bracket, trapeze hanger, threaded rod, strut channel, rod clamp, ceiling plate) and the fasteners (bolt, nut, washer, coupler), each as a solid with our own code and bilingual name.

`pieces(width_m, height_m)` returns the list; the caller draws or writes each one (one DXF per piece: `epc_plan.write_dxf_3d`). Sizes are `params.json` (`detail.ladder` and `detail.library`): our own
drawing values, to be confirmed. A pure function of its arguments.
"""
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from epc_plan import core, tray_code
from epc_plan import tray_accessories as A, tray_hardware as H, tray_solid as T

TRAY_LAYER, SUPPORT_LAYER, FASTENER_LAYER = "ELEC-BANDEJA", "MEC-SOPORTE", "MEC-FIJACION"


def _sizes() -> Tuple[Dict[str, float], Dict[str, float], float]:
    ladder = core.PARAMS["detail"]["ladder"]
    keys = ("rail", "rung", "rung_thick", "rung_pitch", "foot", "curl", "lip", "jog", "slot_pitch", "slot", "slot_height", "floor_margin", "hole_pitch", "hole", "wire", "wire_pitch", "joint", "bolt")
    return {k: ladder[k + "_m"] for k in keys}, core.PARAMS["detail"]["library"], ladder["elbow_radius_m"]


def _piece(code: Dict[str, Any], group: str, layer: str, mesh: Dict[str, list], tag_of: str = "") -> Dict[str, Any]:
    xs = [v[0] for v in mesh["vertices"]] or [0.0, 0.0]
    return {"id": code["code"], "tag": code["code"], "code": code["code"], "name": code["name"], "group": group, "layer": layer, "kind": "tray_part", "discipline": "electricidad",
            "level": "", "shape": "box", "path": [[round(min(xs), 4), 0.0, 0.0], [round(max(xs) + 1e-3, 4), 0.0, 0.0]], "mesh": mesh}


def _tray_code(kind: str, width: float, height: float, fitting: str) -> Dict[str, Any]:
    return {"code": tray_code.code(kind, width * 1000, height * 1000, fitting), "name": tray_code.name(kind, fitting)}


def _path(run: List[Tuple[float, float, float]], radius: float, links: int = 5) -> List[Tuple[float, float, float]]:
    return T.path3d(run, radius, radius, links)


def _fitting(kind: str, width: float, depth: float, p: Dict[str, float], q: Dict[str, float], radius: float, fitting: str) -> Dict[str, list]:
    leg, side = q["leg_m"], q["side_m"]
    if fitting == "straight":
        return T.tray_mesh([(0, 0, 0), (q["straight_m"], 0, 0)], width, depth, p, kind)
    if fitting == "elbow90":
        return T.tray_mesh(_path([(0, 0, 0), (leg, 0, 0), (leg, leg, 0)], radius), width, depth, p, kind)
    if fitting == "elbow45":
        return T.tray_mesh(_path([(0, 0, 0), (leg, 0, 0), (leg + side * math.cos(math.pi / 4), side * math.sin(math.pi / 4), 0)], radius), width, depth, p, kind)
    if fitting == "elbow_adjustable":
        return T.tray_mesh(_path([(0, 0, 0), (leg, 0, 0), (leg + side * math.cos(math.pi / 3), side * math.sin(math.pi / 3), 0)], radius), width, depth, p, kind)
    if fitting == "vertical_bend":
        return T.tray_mesh(_path([(0, 0, 0), (leg, 0, 0), (leg + side, 0, side)], radius), width, depth, p, kind)
    return _junction(kind, width, depth, p, q, fitting)


def _junction(kind: str, width: float, depth: float, p: Dict[str, float], q: Dict[str, float], fitting: str) -> Dict[str, list]:
    leg = q["leg_m"]
    if fitting in ("tee", "cross"):
        parts = [T.tray_mesh([(-leg, 0, 0), (leg, 0, 0)], width, depth, p, kind), T.tray_mesh([(0, 0, 0), (0, leg, 0)], width, depth, p, kind)]
        if fitting == "cross":
            parts.append(T.tray_mesh([(0, -leg, 0), (0, 0, 0)], width, depth, p, kind))
        return H.join(*parts)
    if fitting in ("reduction_central", "reduction_side"):
        reduced = T.reducer_mesh((0, 0, 0), (leg, 0, 0), (width, width / 2), depth, p, kind)
        return reduced if fitting == "reduction_central" else H.side_reducer(reduced, leg, (width, width / 2))
    return _accessory(kind, width, depth, p, q, fitting)


def _plate(size: Tuple[float, float, float], at: Tuple[float, float, float]) -> Dict[str, list]:
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    T._box(vertices, faces, at, H.AXES, size)
    return {"vertices": vertices, "faces": faces}


def _accessory(kind: str, width: float, depth: float, p: Dict[str, float], q: Dict[str, float], fitting: str) -> Dict[str, list]:
    if fitting == "end":
        return H.join(T.tray_mesh([(0, 0, 0), (q["leg_m"], 0, 0)], width, depth, p, kind), _plate((q["end_thick_m"], width, depth), (q["leg_m"] + q["end_thick_m"] / 2, 0, 0)))
    if fitting == "divider":
        return _plate((q["straight_m"], q["divider_thick_m"], depth * 0.9), (q["straight_m"] / 2, 0, 0))
    if fitting == "splice":
        n = q["splice_len_m"]
        return H.join(*[_plate((n, q["splice_thick_m"], depth * 0.7), (0.0, s * (width / 2 + q["splice_thick_m"] / 2), 0)) for s in (-1, 1)])
    return _plate((q["straight_m"], width + 2 * q["lid_flange_m"], p["cover"] if "cover" in p else 0.004), (q["straight_m"] / 2, 0, 0))     # cover


COVERS = {"straight": "cover", "elbow90": "cover_elbow90", "elbow45": "cover_elbow45", "elbow_adjustable": "cover_adjustable", "tee": "cover_tee", "cross": "cover_cross", "vertical_bend": "cover_link"}


def _runs(fitting: str, q: Dict[str, float], radius: float) -> List[List[Tuple[float, float, float]]]:
    """The axes of the stretches a fitting is made of, for its cover."""
    leg, side = q["leg_m"], q["side_m"]
    turn = {"elbow90": (leg, leg), "elbow45": (leg + side * math.cos(math.pi / 4), side * math.sin(math.pi / 4)), "elbow_adjustable": (leg + side * math.cos(math.pi / 3), side * math.sin(math.pi / 3))}
    if fitting in turn:
        return [_path([(0, 0, 0), (leg, 0, 0), (turn[fitting][0], turn[fitting][1], 0)], radius)]
    if fitting == "vertical_bend":
        return [_path([(0, 0, 0), (leg, 0, 0), (leg + side, 0, side)], radius)]
    arms = {"straight": [[(0, 0, 0), (q["straight_m"], 0, 0)]], "tee": [[(-leg, 0, 0), (leg, 0, 0)], [(0, 0, 0), (0, leg, 0)]],
            "cross": [[(-leg, 0, 0), (leg, 0, 0)], [(0, -leg, 0), (0, leg, 0)]]}
    return arms[fitting]


def _covers(width: float, depth: float) -> List[Dict[str, Any]]:
    """The cover of the straight and of each fitting, for every kind that takes one (a wire-mesh tray has none)."""
    p, q, radius = _sizes()
    p = dict(p, cover=core.PARAMS["detail"]["ladder"]["cover_m"])
    return [_piece(_tray_code(kind, width, depth, COVERS[fitting]), "tray", TRAY_LAYER, H.join(*[T.cover_mesh(path, width, depth, p) for path in _runs(fitting, q, radius)]))
            for kind in ("escalera", "perforada", "ciega", "canal") for fitting in COVERS]


def _trays(width: float, depth: float) -> List[Dict[str, Any]]:
    p, q, radius = _sizes()
    out = []
    for kind in ("escalera", "perforada", "ciega", "alambre", "canal"):
        for fitting in ("straight", "elbow90", "elbow45", "elbow_adjustable", "vertical_bend", "tee", "cross", "reduction_central", "reduction_side", "end", "splice", "divider", "cover"):
            if fitting == "divider" and kind in ("escalera", "alambre") or fitting == "cover":
                continue                                                  # the covers come from `_covers`, one for each fitting
            out.append(_piece(_tray_code(kind, width, depth, fitting), "tray", TRAY_LAYER, _fitting(kind, width, depth, p, q, radius, fitting)))
    return out


def _supports(width: float, depth: float) -> List[Dict[str, Any]]:
    q = _sizes()[1]
    size = f"{round(width * 1000)}x{round(depth * 1000)}"
    wall = H.wall_bracket(q, width, 0.1, 0.04, q["plate_m"], 0.15)
    named = [(_tray_code("escalera", width, depth, "bracket_wall"), wall), (_tray_code("escalera", width, depth, "bracket_heavy"), H.heavy_bracket(q, width)),
             (tray_code.part("trapeze", size), H.trapeze(q, width, 0.5)), (tray_code.part("rod", f"M{round(q['rod_m'] * 1000)}x{round(q['rod_len_m'] * 1000)}"), H.rod(q)),
             (tray_code.part("strut", f"{round(q['strut_m'] * 1000)}x{round(q['strut_m'] * 1000)}x{round(q['strut_len_m'] * 1000)}"), H.strut(q)),
             (tray_code.part("clamp", f"M{round(q['rod_m'] * 1000)}"), H.clamp(q)), (tray_code.part("ceiling_plate", f"M{round(q['rod_m'] * 1000)}"), H.ceiling_plate(q))]
    return [_piece(c, "support", SUPPORT_LAYER, m) for c, m in named]


def _fasteners() -> List[Dict[str, Any]]:
    q = _sizes()[1]
    m = f"M{round(q['bolt_m'] * 1000)}"
    named = [(tray_code.part("bolt", f"{m}x{round(q['bolt_len_m'] * 1000)}"), H.bolt(q)), (tray_code.part("nut", m), H.nut(q)), (tray_code.part("washer", m), H.washer(q)),
             (tray_code.part("coupler", f"M{round(q['rod_m'] * 1000)}"), H.coupler(q))]
    return [_piece(c, "fastener", FASTENER_LAYER, mesh) for c, mesh in named]


def _accessories(width: float, depth: float) -> List[Dict[str, Any]]:
    q = _sizes()[1]
    mm = lambda x: round(x * 1000)                                          # noqa: E731
    named = [(_tray_code("escalera", width, depth, "bracket_adjustable"), A.adjustable_bracket(q, width, 0.15)), (_tray_code("escalera", width, depth, "splice_lateral"), A.lateral_splice(q, depth)),
             (_tray_code("escalera", width, depth, "union_articulated"), A.articulated_union(q, depth)), (tray_code.part("mounting_plate", f"{mm(q['plate_m'])}x{mm(q['plate_m'])}"), A.mounting_plate(q)),
             (tray_code.part("carriage_bolt", f"M{mm(q['bolt_m'])}x{mm(q['bolt_len_m'])}"), A.carriage_bolt(q, q["bolt_m"])),
             (tray_code.part("carriage_bolt", f"3-8x{mm(q['bolt_len_m'])}"), A.carriage_bolt(q, q["bolt38_m"])),
             (tray_code.part("retainer_bolt", f"M{mm(q['bolt_m'])}"), A.retainer_bolt(q)), (tray_code.part("suspension_clamp", f"M{mm(q['rod_m'])}"), A.suspension_clamp(q)),
             (tray_code.part("fixing_clamp", f"M{mm(q['bolt_m'])}"), A.fixing_clamp(q)), (tray_code.part("ground_clamp", f"M{mm(q['bolt_m'])}"), A.grounding_clamp(q))]
    return [_piece(c, "support" if "BN" in c["code"] or "PUM" in c["code"] else "fastener", SUPPORT_LAYER if "BN" in c["code"] or "PUM" in c["code"] else FASTENER_LAYER, m) for c, m in named]


def pieces(width_m: float = 0.3, height_m: float = 0.09) -> List[Dict[str, Any]]:
    """Every part of the system for a tray `width_m` wide and `height_m` high, one solid each (id, code, bilingual name, group, layer, path, mesh)."""
    if width_m <= 0 or height_m <= 0:
        raise core.PlanError("err_detail_number", key="tray size")
    return _trays(width_m, height_m) + _covers(width_m, height_m) + _supports(width_m, height_m) + _fasteners() + _accessories(width_m, height_m)
