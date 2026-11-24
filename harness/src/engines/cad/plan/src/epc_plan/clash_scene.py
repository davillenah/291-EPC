"""Clashes found in a 3D scene: the raceways against the building and against each other, noted so a solution can be sought later. Pure: a scene in, a list of clashes out.

Each solid of the scene is taken as the boxes it is made of (a solid whose mesh is made of boxes of eight corners, as the walls, slabs and the trays of `tray_solid` are; any other solid is one box).
Two boxes clash when
  hard       they share volume (the building and a tray that goes through it, or two trays that touch);
  clearance  two trays do not touch but are closer than `clearance_m` (0 asks for nothing).
Boxes are axis-aligned, so a tray on a slope is taken a little bigger than it is: a clash it reports is to be confirmed by looking at it, one it does not report is not there.
Rooms (plates that mark a floor) are not bodies and are left out; two solids of the building never clash with each other. The same scene gives the same list, worst first.
"""
import hashlib
from typing import Any, Dict, List, Sequence, Tuple

Box = Tuple[Tuple[float, float, float], Tuple[float, float, float]]
BUILDING = ("wall", "slab", "glass")
EPS = 1e-6


def _box_of(points: Sequence[Sequence[float]]) -> Box:
    return (tuple(min(p[i] for p in points) for i in range(3)), tuple(max(p[i] for p in points) for i in range(3)))  # type: ignore[return-value]


def boxes(solid: Dict[str, Any]) -> List[Box]:
    """The boxes a solid is made of: one per eight corners when its mesh is built that way, else the box of the whole mesh."""
    v = solid["mesh"]["vertices"]
    if v and len(v) % 8 == 0 and len(solid["mesh"]["faces"]) == len(v) // 8 * 6:
        return [_box_of(v[i:i + 8]) for i in range(0, len(v), 8)]
    return [_box_of(v)] if v else []


def _gap(a: Box, b: Box) -> Tuple[float, Tuple[float, float, float]]:
    """(gap, point): the gap between two boxes (negative: how deep they go into each other, along the axis of least depth) and a point at the middle of the overlap or of the space between."""
    per_axis = [max(a[0][i], b[0][i]) - min(a[1][i], b[1][i]) for i in range(3)]
    gap = max(per_axis) if max(per_axis) > 0 else max(per_axis)
    point = tuple((max(a[0][i], b[0][i]) + min(a[1][i], b[1][i])) / 2 for i in range(3))
    return gap, point  # type: ignore[return-value]


def _distance(a: Box, b: Box) -> float:
    """The distance between two boxes (0 when they touch or share space)."""
    d = [max(0.0, max(a[0][i], b[0][i]) - min(a[1][i], b[1][i])) for i in range(3)]
    return sum(x * x for x in d) ** 0.5


def _pair(a: Dict[str, Any], b: Dict[str, Any], clearance_m: float):
    """The worst relation found between the boxes of two solids: (type, gap, point, the two boxes) or None."""
    worst = None
    for x in boxes(a):
        for y in boxes(b):
            gap, point = _gap(x, y)
            if gap < -EPS:
                cand = ("hard", gap, point, (x, y))
            elif clearance_m > 0 and a["kind"] == b["kind"] == "tray" and _distance(x, y) < clearance_m - EPS:
                cand = ("clearance", _distance(x, y), point, (x, y))
            else:
                continue
            if worst is None or (cand[0] == "hard" and (worst[0] != "hard" or cand[1] < worst[1])) or (cand[0] == worst[0] == "clearance" and cand[1] < worst[1]):
                worst = cand
    return worst


def _overlap(a: Box, b: Box) -> List[float]:
    """The size of the space two boxes share, along x, y and z."""
    return [round(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]), 3) for i in range(3)]


def _relevant(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    kinds = {a["kind"], b["kind"]}
    if "room" in kinds or (a["kind"] in BUILDING and b["kind"] in BUILDING):
        return False
    return True


def detect(scene: Dict[str, Any], clearance_m: float = 0.0) -> List[Dict[str, Any]]:
    """Every clash between the solids of the scene (see the module text), worst first."""
    solids = [s for s in scene["solids"] if s["kind"] != "room"]
    found = []
    for i, a in enumerate(solids):
        for b in solids[i + 1:]:
            if not _relevant(a, b):
                continue
            hit = _pair(a, b, clearance_m)
            if hit is None:
                continue
            kind, gap, point, hit_boxes = hit
            found.append({"id": hashlib.sha1("|".join(sorted([str(a["id"]), str(b["id"])])).encode()).hexdigest()[:10], "type": kind, "severity": "error" if kind == "hard" else "warning",
                          "gap_m": round(gap, 3), "overlap_m": _overlap(hit_boxes[0], hit_boxes[1]) if kind == "hard" else None, "point_m": [round(c, 3) for c in point], "level": a.get("level") or b.get("level") or "",
                          "a": {k: a.get(k) for k in ("id", "tag", "kind", "layer")}, "b": {k: b.get(k) for k in ("id", "tag", "kind", "layer")},
                          "text": {"en": f"{a['tag']} ({a['kind']}) and {b['tag']} ({b['kind']}): {kind}, {abs(round(gap, 3))} m", "es": f"{a['tag']} ({a['kind']}) y {b['tag']} ({b['kind']}): {'choque' if kind == 'hard' else 'separación insuficiente'}, {abs(round(gap, 3))} m"}})
    found.sort(key=lambda c: (c["type"] != "hard", c["gap_m"], c["id"]))
    return found
