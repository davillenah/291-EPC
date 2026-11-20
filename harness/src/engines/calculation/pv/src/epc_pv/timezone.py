"""Time zone of a place: the standard (winter) UTC offset of the weather file, taken from latitude and longitude.

PVGIS hours are matched to the sun with this offset, so it must be the standard offset, not the daylight-saving one: of the offsets of January and July the smaller one. The zone comes from the offline
`timezonefinder` database and the offset from the system `zoneinfo`; no network and no value typed by hand. Returns None when no zone is found (open sea) or the package is missing: the caller asks the person.
"""
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def standard_utc_offset_h(lat: float, lon: float) -> Optional[float]:
    try:
        from timezonefinder import TimezoneFinder
        name = TimezoneFinder().timezone_at(lat=lat, lng=lon)
        if name is None:
            return None
        zone = ZoneInfo(name)
    except (ImportError, ZoneInfoNotFoundError):
        return None
    return min(zone.utcoffset(datetime(2026, m, 1)).total_seconds() for m in (1, 7)) / 3600.0
