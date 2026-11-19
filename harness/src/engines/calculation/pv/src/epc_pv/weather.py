"""PVGIS weather step: the typical meteorological year of a site as the `weather` block of the engine input.

This is a data step, separate from the engine on purpose (ADR-0036): `epc_pv.run` never reads the network, so the same input always gives the same result. This module asks PVGIS once, writes
the answer with its source (database, years, coordinates, date of the query) into the project, and the engine reads that file afterwards.

PVGIS is a free service of the European Commission Joint Research Centre (JRC); its data may be reused citing the source (see `CITATION`). The values are stored as `pending review`.

  fetch_tmy   one call to the `tmy` tool of PVGIS (hourly typical year, 8760 values) and `parse_tmy` on the answer
  parse_tmy   PVGIS answer -> {"weather": <engine block>, "source": {...}}: the typical year mixes months of different years, so every hour is moved to one reference year (2023, no leap day),
              and from PVGIS time (UTC) to local standard time with the given offset, so that the engine buckets the months by local date
Units: ghi, dni, dhi in W/m2 (G(h), Gb(n), Gd(h)); air temperature in C (T2m); wind in m/s at 10 m height (WS10m), as PVGIS gives it.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from epc_pv.model import PvError

API = "https://re.jrc.ec.europa.eu/api/v5_3/"
REFERENCE_YEAR = 2023
HOURS = 8760
COLUMNS = {"ghi": "G(h)", "dni": "Gb(n)", "dhi": "Gd(h)", "temp_air_c": "T2m", "wind_ms": "WS10m"}
CITATION = "PVGIS, European Commission Joint Research Centre (JRC), https://re.jrc.ec.europa.eu/pvg_tools/ ; typical meteorological year, hourly data."
USER_AGENT = "epc-291-harness"


def _check_site(lat: Any, lon: Any, utc_offset_h: Any) -> None:
    for name, v, lo, hi in (("latitude", lat, -90, 90), ("longitude", lon, -180, 180), ("utc_offset_h", utc_offset_h, -14, 14)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
            raise PvError("err_range", name=name, rule=f"{lo} to {hi}", value=v)


def url_for(lat: float, lon: float, start_year: Optional[int] = None, end_year: Optional[int] = None) -> str:
    query = {"lat": lat, "lon": lon, "outputformat": "json"}
    if start_year is not None:
        query["startyear"] = start_year
    if end_year is not None:
        query["endyear"] = end_year
    return API + "tmy?" + urllib.parse.urlencode(query)


def _read(url: str, opener: Optional[Callable], timeout: float) -> Any:
    try:
        if opener is not None:
            return opener(url)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise PvError("err_pvgis_http", detail=f"HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PvError("err_pvgis_http", detail=str(getattr(exc, "reason", exc))) from exc
    except ValueError as exc:
        raise PvError("err_pvgis_payload", detail=str(exc)) from exc


def fetch_tmy(lat: float, lon: float, utc_offset_h: float, *, start_year: Optional[int] = None, end_year: Optional[int] = None,
              opener: Optional[Callable[[str], Any]] = None, timeout: float = 90.0, retrieved: Optional[str] = None) -> Dict[str, Any]:
    """Asks PVGIS for the typical year of (lat, lon). `opener(url) -> parsed JSON` replaces the network (tests, offline copies)."""
    _check_site(lat, lon, utc_offset_h)
    payload = _read(url_for(lat, lon, start_year, end_year), opener, timeout)
    return parse_tmy(payload, utc_offset_h, retrieved=retrieved or date.today().isoformat())


def _rows(payload: Any) -> List[Dict[str, Any]]:
    try:
        rows = payload["outputs"]["tmy_hourly"]
    except (KeyError, TypeError) as exc:
        raise PvError("err_pvgis_payload", detail="outputs.tmy_hourly") from exc
    if not isinstance(rows, list):
        raise PvError("err_pvgis_payload", detail="outputs.tmy_hourly")
    return rows


def _local(stamp: str, utc_offset_h: float) -> datetime:
    """PVGIS time (UTC, `YYYYMMDD:HHMM`) -> local standard time in the reference year, wrapped inside it."""
    try:
        moment = datetime.strptime(stamp, "%Y%m%d:%H%M").replace(year=REFERENCE_YEAR) + timedelta(hours=utc_offset_h)
    except (ValueError, TypeError) as exc:
        raise PvError("err_pvgis_payload", detail=f"time(UTC) {stamp!r}") from exc
    if moment.year < REFERENCE_YEAR:
        moment += timedelta(days=365)
    elif moment.year > REFERENCE_YEAR:
        moment -= timedelta(days=365)
    return moment


def _series(rows: List[Dict[str, Any]], utc_offset_h: float) -> Dict[str, Any]:
    try:
        records = sorted(((_local(r["time(UTC)"], utc_offset_h), [float(r[c]) for c in COLUMNS.values()]) for r in rows), key=lambda x: x[0])
    except (KeyError, TypeError, ValueError) as exc:
        raise PvError("err_pvgis_payload", detail=f"hourly record ({exc})") from exc
    steps = {records[k + 1][0] - records[k][0] for k in range(len(records) - 1)}
    if len(records) != HOURS or steps != {timedelta(hours=1)}:
        raise PvError("err_pvgis_shape", n=len(records), expected=HOURS)
    columns = list(zip(*(values for _, values in records)))
    return {"start": records[0][0].strftime("%Y-%m-%dT%H:%M"), "utc_offset_h": utc_offset_h, "step_minutes": 60,
            **{key: [max(v, 0.0) if key != "temp_air_c" else v for v in columns[i]] for i, key in enumerate(COLUMNS)}}


def _source(payload: Dict[str, Any], utc_offset_h: float, retrieved: str) -> Dict[str, Any]:
    inputs = payload.get("inputs", {}) if isinstance(payload, dict) else {}
    location, meteo = inputs.get("location", {}), inputs.get("meteo_data", {})
    return {"provider": "PVGIS (European Commission JRC)", "service": "tmy", "api": API, "citation": CITATION, "retrieved": retrieved, "status": "pending review",
            "latitude_deg": location.get("latitude"), "longitude_deg": location.get("longitude"), "elevation_m": location.get("elevation"), "utc_offset_h": utc_offset_h,
            "radiation_db": meteo.get("radiation_db"), "meteo_db": meteo.get("meteo_db"), "year_min": meteo.get("year_min"), "year_max": meteo.get("year_max"),
            "months_selected": (payload.get("outputs") or {}).get("months_selected"),
            "notes": {"time": f"hours moved from PVGIS time (UTC) to local standard time (UTC{utc_offset_h:+g}) in the reference year {REFERENCE_YEAR}, without leap day",
                      "wind": "wind speed is at 10 m height, as PVGIS gives it", "typical_year": "months of different years joined; not a measured year"}}


def parse_tmy(payload: Any, utc_offset_h: float, *, retrieved: str = "") -> Dict[str, Any]:
    """The PVGIS `tmy` answer as {"weather": <engine block>, "source": <origin, edition and notes>}."""
    return {"weather": _series(_rows(payload), utc_offset_h), "source": _source(payload, utc_offset_h, retrieved)}


def main(argv=None) -> int:
    """CLI: python -m epc_pv.weather --lat LAT --lon LON --utc-offset H --out DIR  (writes DIR/weather_pvgis.json)."""
    import argparse
    ap = argparse.ArgumentParser(prog="epc_pv.weather", description="Typical meteorological year of a site from PVGIS, as the weather block of epc_pv.")
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--utc-offset", type=float, required=True, help="local standard time minus UTC, in hours (Argentina: -3)")
    ap.add_argument("--start-year", type=int)
    ap.add_argument("--end-year", type=int)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        result = fetch_tmy(a.lat, a.lon, a.utc_offset, start_year=a.start_year, end_year=a.end_year)
    except PvError as e:
        print(f"ERROR {e.en}", file=sys.stderr)
        print(f"ERROR (es) {e.es}", file=sys.stderr)
        return 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "weather_pvgis.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
