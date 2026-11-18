"""Irradiance on the plane of the array: transposition of the horizontal components and the angle-of-incidence loss.

    cos(aoi) = cos(z) cos(b) + sin(z) sin(b) cos(az_sun - az_surface)        b: tilt, z: apparent zenith
    direct   = DNI max(cos aoi, 0)
    ground   = albedo GHI (1 - cos b) / 2
    isotropic sky   = DHI (1 + cos b) / 2
    Hay-Davies sky  = DHI [AI Rb + (1 - AI)(1 + cos b)/2],  AI = DNI / DNI_extra,  Rb = max(cos aoi, 0) / max(cos z, cos 89.0 deg)
    IAM (ASHRAE)    = max(0, 1 - b0 (1 / cos aoi - 1)), 0 beyond 90 degrees
"""
import math
from typing import Dict

from epc_pv.model import PvError

MODELS = ("haydavies", "isotropic")
MIN_COS_ZENITH = 0.01745                                 # cos(89 degrees): keeps Rb finite at the horizon


def cos_aoi(tilt_deg: float, surface_azimuth_deg: float, zenith_deg: float, sun_azimuth_deg: float) -> float:
    b, z = math.radians(tilt_deg), math.radians(zenith_deg)
    return math.cos(z) * math.cos(b) + math.sin(z) * math.sin(b) * math.cos(math.radians(sun_azimuth_deg - surface_azimuth_deg))


def iam_ashrae(cos_incidence: float, b0: float) -> float:
    if cos_incidence <= 0.0:
        return 0.0
    return max(0.0, 1.0 - b0 * (1.0 / cos_incidence - 1.0))


def sky_diffuse(model: str, tilt_deg: float, cos_incidence: float, zenith_deg: float, dni: float, dhi: float, dni_extra: float) -> float:
    cos_tilt = math.cos(math.radians(tilt_deg))
    if model == "isotropic":
        return dhi * 0.5 * (1.0 + cos_tilt)
    if model != "haydavies":
        raise PvError("err_choice", name="transposition", choices=list(MODELS), value=model)
    ai = dni / dni_extra
    rb = max(cos_incidence, 0.0) / max(math.cos(math.radians(zenith_deg)), MIN_COS_ZENITH)
    return max(dhi * (ai * rb + (1.0 - ai) * 0.5 * (1.0 + cos_tilt)), 0.0)


def plane_of_array(model: str, surface: Dict[str, float], sun: Dict[str, float], sky: Dict[str, float], albedo: float, iam_b0: float) -> Dict[str, float]:
    """The plane-of-array components (W/m2) of one instant.

    surface: tilt_deg, azimuth_deg. sun: zenith_deg (apparent), azimuth_deg, dni_extra. sky: ghi, dni, dhi.
    Returns direct, sky, ground, global, effective (the direct part reduced by the IAM) and cos_aoi."""
    c = cos_aoi(surface["tilt_deg"], surface["azimuth_deg"], sun["zenith_deg"], sun["azimuth_deg"])
    direct = max(sky["dni"] * c, 0.0)
    diffuse = sky_diffuse(model, surface["tilt_deg"], c, sun["zenith_deg"], sky["dni"], sky["dhi"], sun["dni_extra"])
    ground = albedo * sky["ghi"] * 0.5 * (1.0 - math.cos(math.radians(surface["tilt_deg"])))
    total = direct + diffuse + ground
    return {"direct": direct, "sky": diffuse, "ground": ground, "global": total, "effective": direct * iam_ashrae(c, iam_b0) + diffuse + ground, "cos_aoi": c}
