"""Shading of the direct beam: the far horizon and the shade of one row on the next (pure geometry, no norm value).

Two causes, both on the direct component only (the diffuse and ground parts stay; the area of a row shaded counts as the share of its direct beam lost):

* far horizon: the sun below the horizon profile (hills, buildings), given as points `{azimuth_deg, elevation_deg}` clockwise from north, joined by straight lines and closed around the circle;
* row to row: a row of tilted tables in front of another with the same azimuth, from the slope length `slope_m`, the horizontal distance `pitch_m` between the front edges of two rows and the number of
  rows. The sun is taken in the plane normal to the rows: tan(a') = tan(a) / cos(psi), psi being the sun azimuth minus the azimuth of the surface. Behind the surface (cos psi <= 0) no row shades another.

`direct_factor(...)` is the share of the direct beam that is kept at one instant; `apply(poa, factor)` gives the plane-of-array values with that share.
"""
import math
from typing import Any, Dict, List, Optional, Sequence

from epc_pv import nearshade
from epc_pv.model import PvError


def horizon_points(points: Any, where: str) -> List[Dict[str, float]]:
    """The checked horizon profile, sorted by azimuth. Elevations from 0 to 90, azimuths from 0 to 360 (360 counts as 0), at least one point."""
    if not isinstance(points, (list, tuple)) or not points:
        raise PvError("err_type", name=where, kind={"en": "a non-empty list of {azimuth_deg, elevation_deg}", "es": "una lista no vacía de {azimuth_deg, elevation_deg}"})
    out = []
    for i, p in enumerate(points):
        try:
            az, el = float(p["azimuth_deg"]) % 360.0, float(p["elevation_deg"])
        except (KeyError, TypeError, ValueError) as e:
            raise PvError("err_missing", where=f"{where}[{i}]", names="azimuth_deg, elevation_deg") from e
        if not 0.0 <= el <= 90.0:
            raise PvError("err_range", name=f"{where}[{i}].elevation_deg", rule={"en": "from 0 to 90", "es": "de 0 a 90"}, value=el)
        out.append({"azimuth_deg": az, "elevation_deg": el})
    return sorted(out, key=lambda p: p["azimuth_deg"])


def horizon_elevation_deg(points: Sequence[Dict[str, float]], azimuth_deg: float) -> float:
    """Elevation of the horizon at an azimuth: straight line between the two nearest points, around the circle."""
    az = azimuth_deg % 360.0
    if len(points) == 1:
        return points[0]["elevation_deg"]
    before = max((p for p in points if p["azimuth_deg"] <= az), key=lambda p: p["azimuth_deg"], default=points[-1])
    after = min((p for p in points if p["azimuth_deg"] > az), key=lambda p: p["azimuth_deg"], default=points[0])
    span = (after["azimuth_deg"] - before["azimuth_deg"]) % 360.0 or 360.0
    t = ((az - before["azimuth_deg"]) % 360.0) / span
    return before["elevation_deg"] + t * (after["elevation_deg"] - before["elevation_deg"])


def row_shaded_fraction(slope_m: float, pitch_m: float, tilt_deg: float, surface_azimuth_deg: float, sun_elevation_deg: float, sun_azimuth_deg: float) -> float:
    """Share (0 to 1) of the slope of a row shaded by the row in front of it at one instant."""
    if sun_elevation_deg <= 0.0 or tilt_deg <= 0.0:
        return 0.0
    cos_psi = math.cos(math.radians(sun_azimuth_deg - surface_azimuth_deg))
    if cos_psi <= 1e-9:
        return 0.0
    tan_a = math.tan(math.radians(sun_elevation_deg)) / cos_psi
    b = math.radians(tilt_deg)
    tan_b = math.tan(b)
    reach = (slope_m * math.sin(b) + slope_m * math.cos(b) * tan_a + pitch_m * tan_b) / (tan_b + tan_a)     # horizontal position where the ray meets the plane of the row behind
    return min(1.0, max(0.0, (reach - pitch_m) / math.cos(b) / slope_m))


def direct_factor(sun_elevation_deg: float, sun_azimuth_deg: float, tilt_deg: float, surface_azimuth_deg: float,
                  horizon: Optional[Sequence[Dict[str, float]]] = None, rows: Optional[Dict[str, float]] = None, near: Optional[Dict[str, Any]] = None) -> float:
    """Share of the direct beam kept (1 = no shade): 0 below the horizon profile, else one minus the shaded share of the rows (the front row is never shaded: (n - 1) / n of the rows),
    times the share of the array in the sun with the near obstacles (`near`: {"points", "boxes"} from `nearshade`)."""
    if horizon and sun_elevation_deg < horizon_elevation_deg(horizon, sun_azimuth_deg):
        return 0.0
    kept = 1.0
    if rows and rows["n_rows"] > 1:
        shaded = row_shaded_fraction(rows["slope_m"], rows["pitch_m"], tilt_deg, surface_azimuth_deg, sun_elevation_deg, sun_azimuth_deg)
        kept = 1.0 - shaded * (rows["n_rows"] - 1) / rows["n_rows"]
    if near:
        kept *= nearshade.sunlit_fraction(near["points"], near["boxes"], sun_elevation_deg, sun_azimuth_deg)
    return kept


def apply(poa: Dict[str, float], factor: float) -> Dict[str, float]:
    """The plane-of-array values with the direct part multiplied by `factor` (the effective value keeps its IAM on the direct part)."""
    if factor >= 1.0:
        return poa
    lost = poa["direct"] * (1.0 - factor)
    kept_direct_effective = poa["effective"] - poa["sky"] - poa["ground"]
    return dict(poa, direct=poa["direct"] - lost, **{"global": poa["global"] - lost, "effective": poa["effective"] - kept_direct_effective * (1.0 - factor)})
