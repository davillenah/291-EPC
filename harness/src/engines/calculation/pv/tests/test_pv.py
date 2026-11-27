"""The photovoltaic engine: each formula, the string layout, the pipeline, the contract (schemas, English and Spanish texts) and the CLI."""
import json
import math
import tempfile
import unittest
from datetime import date
from pathlib import Path

from epc_pv import Options, PvError, __main__ as cli, config, irradiance, messages, power, run, solar, strings, thermal

SCHEMAS = Path(__file__).resolve().parents[1] / "src" / "epc_pv" / "schema"
MODULE = {"pmax_w": 550.0, "voc_v": 49.9, "vmp_v": 41.8, "isc_a": 13.9, "imp_a": 13.16, "beta_voc_pct_c": -0.27, "gamma_pmax_pct_c": -0.34}
INVERTER = {"pac0_w": 100000.0, "mppt_v_min": 200.0, "mppt_v_max": 1000.0, "vdc_max_v": 1100.0, "n_mppt": 10, "i_max_input_a": 30.0, "isc_max_input_a": 45.0}


def weather(days: int = 3):
    """A clear-looking synthetic day repeated: bell of irradiance between 6 and 18 h."""
    ghi, dni, dhi, temp, wind = [], [], [], [], []
    for h in range(24 * days):
        x = math.sin(math.pi * (h % 24 - 6) / 12.0) if 6 <= h % 24 <= 18 else 0.0
        ghi.append(round(900 * x, 1))
        dni.append(round(700 * x, 1))
        dhi.append(round(150 * x, 1))
        temp.append(20.0)
        wind.append(2.0)
    return {"start": "2023-01-01T00:00", "utc_offset_h": -3, "step_minutes": 60, "ghi": ghi, "dni": dni, "dhi": dhi, "temp_air_c": temp, "wind_ms": wind}


def doc(**array):
    spec = {"id": "A1", "tilt_deg": 30, "azimuth_deg": 0, "n_modules": 1000, "module": dict(MODULE), "inverter": dict(INVERTER), "dc_ac_ratio": 1.2}
    spec.update(array)
    return {"site": {"latitude_deg": -34.6, "longitude_deg": -58.4, "albedo": 0.2, "design_t_min_c": -5}, "weather": weather(), "arrays": [spec]}


class TestSun(unittest.TestCase):
    def test_julian_day_of_j2000(self):
        self.assertAlmostEqual(solar.julian_day(date(2000, 1, 1), 720.0), 2451545.0)

    def test_the_sun_at_the_equinox_noon_on_the_equator_is_overhead(self):
        zen, app, _ = solar.position(date(2023, 3, 20), 12 * 60 + 7.5, 0.0, 0.0)          # near the equinox, the equation of time is about -7.5 min
        self.assertLess(zen, 1.0)
        self.assertLessEqual(app, zen)

    def test_the_sun_at_noon_in_the_south_is_north(self):
        best = min((solar.position(date(2023, 6, 21), m, -34.6, -58.4) for m in range(14 * 60, 17 * 60)), key=lambda t: t[0])
        self.assertTrue(best[2] < 2.0 or best[2] > 358.0)

    def test_the_summer_solstice_noon_zenith_of_buenos_aires(self):
        zen = min(solar.position(date(2023, 12, 21), m, -34.6, -58.4)[0] for m in range(14 * 60, 17 * 60))
        self.assertAlmostEqual(zen, 34.6 - 23.44, delta=0.15)

    def test_refraction_is_zero_high_and_grows_at_the_horizon(self):
        self.assertEqual(solar.refraction_deg(90), 0.0)
        self.assertGreater(solar.refraction_deg(0.0), 0.4)

    def test_extra_radiation_is_largest_in_january(self):
        self.assertGreater(solar.extra_radiation_w_m2(3), solar.extra_radiation_w_m2(185))
        self.assertAlmostEqual(solar.extra_radiation_w_m2(1), 1366.1 * (1.00011 + 0.034221 + 0.000719), delta=0.5 + 0.0)


