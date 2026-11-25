"""From the solids of the services to the parts they are built from (the fabrication model, towards LOD 400): every run becomes its straight pieces with their cut length and the fittings
between them, and the horizontal runs get their supports. Each part is a solid like any other (it goes into the scene, the 3D DXF and the sections) and a row of the take-off.

    parts(solids)                  -> straights (cut to the fittings), elbows at the bends, tees where a run ends on another, reducers where two runs of different size meet end to end
    supports(solids, spec)         -> the hangers of the horizontal runs under a slab: a trapeze (two rods and a channel) for trays and ducts, a rod and a clamp for pipes
    takeoff(parts)                 -> what to cut and what to buy: straight lengths by size, fittings by type, size and angle, supports by type and the rod they need

What is geometry is done here; what is design is asked for. The spacing of the supports and the underside of the slab they hang from are inputs (`spec`: no default, they come from the
standard, the manufacturer and the building). The sizes a part is drawn with when nobody says them (the leg of an elbow in widths of the run, the rod, the channel) are drawing data in
`params.json` (`detail`), which `spec` overrides; they are not design values. A fitting is found from the geometry alone: nothing is added to the drawing to have it.

Limits: one fitting per bend (a mitred elbow of the size of the run), a tee is the piece of the main run where the branch arrives (the main run is not split in two straights), no flanges,
couplings, covers or fixings to the structure, and supports only for horizontal runs under a slab.
"""
import math
from typing import Any, Dict, List, Optional, Tuple

from epc_plan import core
from epc_plan import solid as S
from epc_plan.core import PlanError

V3 = Tuple[float, float, float]
TOUCH = 0.02                               # metres: two ends this close are joined
SUPPORT_LAYER = "MEC-SOPORTE"


# ---------------------------------------------------------------- vectors
def _sub(a, b) -> V3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b, k: float = 1.0) -> V3:
    return (a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k)


def _dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(a) -> V3:
    n = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def _len(a, b) -> float:
    return math.dist(a, b)


def _r(p) -> List[float]:
    return [round(c, 4) for c in p]


# ---------------------------------------------------------------- swept meshes
def _ring_at(a, b, ring: List[Tuple[float, float]]) -> List[V3]:
    """The section of a run as offsets from its axis, for the stretch a-b."""
    side, up = S._frame(tuple(a), tuple(b))
    return [_add((s * side[0], s * side[1], s * side[2]), up, u) for s, u in ring]


def _mitred(offsets: List[V3], d1: V3, d2: V3) -> List[V3]:
    """The offsets of a section slid along the run until they lie in the plane that halves the bend between the directions `d1` and `d2`."""
    n = _unit(_add(d1, d2))
    den = _dot(d1, n) or 1.0
    return [_add(o, d1, -_dot(o, n) / den) for o in offsets]


def _square(offsets: List[V3], d: V3) -> List[V3]:
    """Offsets brought back square to a direction (what a mitred section is for the stretch that leaves the bend)."""
    return [_add(o, d, -_dot(o, d)) for o in offsets]


