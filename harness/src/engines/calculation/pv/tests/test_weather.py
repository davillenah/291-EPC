"""The PVGIS weather step: the answer of the `tmy` tool becomes the weather block of the engine (no network: the opener is replaced)."""
import json
import tempfile
import unittest
import urllib.error
from unittest import mock
from datetime import datetime, timedelta
from pathlib import Path

from epc_pv import PvError, run, weather
from test_pv import doc


def payload(shuffle_years: bool = True):
    """A PVGIS-shaped answer: 8760 hourly records whose months come from different years, as a typical year does (UTC stamps)."""
    years = {1: 2008, 2: 2008, 3: 2010, 4: 2018, 5: 2010, 6: 2010, 7: 2023, 8: 2023, 9: 2007, 10: 2015, 11: 2012, 12: 2023}
    rows, t = [], datetime(2023, 1, 1)
    while t.year == 2023:
        sun = 800.0 if 9 <= t.hour <= 20 else 0.0
        rows.append({"time(UTC)": t.replace(year=years[t.month] if shuffle_years else 2023).strftime("%Y%m%d:%H%M"), "T2m": 20.0 + t.month, "RH": 50.0, "G(h)": sun, "Gb(n)": sun * 0.7,
                     "Gd(h)": sun * 0.2, "IR(h)": 300.0, "WS10m": 3.0, "WD10m": 90.0, "SP": 101000.0})
        t += timedelta(hours=1)
    meta = {"location": {"latitude": -34.6, "longitude": -58.4, "elevation": 27.0}, "meteo_data": {"radiation_db": "PVGIS-SARAH3", "meteo_db": "ERA5", "year_min": 2005, "year_max": 2023}}
    return {"inputs": meta, "outputs": {"tmy_hourly": rows, "months_selected": [{"month": m, "year": y} for m, y in years.items()]}}


class TestParse(unittest.TestCase):
    def test_a_typical_year_is_one_continuous_local_year(self):
        r = weather.parse_tmy(payload(), -3, retrieved="2026-11-19")
        w = r["weather"]
        self.assertEqual((w["start"], w["utc_offset_h"], w["step_minutes"]), ("2023-01-01T00:00", -3, 60))
        for key in ("ghi", "dni", "dhi", "temp_air_c", "wind_ms"):
            self.assertEqual(len(w[key]), 8760)
        self.assertEqual(w["wind_ms"][0], 3.0)

    def test_the_hours_move_to_local_time(self):
        w = weather.parse_tmy(payload(), -3)["weather"]
        # UTC 12:00 is local 09:00: the sun in the fake file starts at 09 UTC, so it starts at 06 local
        self.assertEqual((w["ghi"][5], w["ghi"][6]), (0.0, 800.0))

    def test_the_source_is_recorded_and_pending_review(self):
        s = weather.parse_tmy(payload(), -3, retrieved="2026-11-19")["source"]
        self.assertEqual((s["status"], s["retrieved"], s["radiation_db"], s["elevation_m"]), ("pending review", "2026-11-19", "PVGIS-SARAH3", 27.0))
        self.assertIn("Joint Research Centre", s["citation"])

    def test_a_positive_offset_wraps_inside_the_year(self):
        w = weather.parse_tmy(payload(), 5.5)["weather"]
        self.assertEqual((w["start"], len(w["ghi"])), ("2023-01-01T00:30", 8760))

    def test_a_wrong_answer_is_refused_in_both_languages(self):
        for bad in ({}, {"outputs": {"tmy_hourly": "x"}}, {"outputs": {"tmy_hourly": [{"time(UTC)": "x"}]}}):
            with self.assertRaises(PvError) as ctx:
                weather.parse_tmy(bad, -3)
            self.assertEqual(ctx.exception.code, "err_pvgis_payload")
            self.assertTrue(ctx.exception.es)
        short = payload()
        short["outputs"]["tmy_hourly"] = short["outputs"]["tmy_hourly"][:100]
        with self.assertRaises(PvError) as ctx:
            weather.parse_tmy(short, -3)
        self.assertEqual(ctx.exception.code, "err_pvgis_shape")

    def test_the_engine_runs_on_the_converted_year(self):
        d = doc()
        d["weather"] = weather.parse_tmy(payload(), -3)["weather"]
        t = run(d).as_dict()["totals"]
        self.assertGreater(t["specific_yield_kwh_kwp"], 500)
        self.assertEqual(len(t["monthly_ac_kwh"]), 12)
        self.assertTrue(all(m > 0 for m in t["monthly_ac_kwh"]))