class TestIrradiance(unittest.TestCase):
    def test_the_angle_of_incidence(self):
        self.assertAlmostEqual(irradiance.cos_aoi(0, 0, 30, 0), math.cos(math.radians(30)))
        self.assertAlmostEqual(irradiance.cos_aoi(30, 0, 30, 0), 1.0)             # the sun is normal to the plane
        self.assertAlmostEqual(irradiance.cos_aoi(90, 90, 60, 270), -math.sin(math.radians(60)))

    def test_the_incidence_modifier(self):
        self.assertEqual(irradiance.iam_ashrae(1.0, 0.05), 1.0)
        self.assertAlmostEqual(irradiance.iam_ashrae(0.5, 0.05), 0.95)
        self.assertEqual(irradiance.iam_ashrae(-0.2, 0.05), 0.0)
        self.assertEqual(irradiance.iam_ashrae(1e-4, 0.05), 0.0)

    def test_a_horizontal_plane_has_no_ground_part_and_the_global_is_the_ghi(self):
        poa = irradiance.plane_of_array("isotropic", {"tilt_deg": 0, "azimuth_deg": 0}, {"zenith_deg": 40, "azimuth_deg": 100, "dni_extra": 1360},
                                        {"ghi": 100 + 600 * math.cos(math.radians(40)), "dni": 600, "dhi": 100}, 0.3, 0.05)
        self.assertEqual(poa["ground"], 0.0)
        self.assertAlmostEqual(poa["global"], 100 + 600 * math.cos(math.radians(40)))

    def test_a_vertical_plane_sees_half_the_sky_and_half_the_ground(self):
        poa = irradiance.plane_of_array("isotropic", {"tilt_deg": 90, "azimuth_deg": 0}, {"zenith_deg": 90, "azimuth_deg": 180, "dni_extra": 1360}, {"ghi": 200, "dni": 0, "dhi": 200}, 0.5, 0.05)
        self.assertAlmostEqual(poa["sky"], 100.0)
        self.assertAlmostEqual(poa["ground"], 50.0)

    def test_hay_davies_with_no_direct_beam_is_isotropic(self):
        args = ({"tilt_deg": 30, "azimuth_deg": 0}, {"zenith_deg": 50, "azimuth_deg": 90, "dni_extra": 1360}, {"ghi": 150, "dni": 0, "dhi": 150}, 0.2, 0.05)
        self.assertAlmostEqual(irradiance.plane_of_array("haydavies", *args)["global"], irradiance.plane_of_array("isotropic", *args)["global"])

    def test_an_unknown_model_is_refused(self):
        with self.assertRaises(PvError):
            irradiance.sky_diffuse("perez", 30, 0.5, 40, 500, 100, 1360)


class TestPower(unittest.TestCase):
    def test_cell_temperature(self):
        self.assertAlmostEqual(thermal.faiman_cell_c(800, 20, 0, 25, 6.84), 20 + 800 / 25)
        self.assertLess(thermal.faiman_cell_c(800, 20, 5, 25, 6.84), thermal.faiman_cell_c(800, 20, 0, 25, 6.84))

    def test_dc_power_at_stc_and_with_heat(self):
        self.assertAlmostEqual(power.dc_power_w(1000, 1000, 25, -0.004), 1000.0)
        self.assertAlmostEqual(power.dc_power_w(1000, 500, 45, -0.004), 500 * (1 - 0.004 * 20))
        self.assertEqual(power.dc_power_w(1000, 0, 25, -0.004), 0.0)

    def test_the_inverter_clips_at_its_rating_and_gives_nothing_without_input(self):
        self.assertEqual(power.inverter_ac_w(0, 1000, 0.96, 0.9637), 0.0)
        self.assertEqual(power.inverter_ac_w(5000, 1000, 0.96, 0.9637), 1000.0)
        self.assertGreater(power.inverter_curve_w(5000, 1000, 0.96, 0.9637), 1000.0)
        mid = power.inverter_ac_w(520, 1000, 0.96, 0.9637)
        self.assertTrue(0.9 * 520 < mid < 520)

    def test_the_losses_multiply(self):
        self.assertAlmostEqual(config.losses_total_pct({"a": 10, "b": 10}), 19.0)
        self.assertAlmostEqual(config.losses_total_pct(config.params()["losses_pct"]), 14.0757, places=3)


