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


def _relation(x: Box, y: Box, clearance_m: float, trays: bool):
    """How two boxes relate: ("hard", depth, point, boxes), ("clearance", distance, point, boxes) or None."""
    gap, point = _gap(x, y)
    if gap < -EPS:
        return ("hard", gap, point, (x, y))
    if clearance_m > 0 and trays and _distance(x, y) < clearance_m - EPS:
        return ("clearance", _distance(x, y), point, (x, y))
    return None


def _pair(a: Dict[str, Any], b: Dict[str, Any], clearance_m: float, boxes_a: Sequence[Box] = (), boxes_b: Sequence[Box] = ()):
    """The worst relation found between the boxes of two solids: (type, gap, point, the two boxes) or None. The boxes of each solid may be given when they are already known."""
    trays = a["kind"] == b["kind"] == "tray"
    found = [r for x in (boxes_a or boxes(a)) for y in (boxes_b or boxes(b)) for r in [_relation(x, y, clearance_m, trays)] if r]
    return min(found, key=lambda r: (r[0] != "hard", r[1])) if found else None


def _overlap(a: Box, b: Box) -> List[float]:
    """The size of the space two boxes share, along x, y and z."""
    return [round(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]), 3) for i in range(3)]


def _relevant(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    kinds = {a["kind"], b["kind"]}
    if "room" in kinds or (a["kind"] in BUILDING and b["kind"] in BUILDING):
        return False
    return True


def _entry(a: Dict[str, Any], b: Dict[str, Any], hit) -> Dict[str, Any]:
    kind, gap, point, pair = hit
    ref = lambda s: {k: s.get(k) for k in ("id", "tag", "kind", "layer")}
    what = {"en": "clash" if kind == "hard" else "clearance too small", "es": "choque" if kind == "hard" else "separación insuficiente"}
    return {"id": hashlib.sha1("|".join(sorted([str(a["id"]), str(b["id"])])).encode()).hexdigest()[:10], "type": kind, "severity": "error" if kind == "hard" else "warning",
            "gap_m": round(gap, 3), "overlap_m": _overlap(*pair) if kind == "hard" else None, "point_m": [round(c, 3) for c in point], "level": a.get("level") or b.get("level") or "",
            "a": ref(a), "b": ref(b),
            "text": {lang: f"{a['tag']} ({a['kind']}) / {b['tag']} ({b['kind']}): {what[lang]}, {abs(round(gap, 3))} m" for lang in ("en", "es")}}


def _extent(parts: Sequence[Box]) -> Box:
    return (tuple(min(b[0][k] for b in parts) for k in range(3)), tuple(max(b[1][k] for b in parts) for k in range(3)))  # type: ignore[return-value]


def _near(a: Box, b: Box, margin: float) -> bool:
    """Whether two extents are no further apart than `margin` along any axis (a pair that is not cannot clash and is not looked at)."""
    return all(a[0][k] - margin <= b[1][k] and b[0][k] - margin <= a[1][k] for k in (1, 2))


def _candidates(solids: List[Dict[str, Any]], parts: List[Sequence[Box]], clearance_m: float) -> List[Tuple[int, int]]:
    """The pairs of solids whose extents come near enough to clash, found by sweeping along x (sorted by their lowest x) instead of comparing every pair."""
    margin = max(clearance_m, 0.0) + 2 * EPS
    order = sorted((i for i in range(len(solids)) if parts[i]), key=lambda i: _extent(parts[i])[0][0])
    extents = {i: _extent(parts[i]) for i in order}
    pairs = []
    for n, i in enumerate(order):
        for j in order[n + 1:]:
            if extents[j][0][0] > extents[i][1][0] + margin:
                break                                                  # every later solid starts further along x than this one reaches
            if _near(extents[i], extents[j], margin) and _relevant(solids[i], solids[j]):
                pairs.append((min(i, j), max(i, j)))                  # the order of the scene, as when every pair was compared
    return pairs


def detect(scene: Dict[str, Any], clearance_m: float = 0.0) -> List[Dict[str, Any]]:
    """Every clash between the solids of the scene (see the module text), worst first."""
    solids = [s for s in scene["solids"] if s["kind"] != "room"]
    parts = [boxes(s) for s in solids]
    hits = [(solids[i], solids[j], _pair(solids[i], solids[j], clearance_m, parts[i], parts[j])) for i, j in _candidates(solids, parts, clearance_m)]
    found = [_entry(a, b, hit) for a, b, hit in hits if hit is not None]
    return sorted(found, key=lambda c: (c["type"] != "hard", c["gap_m"], c["id"]))