class TestFetch(unittest.TestCase):
    def test_the_url_asks_for_the_tmy_tool(self):
        u = weather.url_for(-34.6, -58.4, 2010, 2020)
        self.assertTrue(u.startswith("https://re.jrc.ec.europa.eu/api/v5_3/tmy?"))
        for part in ("lat=-34.6", "lon=-58.4", "outputformat=json", "startyear=2010", "endyear=2020"):
            self.assertIn(part, u)

    def test_the_opener_replaces_the_network(self):
        seen = []
        r = weather.fetch_tmy(-34.6, -58.4, -3, opener=lambda url: seen.append(url) or payload(), retrieved="2026-11-19")
        self.assertEqual(len(seen), 1)
        self.assertEqual(len(r["weather"]["ghi"]), 8760)

    def test_a_bad_site_is_refused_before_any_call(self):
        for args in ((95, 0, -3), (0, 200, -3), (0, 0, 20)):
            with self.assertRaises(PvError):
                weather.fetch_tmy(*args, opener=lambda url: self.fail("no call expected"))

    def _urlopen(self, **kw):
        return mock.patch("urllib.request.urlopen", **kw)

    def test_the_real_reader_parses_the_body_and_sends_an_agent(self):
        body = mock.MagicMock()
        body.__enter__.return_value.read.return_value = json.dumps(payload()).encode()
        with self._urlopen(return_value=body) as op:
            r = weather.fetch_tmy(-34.6, -58.4, -3, retrieved="2026-11-19")
        self.assertEqual(len(r["weather"]["ghi"]), 8760)
        self.assertEqual(op.call_args[0][0].get_header("User-agent"), "epc-291-harness")

    def test_network_failures_are_pvgis_errors(self):
        errors = (urllib.error.HTTPError("u", 503, "x", {}, None), urllib.error.URLError("no route"), TimeoutError("slow"))
        for exc in errors:
            with self._urlopen(side_effect=exc), self.assertRaises(PvError) as ctx:
                weather.fetch_tmy(-34.6, -58.4, -3)
            self.assertEqual(ctx.exception.code, "err_pvgis_http")
        body = mock.MagicMock()
        body.__enter__.return_value.read.return_value = b"<html>"
        with self._urlopen(return_value=body), self.assertRaises(PvError) as ctx:
            weather.fetch_tmy(-34.6, -58.4, -3)
        self.assertEqual(ctx.exception.code, "err_pvgis_payload")

    def test_the_cli_reports_an_error_in_both_languages(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(weather, "fetch_tmy", side_effect=PvError("err_pvgis_http", detail="down")):
            self.assertEqual(weather.main(["--lat", "-34.6", "--lon", "-58.4", "--utc-offset", "-3", "--out", tmp]), 1)

    def test_the_cli_writes_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = weather.fetch_tmy
            weather.fetch_tmy = lambda *a, **k: real(*a, opener=lambda url: payload(), **k)
            try:
                self.assertEqual(weather.main(["--lat", "-34.6", "--lon", "-58.4", "--utc-offset", "-3", "--out", tmp]), 0)
            finally:
                weather.fetch_tmy = real
            data = json.loads((Path(tmp) / "weather_pvgis.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(data), ["source", "weather"])


if __name__ == "__main__":
    unittest.main()