def _skin(rings: List[List[V3]]) -> Dict[str, Any]:
    """A closed solid through a row of sections: the sides between each two and a cap at each end."""
    n = len(rings[0])
    vertices = [_r(p) for ring in rings for p in ring]
    faces = [[r * n + k, r * n + (k + 1) % n, (r + 1) * n + (k + 1) % n, (r + 1) * n + k] for r in range(len(rings) - 1) for k in range(n)]
    last = (len(rings) - 1) * n
    for base, order in ((0, -1), (last, 1)):
        centre = len(vertices)
        vertices.append(_r([sum(p[i] for p in rings[base // n]) / n for i in range(3)]))
        faces += [[centre, base + (k + 1) % n, base + k, centre][::order] for k in range(n)]
    return {"vertices": vertices, "faces": faces}


def _elbow_mesh(a, corner, b, ring: List[Tuple[float, float]]) -> Dict[str, Any]:
    """A mitred elbow from `a` through `corner` to `b`: the section at each end and, at the corner, the section in the plane that halves the bend."""
    d1, d2 = _unit(_sub(corner, a)), _unit(_sub(b, corner))
    first = _ring_at(a, corner, ring)
    middle = _mitred(first, d1, d2)
    return _skin([[_add(a, o) for o in first], [_add(corner, o) for o in middle], [_add(b, o) for o in _square(middle, d2)]])


def _reducer_mesh(a, b, big: List[Tuple[float, float]], small: List[Tuple[float, float]]) -> Dict[str, Any]:
    return _skin([[_add(a, o) for o in _ring_at(a, b, big)], [_add(b, o) for o in _ring_at(a, b, small)]])


# ---------------------------------------------------------------- parts of a run
def _size(s: Dict[str, Any]) -> str:
    """The size of a run as it is ordered: its diameter, or its width by its height, in millimetres."""
    if s["section"] == "round":
        return f"D{round(s['width_m'] * 1000)}"
    return f"{round(s['width_m'] * 1000)}x{round(s['height_m'] * 1000)}"


def _part(s: Dict[str, Any], part: str, n: int, mesh: Dict[str, Any], **more) -> Dict[str, Any]:
    keep = {k: s[k] for k in ("kind", "discipline", "level", "sheet", "layer", "section", "width_m", "height_m")}
    return dict(keep, id=f"{s['id']}:{part}{n}", tag=f"{s['tag']}", run=s["id"], part=part, size=_size(s), shape="run", mesh=mesh, **more)


def _angle(a, corner, b) -> float:
    """The turn of a bend in degrees (0 = straight on)."""
    c = max(-1.0, min(1.0, _dot(_unit(_sub(corner, a)), _unit(_sub(b, corner)))))
    return round(math.degrees(math.acos(c)), 1)


def _legs(path: List[V3], leg: float) -> List[float]:
    """The length an elbow takes of each stretch at each inner vertex of a path: its leg, or less where two bends are closer than two legs (0 where the run goes straight on)."""
    out = [0.0]
    for i in range(1, len(path) - 1):
        bent = _angle(path[i - 1], path[i], path[i + 1]) > 0.5
        out.append(min(leg, _len(path[i - 1], path[i]) / 2, _len(path[i], path[i + 1]) / 2) if bent else 0.0)
    return out + [0.0]


def _toward(a, b, d: float) -> V3:
    return _add(a, _unit(_sub(b, a)), d)


def _straight_mesh(piece: Dict[str, Any], ladder: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The mesh of a straight piece: the rails and rungs of a ladder tray when `ladder` says its layer is one, else the swept box."""
    if ladder and piece.get("layer") in ladder["layers"] and piece["section"] == "rect":
        from epc_plan import tray_solid
        kind = ladder.get("kinds", {}).get(piece["layer"], "escalera")
        return tray_solid.tray_mesh([tuple(p) for p in piece["path"]], piece["width_m"], piece["height_m"], ladder["sizes"], kind)
    return S.mesh(piece)


def _elbow_mesh_for(s: Dict[str, Any], a, corner, b, ring, ladder: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The mesh of an elbow: the tray of its kind turned through the bend (inner radius of the catalogue, never more than the legs) on a ladder layer, else the swept box."""
    if not (ladder and s.get("layer") in ladder["layers"] and s["section"] == "rect"):
        return _elbow_mesh(a, corner, b, ring)
    from epc_plan import tray_solid
    reach = min(_len(a, corner), _len(corner, b))
    radius = min(ladder["elbow_radius"] + s["width_m"] / 2, reach)
    path = tray_solid.path3d([a, corner, b], radius, radius, ladder["links"])
    return tray_solid.tray_mesh(path, s["width_m"], s["height_m"], ladder["sizes"], ladder.get("kinds", {}).get(s["layer"], "escalera"))


def _run_parts(s: Dict[str, Any], ring: List[Tuple[float, float]], leg: float, ladder: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """One run as its straight pieces (cut to the elbows) and the elbow at each bend."""
    path = [tuple(p) for p in s["path"]]
    legs = _legs(path, leg)
    out = []
    for i in range(len(path) - 1):
        a, b = _toward(path[i], path[i + 1], legs[i]), _toward(path[i + 1], path[i], legs[i + 1])
        if _len(a, b) > 1e-6:
            piece = dict(s, path=[_r(a), _r(b)])
            out.append(_part(s, "straight", i + 1, _straight_mesh(piece, ladder), path=piece["path"], length_m=round(_len(a, b), 3)))
    for i in range(1, len(path) - 1):
        if legs[i] > 0:
            a, b = _toward(path[i], path[i - 1], legs[i]), _toward(path[i], path[i + 1], legs[i])
            out.append(_part(s, "elbow", i, _elbow_mesh_for(s, a, path[i], b, ring, ladder), path=[_r(a), _r(path[i]), _r(b)], angle_deg=_angle(path[i - 1], path[i], path[i + 1])))
    return out


def _on_stretch(p, a, b) -> bool:
    """Is the point on the stretch a-b, away from its ends?"""
    d = _sub(b, a)
    length = math.sqrt(_dot(d, d))
    if length < 1e-9:
        return False
    t = _dot(_sub(p, a), d) / length
    foot = _add(a, d, t / length)
    return TOUCH < t < length - TOUCH and _len(p, foot) <= TOUCH


def _ends(s: Dict[str, Any]) -> List[V3]:
    return [tuple(s["path"][0]), tuple(s["path"][-1])]


def _stretches(s: Dict[str, Any]) -> List[Tuple[V3, V3]]:
    path = [tuple(p) for p in s["path"]]
    return list(zip(path, path[1:]))


def _tees(runs: List[Dict[str, Any]], rings, leg_of, ladder: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Where a run ends on the side of another of its discipline: a tee of the main run, as long as the branch is wide plus a leg each way."""
    out = []
    for branch in runs:
        for main in runs:
            if main is branch or main["discipline"] != branch["discipline"]:
                continue
            for end in _ends(branch):
                for a, b in _stretches(main):
                    if _on_stretch(end, a, b):
                        half = branch["width_m"] / 2 + leg_of(main)
                        p, q = _toward(end, a, min(half, _len(end, a))), _toward(end, b, min(half, _len(end, b)))
                        piece = dict(main, path=[_r(p), _r(q)])
                        out.append(_part(main, "tee", len(out) + 1, _straight_mesh(piece, ladder), path=piece["path"], branch=branch["id"], branch_size=_size(branch), at=_r(end)))
    return out


def _reducer_for(big: Dict[str, Any], small: Dict[str, Any], p, tip, rings, ladder: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The mesh of a reducer: a tapering tray of the kind of the layer, else the skin between the two sections."""
    if not (ladder and big.get("layer") in ladder["layers"] and big["section"] == small["section"] == "rect"):
        return _reducer_mesh(p, tip, rings[big["id"]], rings[small["id"]])
    from epc_plan import tray_solid
    return tray_solid.reducer_mesh(p, tip, (big["width_m"], small["width_m"]), big["height_m"], ladder["sizes"], ladder.get("kinds", {}).get(big["layer"], "escalera"))


def _cross_at(a, b, c, d) -> Optional[V3]:
    """Where the stretches a-b and c-d cross in plan, away from their ends and at the same height, else None."""
    r, q = _sub(b, a), _sub(d, c)
    det = r[0] * q[1] - r[1] * q[0]
    if abs(det) < 1e-9:
        return None
    w = _sub(c, a)
    t, u = (w[0] * q[1] - w[1] * q[0]) / det, (w[0] * r[1] - w[1] * r[0]) / det
    lo_t, lo_u = TOUCH / max(_len(a, b), 1e-9), TOUCH / max(_len(c, d), 1e-9)
    if not (lo_t < t < 1 - lo_t and lo_u < u < 1 - lo_u):
        return None
    mine, other = _add(a, r, t), _add(c, q, u)
    return mine if abs(mine[2] - other[2]) <= TOUCH else None


def _arm(point: V3, a, b, half: float) -> List[List[float]]:
    """The piece of the stretch a-b that centres on `point`, `half` each way."""
    return [_r(_toward(point, a, min(half, _len(point, a)))), _r(_toward(point, b, min(half, _len(point, b))))]


def _same_tray(first: Dict[str, Any], second: Dict[str, Any]) -> bool:
    return first["discipline"] == second["discipline"] and first.get("layer") == second.get("layer") and first["section"] == second["section"] == "rect"


def _cross_part(first, second, stretch_a, stretch_b, at: V3, leg_of, ladder, n: int) -> Dict[str, Any]:
    """The cross of two runs at `at`: both arms, each as long as the other tray is wide plus a leg each way."""
    pieces = [dict(first, path=_arm(at, *stretch_a, second["width_m"] / 2 + leg_of(first))), dict(second, path=_arm(at, *stretch_b, first["width_m"] / 2 + leg_of(second)))]
    meshes = [_straight_mesh(piece, ladder) for piece in pieces]
    shift = len(meshes[0]["vertices"])
    mesh = {"vertices": meshes[0]["vertices"] + meshes[1]["vertices"], "faces": meshes[0]["faces"] + [[v + shift for v in f] for f in meshes[1]["faces"]]}
    return _part(first, "cross", n, mesh, path=pieces[0]["path"], branch=second["id"], branch_size=_size(second), at=_r(at))


def _crosses(runs: List[Dict[str, Any]], leg_of, ladder: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Where two tray runs of one layer cross in the middle at the same height: a cross."""
    out = []
    for i, first in enumerate(runs):
        for second in (r for r in runs[i + 1:] if _same_tray(first, r)):
            for sa in _stretches(first):
                for sb in _stretches(second):
                    at = _cross_at(*sa, *sb)
                    if at is not None:
                        out.append(_cross_part(first, second, sa, sb, at, leg_of, ladder, len(out) + 1))
    return out


def _reducers(runs: List[Dict[str, Any]], rings, leg_of, ladder: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Where two runs of one discipline and different size meet end to end: a reducer, drawn on the end of the smaller one."""
    out = []
    for i, big in enumerate(runs):
        for small in runs[i + 1:]:
            if big["discipline"] != small["discipline"] or _size(big) == _size(small):
                continue
            if big["width_m"] < small["width_m"]:
                big, small = small, big
            for p in _ends(big):
                far = next((q for q, e in zip(reversed(_ends(small)), _ends(small)) if _len(p, e) <= TOUCH), None)
                if far is not None:
                    tip = _toward(p, far, min(leg_of(big), _len(p, far)))
                    out.append(_part(big, "reducer", len(out) + 1, _reducer_for(big, small, p, tip, rings, ladder), path=[_r(p), _r(tip)], to=small["id"], to_size=_size(small)))
    return out


def _setting(spec: Optional[Dict[str, Any]], key: str) -> float:
    """A drawing size of the parts: what `spec` says, else the one of `params.json`."""
    value = (spec or {}).get(key, core.PARAMS["detail"][key])
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise core.PlanError("err_detail_number", key=key)
    return float(value)


def tray_kinds() -> tuple:
    from epc_plan import tray_draw
    return tray_draw.KINDS


def _ladder_sizes(cover: bool) -> Dict[str, float]:
    """The sizes of rail, rungs, floor and wires (`params.json`, `detail.ladder`, in metres), and the lid when there is one."""
    q = core.PARAMS["detail"]["ladder"]
    keys = ("rail", "rung", "rung_thick", "rung_pitch", "foot", "curl", "slot_pitch", "slot", "slot_height", "floor_margin", "wire", "wire_pitch", "joint", "bolt")
    sizes = {k: q[k + "_m"] for k in keys}
    if cover:
        sizes["cover"] = q["cover_m"]                                    # the lid, a flat sheet over the rails
    return sizes


def _kinds_ok(kinds: Any, layers: List[str]) -> bool:
    return isinstance(kinds, dict) and all(k in layers and v in tray_kinds() for k, v in kinds.items())


def _ladder(spec: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The trays asked for in `spec["ladder_trays"]` ({"layers": [...], "kinds": {layer: kind}, "cover": bool}): the layers, the kind of each and the sizes they are drawn with."""
    given = (spec or {}).get("ladder_trays")
    if not given:
        return None
    layers = given.get("layers") if isinstance(given, dict) else None
    if not isinstance(layers, list) or not layers or not all(isinstance(x, str) for x in layers) or not _kinds_ok(given.get("kinds", {}), layers):
        raise core.PlanError("err_detail_number", key="ladder_trays")
    return {"layers": layers, "sizes": _ladder_sizes(bool(given.get("cover"))), "kinds": given.get("kinds", {}), "elbow_radius": core.PARAMS["detail"]["ladder"]["elbow_radius_m"], "links": core.PARAMS["detail"]["ladder"]["vertical_links"]}


def parts(solids: List[Dict[str, Any]], spec: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """The runs of the solids as the parts they are built from: straights, elbows, tees and reducers, each with its mesh. Boxes (equipment, boards, chambers) are not parts: they stay as
    they are in the scene. `spec` may give `elbow_leg_factor` (the leg of an elbow in widths of its run) and `ladder_trays` ({"layers": [...]}: the straights on those layers are drawn as ladder trays, with rails and rungs)."""
    factor = _setting(spec, "elbow_leg_factor")
    sides = core.PARAMS["solid"]["sides"]
    runs = [s for s in solids if s.get("shape") == "run"]
    rings = {s["id"]: S._ring(s, sides) for s in runs}
    leg_of = lambda s: factor * s["width_m"]                                  # noqa: E731
    ladder = _ladder(spec)
    out = [p for s in runs for p in _run_parts(s, rings[s["id"]], leg_of(s), ladder)]
    return out + _tees(runs, rings, leg_of, ladder) + _reducers(runs, rings, leg_of, ladder) + _crosses(runs, leg_of, ladder)


# ---------------------------------------------------------------- supports
def _spec_errors(spec: Any) -> List[str]:
    if not isinstance(spec, dict):
        return ["supports: an object with spacing_m and slab_underside_m"]
    out = []
    spacing = spec.get("spacing_m")
    if not isinstance(spacing, (int, float)) or isinstance(spacing, bool) or spacing <= 0:
        out.append("supports/spacing_m: required, the distance between supports in metres (no default: it comes from the standard and the manufacturer)")
    under = spec.get("slab_underside_m")
    if not isinstance(under, dict) or not under or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in under.values()):
        out.append("supports/slab_underside_m: required, {level: height of the underside of the slab above, in metres from the level of the project}")
    return out


def _places(a, b, spacing: float) -> List[V3]:
    """Where the supports of a stretch go: as many as keep them no further apart than the spacing, evenly, half a step in from each end."""
    length = _len(a, b)
    n = max(1, math.ceil(length / spacing - 1e-9))
    return [_add(a, _sub(b, a), (k + 0.5) / n) for k in range(n)]


def _rod(at, top: float, d: float) -> Dict[str, Any]:
    return {"section": "round", "width_m": d, "height_m": d, "path": [_r(at), _r((at[0], at[1], top))]}


def _hanger(s: Dict[str, Any], at: V3, across: V3, top: float, sizes: Dict[str, float]) -> Tuple[str, List[Dict[str, Any]], float]:
    """The pieces of one support as bare runs (section, size, path), its type and the rod it needs."""
    d, ch, over = sizes["rod_m"], sizes["channel_m"], sizes["overhang_m"]
    if s["section"] == "round":
        start = (at[0], at[1], at[2] + s["width_m"] / 2)
        clamp = {"section": "rect", "width_m": s["width_m"] + 2 * d, "height_m": d, "path": [_r(_add(at, across, -d)), _r(_add(at, across, d))]}
        return "rod", [_rod(start, top, d), clamp], round(top - start[2], 3)
    under = at[2] - s["height_m"] / 2 - ch / 2
    half = s["width_m"] / 2 + over
    left, right = _add((at[0], at[1], under), across, -half), _add((at[0], at[1], under), across, half)
    channel = {"section": "rect", "width_m": ch, "height_m": ch, "path": [_r(left), _r(right)]}
    inner = s["width_m"] / 2 + over / 2
    rods = [_rod(_add((at[0], at[1], under), across, k * inner), top, d) for k in (-1.0, 1.0)]
    return "trapeze", [channel] + rods, round(2 * (top - under), 3)


def _hangable(s: Dict[str, Any], a, b, top: Optional[float]) -> bool:
    """A horizontal stretch of a run, under the slab it hangs from."""
    return s.get("shape") == "run" and top is not None and abs(a[2] - b[2]) < 1e-6 and _len(a, b) > 1e-6 and a[2] + s["height_m"] / 2 < top


def supports(solids: List[Dict[str, Any]], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The supports of the horizontal runs that hang under a slab, each as a solid with its mesh. `spec`: `spacing_m` and `slab_underside_m` ({level: metres}) are required; `rod_m`,
    `channel_m` and `overhang_m` override the sizes the supports are drawn with. A run of a level that has no slab given, or that is not under it, gets none."""
    bad = _spec_errors(spec)
    if bad:
        raise core.PlanError("err_supports_spec_invalid", details="; ".join(bad))
    sizes = {k: _setting(spec, k) for k in ("rod_m", "channel_m", "overhang_m")}
    out = []
    for s in solids:
        top = spec["slab_underside_m"].get(s.get("level"))
        for a, b in (_stretches(s) if s.get("shape") == "run" else []):
            if not _hangable(s, a, b, top):
                continue
            across = S._frame(a, b)[0]
            for at in _places(a, b, spec["spacing_m"]):
                kind, pieces, rod = _hanger(s, at, across, top, sizes)
                mesh = _joined([S.mesh(p) for p in pieces])
                out.append({"id": f"{s['id']}:support{len(out) + 1}", "tag": f"SP-{len(out) + 1:03d}", "kind": "support", "discipline": s["discipline"], "level": s["level"], "sheet": s.get("sheet", ""),
                            "layer": SUPPORT_LAYER, "shape": "box", "part": "support", "support": kind, "run": s["id"], "size": _size(s), "at": _r(at), "rod_m": rod, "mesh": mesh})
    return out


def _joined(meshes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Several meshes as one."""
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    for m in meshes:
        base = len(vertices)
        vertices += m["vertices"]
        faces += [[i + base for i in f] for f in m["faces"]]
    return {"vertices": vertices, "faces": faces}


# ---------------------------------------------------------------- take-off
def _count(rows: Dict[tuple, Dict[str, Any]], key: tuple, start: Dict[str, Any], **add: float) -> None:
    row = rows.setdefault(key, dict(start, count=0, **{k: 0.0 for k in add}))
    row["count"] += 1
    for k, v in add.items():
        row[k] = round(row[k] + v, 3)


def takeoff(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """What the parts add up to: `straights` (pieces and total length by discipline, layer and size), `fittings` (by type, size, angle and what they join) and `supports` (by type and size
    of run, with the rod they need). Sorted, so the same model gives the same list."""
    straights: Dict[tuple, Dict[str, Any]] = {}
    fittings: Dict[tuple, Dict[str, Any]] = {}
    hangers: Dict[tuple, Dict[str, Any]] = {}
    for p in items:
        base = {"discipline": p.get("discipline", ""), "layer": p.get("layer", ""), "size": p.get("size", "")}
        if p.get("part") == "straight":
            _count(straights, tuple(base.values()), base, length_m=p["length_m"])
        elif p.get("part") in ("elbow", "tee", "cross", "reducer"):
            extra = {"type": p["part"], "angle_deg": p.get("angle_deg"), "to_size": p.get("branch_size") or p.get("to_size")}
            _count(fittings, tuple(base.values()) + tuple(extra.values()), dict(base, **extra))
        elif p.get("part") == "support":
            extra = {"type": p["support"]}
            _count(hangers, tuple(base.values()) + (p["support"],), dict(base, **extra), rod_m=p["rod_m"])
    order = lambda rows: [rows[k] for k in sorted(rows, key=lambda k: tuple(str(v) for v in k))]      # noqa: E731
    return {"straights": order(straights), "fittings": order(fittings), "supports": order(hangers)}


def scene(solids: List[Dict[str, Any]], spec: Optional[Dict[str, Any]] = None, hangers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The fabrication scene of some solids: the parts of the runs, the equipment as it is and, when `hangers` (the spec of `supports`) is given, the supports."""
    boxes = [s for s in solids if s.get("shape") != "run"]
    items = parts(solids, spec) + (supports(solids, hangers) if hangers is not None else [])
    return S.scene(boxes + items)
