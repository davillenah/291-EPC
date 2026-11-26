"""Horizontal single-axis tracker: the rotation angle of every instant and the tilt and azimuth of the plane it gives (closed-form geometry, no norm value).

The axis is horizontal with azimuth `axis_azimuth_deg` (clockwise from north). The ideal angle turns the plane to the sun in the plane normal to the axis: theta = atan2(s.c, s.z), c being the horizontal
direction across the axis (azimuth axis + 90) and s the unit vector to the sun; theta is positive towards c. It is clipped to `max_angle_deg`. With backtracking and a ground coverage ratio `gcr` (module
width / row pitch) the angle is eased so that a row does not shade the next one: theta_b = theta - sign(theta) * acos(min(1, cos(theta) / gcr)) (Lorenzo et al. 2011).
"""
import math
from typing import Any, Dict, Tuple

from epc_pv.messages import bi
from epc_pv.model import PvError


def check(block: Any, where: str) -> Dict[str, Any]:
    """The checked `tracker` block: axis_azimuth_deg (0 to 360), max_angle_deg (1 to 90), gcr (0 to 1, only with backtracking), backtracking (default true)."""
    if not isinstance(block, dict):
        raise PvError("err_type", name=where, kind=bi("an object", "un objeto"))
    missing = [k for k in ("axis_azimuth_deg", "max_angle_deg") if k not in block]
    if missing:
        raise PvError("err_missing", where=where, names=", ".join(missing))
    out = {"axis_azimuth_deg": _num(block, "axis_azimuth_deg", where, 0.0, 360.0), "max_angle_deg": _num(block, "max_angle_deg", where, 1.0, 90.0), "backtracking": bool(block.get("backtracking", True)), "gcr": None}
    if out["backtracking"]:
        if "gcr" not in block:
            raise PvError("err_missing", where=where, names="gcr")
        out["gcr"] = _num(block, "gcr", where, 0.01, 1.0)
    return out


def _num(block: Dict[str, Any], key: str, where: str, low: float, high: float) -> float:
    try:
        value = float(block[key])
    except (TypeError, ValueError) as e:
        raise PvError("err_type", name=f"{where}.{key}", kind=bi("a number", "un número")) from e
    if not low <= value <= high:
        raise PvError("err_range", name=f"{where}.{key}", rule=bi(f"from {low:g} to {high:g}", f"de {low:g} a {high:g}"), value=value)
    return value


def rotation_deg(sun_elevation_deg: float, sun_azimuth_deg: float, tracker: Dict[str, Any]) -> float:
    """The rotation angle (degrees, positive towards the side of azimuth axis + 90) at one instant; 0 with the sun below the horizon."""
    if sun_elevation_deg <= 0.0:
        return 0.0
    el, az, axis = math.radians(sun_elevation_deg), math.radians(sun_azimuth_deg), math.radians(tracker["axis_azimuth_deg"])
    cross = math.cos(el) * (math.sin(az) * math.cos(axis) - math.cos(az) * math.sin(axis))      # sun . c, with c = (cos axis, -sin axis) in (east, north)
    ideal = math.atan2(cross, math.sin(el))
    theta = ideal
    if tracker["backtracking"]:
        theta = ideal - math.copysign(math.acos(min(1.0, math.cos(ideal) / tracker["gcr"])), ideal)
    limit = math.radians(tracker["max_angle_deg"])
    theta = max(-limit, min(limit, theta))
    return math.degrees(theta)


def surface(rotation_deg_: float, axis_azimuth_deg: float) -> Tuple[float, float]:
    """(tilt, azimuth) in degrees of the plane for a rotation angle: tilt is the size of the angle, azimuth looks across the axis towards the side the angle points to."""
    side = 90.0 if rotation_deg_ >= 0.0 else -90.0
    return abs(rotation_deg_), (axis_azimuth_deg + side) % 360.0
