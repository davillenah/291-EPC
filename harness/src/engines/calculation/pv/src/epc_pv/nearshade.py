"""Shade of near obstacles (a chimney, a tank, a tree trunk, a wall) on the modules, by casting the sun ray from points of the array to boxes.

The array is a tilted rectangle of `width_m` by `slope_m` whose lowest edge is `base_height_m` above the ground and whose centre is the origin of the local frame (x east, y north, z up, metres).
Each obstacle is a box on the ground: its centre `x_m`, `y_m`, size `width_m` (east-west), `depth_m` (north-south) and `height_m`. The array is sampled in a grid of points; a point is shaded when the ray towards
the sun meets a box. The result is the share of the points in the sun (0 to 1) and applies to the direct beam only. Pure geometry: no norm value.
"""
import math
from typing import Any, Dict, List, Sequence, Tuple

from epc_pv.model import PvError

GRID = 4                   # sample points across and along the slope: 16 per array
Vec = Tuple[float, float, float]


def check(block: Any, where: str) -> Dict[str, Any]:
    """The checked `near_obstacles` block: {"array": {width_m, slope_m, base_height_m}, "boxes": [{x_m, y_m, width_m, depth_m, height_m}, ...]}."""
    if not isinstance(block, dict) or not isinstance(block.get("array"), dict) or not isinstance(block.get("boxes"), list):
        raise PvError("err_missing", where=where, names="array, boxes")
    array = {k: _num(block["array"], k, f"{where}.array", k != "base_height_m") for k in ("width_m", "slope_m", "base_height_m")}
    boxes = [{k: _num(b, k, f"{where}.boxes[{i}]", k in ("width_m", "depth_m", "height_m")) for k in ("x_m", "y_m", "width_m", "depth_m", "height_m")} for i, b in enumerate(block["boxes"])]
    return {"array": array, "boxes": boxes}


def _num(obj: Any, key: str, where: str, positive: bool) -> float:
    try:
        value = float(obj[key])
    except (KeyError, TypeError, ValueError) as e:
        raise PvError("err_missing", where=where, names=key) from e
    if (positive and value <= 0.0) or (not positive and value < 0.0 and key == "base_height_m"):
        raise PvError("err_range", name=f"{where}.{key}", rule={"en": "greater than 0" if positive else "0 or more", "es": "mayor que 0" if positive else "0 o más"}, value=value)
    return value


def sample_points(array: Dict[str, float], tilt_deg: float, azimuth_deg: float) -> List[Vec]:
    """The grid of points on the array plane (the cell centres), in the local frame. The plane faces `azimuth_deg` (clockwise from north) and rises towards the opposite side."""
    b, g = math.radians(tilt_deg), math.radians(azimuth_deg)
    front = (math.sin(g), math.cos(g))                       # horizontal unit vector the array faces
    side = (math.cos(g), -math.sin(g))                       # along the lower edge
    points = []
    for i in range(GRID):
        u = ((i + 0.5) / GRID - 0.5) * array["width_m"]
        for j in range(GRID):
            s = (j + 0.5) / GRID * array["slope_m"]            # up the slope from the lowest edge
            back = s * math.cos(b) - array["slope_m"] * math.cos(b) / 2.0
            points.append((u * side[0] - back * front[0], u * side[1] - back * front[1], array["base_height_m"] + s * math.sin(b)))
    return points


def _hits(point: Vec, sun: Vec, box: Dict[str, float]) -> bool:
    """True when the ray from `point` towards `sun` meets the box (slab test, in front of the point)."""
    lo = (box["x_m"] - box["width_m"] / 2.0, box["y_m"] - box["depth_m"] / 2.0, 0.0)
    hi = (box["x_m"] + box["width_m"] / 2.0, box["y_m"] + box["depth_m"] / 2.0, box["height_m"])
    near, far = 0.0, math.inf
    for axis in range(3):
        if abs(sun[axis]) < 1e-12:
            if not lo[axis] <= point[axis] <= hi[axis]:
                return False
            continue
        t1, t2 = (lo[axis] - point[axis]) / sun[axis], (hi[axis] - point[axis]) / sun[axis]
        near, far = max(near, min(t1, t2)), min(far, max(t1, t2))
    return near <= far and far > 0.0


def sunlit_fraction(points: Sequence[Vec], boxes: Sequence[Dict[str, float]], sun_elevation_deg: float, sun_azimuth_deg: float) -> float:
    """Share of the sample points in the sun at one instant (1 = none shaded)."""
    if sun_elevation_deg <= 0.0 or not boxes:
        return 1.0
    el, az = math.radians(sun_elevation_deg), math.radians(sun_azimuth_deg)
    sun = (math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el))
    lit = sum(1 for p in points if not any(_hits(p, sun, b) for b in boxes))
    return lit / len(points)