class TestStrings(unittest.TestCase):
    def test_the_range_follows_the_cold_and_hot_voltages(self):
        r = strings.series_range(MODULE, INVERTER, -5.0, 70.0)
        voc_cold = 49.9 * (1 - 0.0027 * (-5 - 25))
        self.assertEqual(r["s_max"], math.floor(1100 / voc_cold))
        self.assertEqual(r["s_min"], math.ceil(200 / (41.8 * (1 - 0.0027 * 45))))

    def test_the_layout_is_whole_strings_and_within_the_limits(self):
        lay = strings.layout({"id": "A", "n_modules": 1000, "module": MODULE, "inverter": INVERTER, "dc_ac_ratio": 1.2}, -5.0, 70.0, config.params()["strings"])
        self.assertEqual(lay["modules"], lay["strings"] * lay["n_series"])
        self.assertGreaterEqual(lay["modules"], 1000)
        self.assertLess(lay["modules"] - 1000, lay["n_series"])
        self.assertTrue(lay["series_range"]["s_min"] <= lay["n_series"] <= lay["series_range"]["s_max"])
        self.assertEqual(lay["inverters"], max(1, int(lay["modules"] * 550 / (1.2 * 100000) + 0.5)))

    def test_a_given_length_is_kept_or_refused(self):
        spec = {"id": "A", "n_modules": 100, "module": MODULE, "inverter": INVERTER, "n_inverters": 1, "n_series": 10}
        self.assertEqual(strings.layout(spec, -5.0, 70.0, config.params()["strings"])["n_series"], 10)
        spec["n_series"] = 40
        with self.assertRaises(PvError) as ctx:
            strings.layout(spec, -5.0, 70.0, config.params()["strings"])
        self.assertEqual(ctx.exception.code, "err_series_fixed")

    def test_no_layout_when_the_window_is_too_narrow(self):
        narrow = dict(INVERTER, mppt_v_min=900.0, mppt_v_max=910.0, vdc_max_v=950.0)
        with self.assertRaises(PvError) as ctx:
            strings.layout({"id": "A", "n_modules": 100, "module": MODULE, "inverter": narrow, "n_inverters": 1}, -5.0, 70.0, config.params()["strings"])
        self.assertEqual(ctx.exception.code, "err_no_series")

    def test_too_many_strings_per_input_is_a_warning(self):
        lay = strings.layout({"id": "A", "n_modules": 5000, "module": MODULE, "inverter": INVERTER, "n_inverters": 1}, -5.0, 70.0, config.params()["strings"])
        self.assertEqual([w["code"] for w in lay["warnings"]], ["warn_current"])

    def test_the_inverters_need_a_count_or_a_ratio(self):
        with self.assertRaises(PvError):
            strings.layout({"id": "A", "n_modules": 100, "module": MODULE, "inverter": INVERTER}, -5.0, 70.0, config.params()["strings"])

    def test_the_policies(self):
        rng = {"s_min": 6, "s_max": 20}
        self.assertEqual(strings.choose_series(rng, MODULE, INVERTER, "max_voltage", None, "A"), 20)
        self.assertEqual(strings.choose_series(rng, MODULE, INVERTER, "mid_mppt", None, "A"), 14)


class TestPipeline(unittest.TestCase):
    def test_a_day_has_energy_and_consistent_numbers(self):
        r = run(doc()).as_dict()
        a = r["arrays"][0]
        self.assertEqual(r["counts"]["hours"], 72)
        self.assertGreater(a["ac_kwh"], 0)
        self.assertLess(a["ac_kwh"], a["dc_kwh"])
        self.assertAlmostEqual(sum(a["monthly_ac_kwh"]), a["ac_kwh"], delta=0.01)
        self.assertEqual(r["totals"]["ac_kwh"], a["ac_kwh"])
        self.assertAlmostEqual(a["dc_ac_ratio"], a["dc_kwp"] / a["ac_kw"], places=3)
        self.assertAlmostEqual(a["inverter_ac_kw"] * a["inverters"], a["ac_kw"], places=2)      # the rating of one inverter (the AC feeder of each unit is sized from it)
        self.assertTrue(0.5 < a["performance_ratio"] < 1.0)

    def test_the_input_can_be_text_or_bytes(self):
        d = doc()
        self.assertEqual(run(json.dumps(d)).as_dict(), run(json.dumps(d).encode()).as_dict())

    def test_the_result_is_deterministic(self):
        self.assertEqual(run(doc()).as_dict(), run(doc()).as_dict())

    def test_more_modules_give_more_energy(self):
        self.assertGreater(run(doc(n_modules=2000)).totals["ac_kwh"], run(doc(n_modules=1000)).totals["ac_kwh"])

    def test_a_cloudless_plane_facing_the_sun_beats_a_flat_one_in_the_southern_winter(self):
        d = doc(tilt_deg=45)
        flat = doc(tilt_deg=0)
        for x in (d, flat):
            x["weather"]["start"] = "2023-06-20T00:00"
        self.assertGreater(run(d).totals["ac_kwh"], run(flat).totals["ac_kwh"])

    def test_isotropic_and_hay_davies_differ_a_little(self):
        a = run(doc(), Options("haydavies")).totals["ac_kwh"]
        b = run(doc(), Options("isotropic")).totals["ac_kwh"]
        self.assertNotEqual(a, b)
        self.assertAlmostEqual(a / b, 1.0, delta=0.1)

    def test_an_oversized_array_clips(self):
        self.assertGreater(run(doc(dc_ac_ratio=3.0)).arrays[0]["clipping_kwh"], 0.0)
        self.assertEqual(run(doc(dc_ac_ratio=1.0)).arrays[0]["clipping_kwh"], 0.0)

    def test_two_arrays_add_up(self):
        d = doc()
        d["arrays"].append(dict(d["arrays"][0], id="A2", azimuth_deg=90))
        r = run(d).as_dict()
        self.assertEqual(r["counts"]["arrays"], 2)
        self.assertAlmostEqual(r["totals"]["ac_kwh"], sum(a["ac_kwh"] for a in r["arrays"]), delta=0.01)

    def test_the_assumptions_can_be_replaced(self):
        d = doc()
        d["assumptions"] = {"losses_pct": {"all": 0.0}}
        self.assertGreater(run(d).totals["ac_kwh"], run(doc()).totals["ac_kwh"])

    def test_the_minimum_temperature_defaults_to_the_weather_with_a_warning(self):
        d = doc()
        del d["site"]["design_t_min_c"]
        self.assertIn("t_min_from_weather", [w["code"] for w in run(d).warnings])
        self.assertNotIn("t_min_from_weather", [w["code"] for w in run(doc()).warnings])


