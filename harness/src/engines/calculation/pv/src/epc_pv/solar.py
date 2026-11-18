"""Sun position and extraterrestrial irradiance. Pure functions of the instant and the place (no clock, no randomness).

Sun position follows the NOAA solar calculator equations (Meeus, low-precision series): about 0.01 degree for 1900-2100.
    zenith, azimuth (from north, clockwise), and the apparent zenith with the atmospheric refraction correction.
Extraterrestrial normal irradiance: Spencer (1971) series of the day of the year.
"""
import math
from datetime import date
from typing import Tuple

SOLAR_CONSTANT_W_M2 = 1366.1


def julian_day(day: date, minutes_utc: float) -> float:
    """Julian day of a UTC date and minute of the day (day 1 of the proleptic Gregorian calendar is JD 1721425.5)."""
    return day.toordinal() + 1721424.5 + minutes_utc / 1440.0


def _declination_and_eot(jd: float) -> Tuple[float, float]:
    """Declination (radians) and equation of time (minutes) of a Julian day."""
    t = (jd - 2451545.0) / 36525.0
    l0 = math.radians((280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0)
    m = math.radians(357.52911 + t * (35999.05029 - 0.0001537 * t))
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    c = (math.sin(m) * (1.914602 - t * (0.004817 + 0.000014 * t)) + math.sin(2 * m) * (0.019993 - 0.000101 * t) + math.sin(3 * m) * 0.000289)
    omega = math.radians(125.04 - 1934.136 * t)
    lam = math.radians(math.degrees(l0) + c - 0.00569 - 0.00478 * math.sin(omega))
    eps0 = 23.0 + (26.0 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60.0) / 60.0
    eps = math.radians(eps0 + 0.00256 * math.cos(omega))
    decl = math.asin(math.sin(eps) * math.sin(lam))
    y = math.tan(eps / 2.0) ** 2
    eot = 4.0 * math.degrees(y * math.sin(2 * l0) - 2 * e * math.sin(m) + 4 * e * y * math.sin(m) * math.cos(2 * l0) - 0.5 * y * y * math.sin(4 * l0) - 1.25 * e * e * math.sin(2 * m))
    return decl, eot


def refraction_deg(elevation_deg: float) -> float:
    """Atmospheric refraction (degrees) at a true elevation, NOAA approximation."""
    if elevation_deg > 85.0:
        return 0.0
    tan_e = math.tan(math.radians(elevation_deg))
    if elevation_deg > 5.0:
        arcsec = 58.1 / tan_e - 0.07 / tan_e ** 3 + 0.000086 / tan_e ** 5
    elif elevation_deg > -0.575:
        e = elevation_deg
        arcsec = 1735.0 + e * (-518.2 + e * (103.4 + e * (-12.79 + e * 0.711)))
    else:
        arcsec = -20.772 / tan_e
    return arcsec / 3600.0


def position(day: date, minutes_utc: float, latitude_deg: float, longitude_deg: float) -> Tuple[float, float, float]:
    """(true zenith, apparent zenith, azimuth from north clockwise) in degrees, east longitudes positive."""
    decl, eot = _declination_and_eot(julian_day(day, minutes_utc))
    lat = math.radians(latitude_deg)
    solar_minutes = (minutes_utc + eot + 4.0 * longitude_deg) % 1440.0
    hour_angle = math.radians(solar_minutes / 4.0 - 180.0)
    cos_zen = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(hour_angle)
    zenith = math.degrees(math.acos(max(-1.0, min(1.0, cos_zen))))
    azimuth = (math.degrees(math.atan2(math.sin(hour_angle), math.cos(hour_angle) * math.sin(lat) - math.tan(decl) * math.cos(lat))) + 180.0) % 360.0
    return zenith, zenith - refraction_deg(90.0 - zenith), azimuth


def extra_radiation_w_m2(day_of_year: int, solar_constant: float = SOLAR_CONSTANT_W_M2) -> float:
    """Extraterrestrial irradiance on a plane normal to the sun for the day of the year (Spencer)."""
    g = 2.0 * math.pi * (day_of_year - 1) / 365.0
    return solar_constant * (1.00011 + 0.034221 * math.cos(g) + 0.00128 * math.sin(g) + 0.000719 * math.cos(2 * g) + 0.000077 * math.sin(2 * g))
