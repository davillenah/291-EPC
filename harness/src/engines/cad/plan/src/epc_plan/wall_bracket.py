"""Wall brackets: the supports of a horizontal tray that sit on the wall beside it.

A bracket is a backplate against the face of the wall and an arm that runs from the wall under the tray, across all of its width. Where it goes is found, not given: from each support place of a
stretch (`spacing_m`, as for the hangers) the nearest wall on either side that is at the height of the tray and no further than `reach_m` from its edge. The reach is a design value of the engineer
(no default). The walls come from the caller (the engine reads nothing); a place with no wall within reach gets no bracket, and it is the caller who reports it.

    brackets(runs, walls, spec) -> [support solid]      runs: the solids of the runs; walls: the solids of the walls (with their mesh, the frame of the runs); spec: {spacing_m, reach_m}
"""
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from epc_plan import clash_scene, core, detail
from epc_plan import tray_solid as T

Box = Tuple[Tuple[float, float, float], Tuple[float, float, float]]
EPS = 1e-9


def _hit(origin: Tuple[float, float], d: Tuple[float, float], z: float, wall: Box) -> Optional[float]:
    """The distance along `d` from `origin` to the wall in plan (None if it is not hit, or not at the height z)."""
    lo, hi = wall
    if not lo[2] - EPS <= z <= hi[2] + EPS:
        return None
    t0, t1 = -math.inf, math.inf
    for k in (0, 1):
        if abs(d[k]) < EPS:
            if not lo[k] <= origin[k] <= hi[k]:
                return None
            continue
        a, b = (lo[k] - origin[k]) / d[k], (hi[k] - origin[k]) / d[k]
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    return t0 if t0 <= t1 and t0 > EPS else None


def _nearest(at: Sequence[float], d: Tuple[float, float], walls: Sequence[Box]) -> Optional[float]:
    found = [t for t in (_hit((at[0], at[1]), d, at[2], w) for w in walls) if t is not None]
    return min(found) if found else None


def _mesh(at: Sequence[float], d: Tuple[float, float], reach: float, tray: Dict[str, Any], sizes: Dict[str, float]) -> Dict[str, list]:
    """The backplate and the arm of one bracket whose wall is `reach` away from the axis of the tray."""
    dx, dy = d
    along, across, up = (dx, dy, 0.0), (-dy, dx, 0.0), (0.0, 0.0, 1.0)
    arm = sizes["arm_m"]
    length = reach + tray["width_m"] / 2
    z = at[2] - tray["height_m"] / 2 - arm / 2
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    centre = lambda t, h: (at[0] + dx * t, at[1] + dy * t, h)             # noqa: E731
    T._box(vertices, faces, centre(reach - length / 2, z), (along, across, up), (length, arm, arm))
    T._box(vertices, faces, centre(reach - sizes["plate_thick_m"] / 2, z + arm / 2 - sizes["plate_height_m"] / 2), (along, across, up), (sizes["plate_thick_m"], sizes["plate_m"], sizes["plate_height_m"]))
    return {"vertices": vertices, "faces": faces}


def _sides(a: Sequence[float], b: Sequence[float]) -> List[Tuple[float, float]]:
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    u = ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
    return [(-u[1], u[0]), (u[1], -u[0])]


def _wanted(spec: Any) -> List[str]:
    if not isinstance(spec, dict):
        return ["supports: an object with spacing_m and reach_m"]
    return [f"supports/{k}: required, a positive number of metres (no default: it comes from the standard and the manufacturer)" for k in ("spacing_m", "reach_m")
            if not isinstance(spec.get(k), (int, float)) or isinstance(spec.get(k), bool) or spec[k] <= 0]


def _on_wall(s: Dict[str, Any], at, sides, walls: Sequence[Box], reach: float, sizes: Dict[str, float], n: int) -> Optional[Dict[str, Any]]:
    """The bracket of the tray `s` at `at`, on the nearer of the two sides that has a wall within reach of the edge of the tray."""
    seen = [(t, d) for d in sides for t in [_nearest(at, d, walls)] if t is not None and t - s["width_m"] / 2 <= reach]
    if not seen:
        return None
    t, d = min(seen)
    return {"id": f"{s['id']}:support{n}", "tag": f"SP-{n:03d}", "kind": "support", "discipline": s["discipline"], "level": s["level"], "sheet": s.get("sheet", ""), "layer": detail.SUPPORT_LAYER,
            "shape": "box", "part": "support", "support": "wall_bracket", "run": s["id"], "size": detail._size(s), "at": detail._r(at), "rod_m": 0.0, "mesh": _mesh(at, d, t, s, sizes)}


def _level_stretches(s: Dict[str, Any]) -> List[Any]:
    """The horizontal stretches of a rectangular tray run."""
    if s.get("shape") != "run" or s.get("section") != "rect":
        return []
    return [(a, b) for a, b in detail._stretches(s) if abs(a[2] - b[2]) <= 1e-6 and detail._len(a, b) >= 1e-6]


def brackets(runs: List[Dict[str, Any]], walls: Sequence[Dict[str, Any]], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The wall brackets of the horizontal tray runs (rectangular sections) that have a wall within `spec["reach_m"]` of an edge; one per support place and side-nearest wall."""
    bad = _wanted(spec)
    if bad:
        raise core.PlanError("err_supports_spec_invalid", details="; ".join(bad))
    sizes = core.PARAMS["detail"]["bracket"]
    boxes = [b for w in walls for b in clash_scene.boxes(w)]
    out: List[Dict[str, Any]] = []
    for s in runs:
        for a, b in _level_stretches(s):
            for at in detail._places(a, b, spec["spacing_m"]):
                made = _on_wall(s, at, _sides(a, b), boxes, spec["reach_m"], sizes, len(out) + 1)
                if made:
                    out.append(made)
    return out