class TestInput(unittest.TestCase):
    def assertRefused(self, d, code):
        with self.assertRaises(PvError) as ctx:
            run(d)
        self.assertEqual(ctx.exception.code, code)
        return ctx.exception

    def test_bad_documents(self):
        self.assertRefused("not json", "err_json")
        self.assertRefused([], "err_type")
        self.assertRefused({}, "err_missing")
        self.assertRefused({**doc(), "arrays": []}, "err_type")

    def test_bad_values(self):
        d = doc()
        d["site"]["latitude_deg"] = 120
        self.assertRefused(d, "err_range")
        d = doc()
        d["weather"]["dni"].pop()
        self.assertRefused(d, "err_length")
        d = doc()
        d["weather"]["ghi"][3] = -1
        self.assertRefused(d, "err_range")
        d = doc()
        d["weather"]["start"] = "yesterday"
        self.assertRefused(d, "err_range")
        self.assertRefused(doc(n_modules=0), "err_range")
        self.assertRefused(doc(tilt_deg="steep"), "err_type")
        d = doc()
        del d["arrays"][0]["module"]["voc_v"]
        self.assertRefused(d, "err_missing")
        d = doc()
        del d["weather"]["wind_ms"]
        self.assertRefused(d, "err_missing")

    def test_errors_speak_english_and_spanish(self):
        e = self.assertRefused({}, "err_missing")
        self.assertIn("missing", str(e))
        self.assertEqual(e.en, str(e))
        self.assertIn("falta en la entrada", e.es)
        self.assertNotIn("the input", e.es)


class TestContract(unittest.TestCase):
    def test_the_documents_follow_their_schemas(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        d = doc()
        jsonschema.validate(d, json.loads((SCHEMAS / "input.schema.json").read_text(encoding="utf-8")))
        jsonschema.validate(run(d).as_dict(), json.loads((SCHEMAS / "output.schema.json").read_text(encoding="utf-8")))

    def test_every_message_and_label_has_both_languages(self):
        for table in (messages.MESSAGES, messages.LABELS):
            for key, entry in table.items():
                self.assertEqual(sorted(entry), ["en", "es"], key)
                self.assertTrue(entry["en"].strip() and entry["es"].strip(), key)

    def test_the_warnings_are_in_both_languages_and_carry_a_code(self):
        r = run(doc()).as_dict()
        self.assertTrue(r["warnings"])
        for w in r["warnings"]:
            self.assertTrue(w["code"] and w["en"] and w["es"])
        self.assertEqual(r["schema_version"], "1.0")
        self.assertIn("ac_kwh", r["labels"])

    def test_the_two_texts_of_a_message_use_the_same_parameters(self):
        import re
        for code, entry in messages.MESSAGES.items():
            self.assertEqual(sorted(re.findall(r"\{(\w+)", entry["en"])), sorted(re.findall(r"\{(\w+)", entry["es"])), code)

    def test_the_norm_register_points_to_real_parameters(self):
        reg = json.loads((Path(__file__).resolve().parents[1] / "src" / "epc_pv" / "norm_register" / "typical.json").read_text(encoding="utf-8"))
        params = config.params()
        for rec in reg["records"]:
            node = params
            for part in rec["location"]["pointer"].strip("/").split("/"):
                node = node[part]
            self.assertEqual(rec["status"], "pending")


class TestVersion(unittest.TestCase):
    def test_the_version_is_the_same_everywhere(self):
        import epc_pv
        self.assertEqual(epc_pv.__version__, config.VERSION)
        self.assertEqual(run(doc()).as_dict()["schema_version"], config.SCHEMA_VERSION)


class TestCli(unittest.TestCase):
    def test_writes_the_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.json"
            src.write_text(json.dumps(doc()), encoding="utf-8")
            self.assertEqual(cli.main([str(src), "--out", str(Path(tmp) / "out")]), 0)
            out = json.loads((Path(tmp) / "out" / "pv_yield.json").read_text(encoding="utf-8"))
        self.assertEqual(out["counts"]["arrays"], 1)

    def test_an_error_gives_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.json"
            src.write_text("{}", encoding="utf-8")
            self.assertEqual(cli.main([str(src), "--out", str(Path(tmp) / "out")]), 1)
            self.assertEqual(cli.main([str(Path(tmp) / "missing.json"), "--out", str(Path(tmp) / "out")]), 1)


if __name__ == "__main__":
    unittest.main()


class TestFeasibility(unittest.TestCase):
    """The saving, the payback, the technical summary and the inverters raised for the input current (moved from the discipline stage, same numbers)."""

    def run_doc(self, **array):
        return run(doc(**array)).as_dict()

    def test_the_saving_is_the_yearly_energy_times_the_price_and_the_payback_the_investment_over_it(self):
        from epc_pv import feasibility
        result = self.run_doc()
        eco = feasibility.economic_summary(result, {"energy_price": 0.1, "currency": "USD", "investment": 20000})
        kwh = result["totals"]["ac_kwh"]
        self.assertAlmostEqual(eco["saving_year"], kwh * 0.1, delta=0.01)
        self.assertAlmostEqual(eco["simple_payback_years"], 20000 / (kwh * 0.1), delta=0.01)
        self.assertEqual(len(eco["saving_month"]), 12)

    def test_without_a_price_it_says_what_to_give_in_both_languages(self):
        from epc_pv import feasibility
        said = feasibility.economic_summary(self.run_doc(), None)
        self.assertTrue(said["en"] and said["es"])

    def test_the_technical_summary_reads_only_the_result(self):
        from epc_pv import feasibility
        summary = feasibility.technical_summary(self.run_doc(), None)
        self.assertEqual(summary["status"], "pending review")
        self.assertIn("economic", summary)
        self.assertEqual(set(summary["installed"]), {"modules", "dc_kwp", "ac_kw", "inverters"})

    def test_inverters_are_raised_only_for_an_auto_count_over_the_current_limit(self):
        from epc_pv import feasibility
        section = {"document": doc()}
        result = self.run_doc()
        self.assertIs(feasibility.add_inverters_for_current(section, result)[1], result)

    def test_an_auto_count_over_the_current_limit_is_raised_and_said_with_the_real_ratio(self):
        from epc_pv import feasibility
        inverter = {"auto": True, "n_mppt": 6, "pac0_w": 100000.0}
        section = {"document": {"arrays": [{"id": "A1", "inverter": inverter, "n_modules": 100}]}}
        first = {"arrays": [{"inverters": 90, "dc_kwp": 10800.0, "strings": {"strings": 672, "strings_per_mppt": 2, "strings_per_mppt_limit": 1}}], "warnings": []}
        real, feasibility._rerun = feasibility._rerun, lambda sec: {"arrays": [], "warnings": []}
        self.addCleanup(setattr, feasibility, "_rerun", real)
        new_section, out = feasibility.add_inverters_for_current(section, first)
        self.assertEqual(new_section["document"]["arrays"][0]["n_inverters"], 112)
        self.assertEqual([w["code"] for w in out["warnings"]], ["inverters_raised"])

    def test_the_rerun_takes_the_options_of_the_section(self):
        from epc_pv import feasibility
        out = feasibility._rerun({"document": doc(), "options": {}})
        self.assertIn("totals", out)
