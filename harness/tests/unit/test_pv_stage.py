"""Stage 3 runs `epc_pv` (optional slice 32) when the `pv` inputs are given, adds the plant layout when `layout` is given, and is unchanged when they are not."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src/engines/calculation/pv/tests"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src/engines/calculation/pv/src"))
import test_pv as PV  # noqa: E402
import test_pipeline_wiring as W  # noqa: E402
from disciplines.electrical_lv.pipeline import STAGES, run  # noqa: E402

LAYOUT = {"site": {"width_m": 200, "length_m": 120, "setback_m": 5}, "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02,
          "table": {"rows": 2, "modules_per_row": 28, "orientation": "portrait"}, "table_gap_m": 0.5, "road_width_m": 4,
          "station": {"width_m": 6, "depth_m": 2.5}, "inverter_pad": {"width_m": 0.7, "depth_m": 0.4}}


def ctx_with(section=None):
    inputs = W.inputs_doc()
    if section is not None:
        inputs["pv"] = section
    ctx = W.context(engine_inputs=inputs)
    run(ctx, stop_after=2, run_id="r3")
    return ctx


class PvSliceTests(unittest.TestCase):
    def test_without_the_section_stage_3_is_what_it_was(self):
        res = STAGES[2].run(ctx_with())
        self.assertEqual(res.status, "ok")
        self.assertEqual(set(res.outputs), {"load_schedule", "demand"})

    def test_with_the_section_it_adds_the_pv_result(self):
        res = STAGES[2].run(ctx_with({"document": PV.doc()}))
        self.assertEqual(res.status, "ok")
        self.assertIn("totals", res.outputs["pv"])
        self.assertNotIn("layout", res.outputs["pv"])
        self.assertIn("epc_pv.run", {c["function"] for c in res.engine_calls})
        json.dumps(res.to_dict())

    def test_with_a_layout_it_adds_the_geometry_and_one_more_engine_call(self):
        res = STAGES[2].run(ctx_with({"document": PV.doc(), "layout": copy.deepcopy(LAYOUT)}))
        geometry = res.outputs["pv"]["layout"]
        self.assertTrue(geometry["fits"])
        self.assertIn("epc_pv.plan_layout", {c["function"] for c in res.engine_calls})
        self.assertFalse([f for f in res.findings if f["severity"] == "major" and f["document"] == "pv"])

    def test_tables_that_do_not_fit_raise_a_major_finding(self):
        small = copy.deepcopy(LAYOUT)
        small["site"].update(width_m=30, length_m=20)
        res = STAGES[2].run(ctx_with({"document": PV.doc(), "layout": small}))
        self.assertTrue([f for f in res.findings if f["severity"] == "major" and f["field"] == "layout/fits"])

    def test_an_unknown_key_or_a_bad_layout_blocks_in_both_languages(self):
        for section in ({"document": PV.doc(), "extra": 1}, {"document": PV.doc(), "layout": {"site": {}}}):
            res = STAGES[2].run(ctx_with(section))
            self.assertEqual(res.status, "blocked")


class PvFillTests(unittest.TestCase):
    """The structure is given and the harness fills it: the plant size is a result, the equipment is proposed, the gaps are stated."""

    def _section(self, **layout_extra):
        document = PV.doc()
        template = dict(document["arrays"][0], inverter="auto", dc_ac_ratio=1.2, n_modules=1)
        for k in ("tilt_deg", "azimuth_deg"):
            template.pop(k, None)
        document["arrays"] = [template]
        return {"document": document, "layout": dict(copy.deepcopy(LAYOUT), fill=True, front_clearance_m=0.5, **layout_extra)}

    def test_the_site_is_filled_and_the_inverter_is_picked_and_said(self):
        res = STAGES[2].run(ctx_with(self._section()))
        self.assertEqual(res.status, "ok")
        pv = res.outputs["pv"]
        self.assertTrue(pv["layout"]["fits"])
        n_series = pv["arrays"][0]["strings"]["n_series"]
        self.assertEqual(pv["counts"]["modules"], pv["site_fill"]["capacity_modules"] // n_series * n_series)      # whole strings that fit
        fields = {f["field"] for f in res.findings}
        self.assertTrue({"layout/filled", "warning/inverter_auto"} <= fields)
        self.assertNotIn("fill", pv["layout"])
        tf = pv["technical_feasibility"]
        self.assertTrue(tf["feasible"] and tf["checks"]["structure_holds_the_modules"])
        self.assertEqual(tf["installed"]["modules"], pv["counts"]["modules"])
        self.assertTrue(tf["economic"]["en"] and tf["economic"]["es"])

    def test_the_module_that_installs_the_most_power_wins_even_if_it_is_not_the_biggest(self):
        section = self._section()
        section["document"]["arrays"][0]["module"] = dict(section["document"]["arrays"][0]["module"], auto=True)
        res = STAGES[2].run(ctx_with(section))
        self.assertEqual(res.status, "ok")
        note = [f for f in res.findings if f["field"] == "warning/module_auto"]
        self.assertEqual(len(note), 1)
        pv = res.outputs["pv"]
        import epc_pv.modulepick as mp
        pmax = pv["arrays"][0]["dc_kwp"] * 1000.0 / pv["arrays"][0]["modules"]
        self.assertIn(pmax, {float(r["module"]["pmax_w"]) for r in mp.modules()})
        self.assertIn(f"{pv['arrays'][0]['modules']} x", note[0]["value"]["en"] + f"{pv['arrays'][0]['modules']} x") 
        self.assertNotIn("auto", pv["layout"])
        self.assertGreaterEqual(pv["totals"]["dc_kwp"], 1)

    def test_the_saving_is_the_yearly_energy_times_the_client_price(self):
        section = self._section()
        section["economics"] = {"energy_price": 0.1, "currency": "USD", "investment": 20000}
        eco = STAGES[2].run(ctx_with(section)).outputs["pv"]["technical_feasibility"]["economic"]
        kwh = STAGES[2].run(ctx_with(self._section())).outputs["pv"]["totals"]["ac_kwh"]
        self.assertAlmostEqual(eco["saving_year"], kwh * 0.1, delta=0.01)
        self.assertAlmostEqual(eco["simple_payback_years"], 20000 / (kwh * 0.1), delta=0.01)
        self.assertEqual(len(eco["saving_month"]), 12)
        free = STAGES[2].run(ctx_with(self._section())).outputs["pv"]["technical_feasibility"]["economic"]
        self.assertTrue(free["en"] and free["es"])      # no price: it says what to give, nothing is assumed

    def test_a_cap_stops_the_fill_and_a_data_sheet_gap_is_assumed_never_silent(self):
        section = self._section(target_modules=56)
        section["document"]["arrays"][0]["inverter"] = dict(section["document"]["arrays"][0]["inverter"] if isinstance(section["document"]["arrays"][0]["inverter"], dict) else PV.INVERTER, isc_max_input_a=None, model="X")
        section["document"]["arrays"][0]["inverter"]["i_max_input_a"] = 33
        res = STAGES[2].run(ctx_with(section))
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.outputs["pv"]["counts"]["modules"], 56)
        self.assertIn("warning/isc_not_checked", {f["field"] for f in res.findings})      # the gap is said, and nothing is made up

    def test_a_site_smaller_than_the_default_table_gets_a_smaller_table_and_says_so(self):
        section = self._section()
        section["layout"]["site"].update(width_m=40, length_m=30)
        res = STAGES[2].run(ctx_with(section))
        self.assertEqual(res.status, "ok")
        self.assertIn("warning/table_shrunk", {f["field"] for f in res.findings})
        self.assertGreater(res.outputs["pv"]["counts"]["modules"], 0)

    def test_a_site_too_small_for_one_table_is_refused_in_both_languages(self):
        section = self._section()
        section["layout"]["site"].update(width_m=3, length_m=3)
        res = STAGES[2].run(ctx_with(section))
        self.assertEqual(res.status, "blocked")


class PvWeatherFileTests(unittest.TestCase):
    """`weather_file`: the PVGIS file of the project replaces the weather of the document; no network."""

    def _ctx(self, tmp, name, content=None, section_extra=None):
        import test_weather as TW
        from epc_pv import weather
        if content is None:
            content = weather.parse_tmy(TW.payload(), -3, retrieved="2026-11-19")
        if content is not False:
            (Path(tmp) / "weather").mkdir(exist_ok=True)
            (Path(tmp) / "weather" / "weather_pvgis.json").write_text(json.dumps(content), encoding="utf-8")
        document = PV.doc()
        del document["weather"]
        ctx = ctx_with()
        ctx.inputs_dir = tmp
        ctx.engine_inputs = dict(ctx.engine_inputs, pv={"document": document, "weather_file": name, **(section_extra or {})})
        return ctx

    def test_the_file_gives_the_weather_and_a_source_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = STAGES[2].run(self._ctx(tmp, "weather/weather_pvgis.json"))
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.outputs["pv"]["counts"]["hours"], 8760)
        sources = [f for f in res.findings if f["field"] == "weather/source"]
        self.assertEqual(len(sources), 1)
        self.assertIn("pending review", sources[0]["value"])

    def test_a_file_outside_the_inputs_or_missing_or_wrong_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, content in (("../x.json", None), ("weather/none.json", None), ("weather/weather_pvgis.json", {"nope": 1})):
                res = STAGES[2].run(self._ctx(tmp, name, content))
                self.assertEqual(res.status, "blocked", name)


class PvOrientationAndRoofTests(unittest.TestCase):
    """The harness chooses tilt and azimuth when they are missing, and places the modules on the roof planes."""

    def test_arrays_without_tilt_and_azimuth_get_the_engine_choice_and_a_finding(self):
        document = PV.doc()
        for key in ("tilt_deg", "azimuth_deg"):
            del document["arrays"][0][key]
        res = STAGES[2].run(ctx_with({"document": document}))
        self.assertEqual(res.status, "ok")
        chosen = [f for f in res.findings if f["field"] == "orientation/chosen"]
        self.assertEqual(len(chosen), 1)
        self.assertIn("azimuth 0 deg", chosen[0]["value"])

    def test_given_orientation_is_kept_and_no_finding_is_raised(self):
        res = STAGES[2].run(ctx_with({"document": PV.doc()}))
        self.assertFalse([f for f in res.findings if f["field"] == "orientation/chosen"])

    def test_a_roof_gives_the_arrays_the_placement_and_the_orientation(self):
        document = PV.doc()
        template = {k: document["arrays"][0][k] for k in ("module", "inverter", "dc_ac_ratio")}
        document["arrays"] = []
        roof = {"planes": [{"id": "R1", "width_m": 12.0, "slope_m": 6.0, "setback_m": 0.5}], "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02, "array": template, "target_modules": 10}
        res = STAGES[2].run(ctx_with({"document": document, "roof": roof}))
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.outputs["pv"]["roof"]["counts"]["modules"], 10)
        self.assertEqual(res.outputs["pv"]["counts"]["arrays"], 1)
        self.assertTrue([f for f in res.findings if f["field"] == "orientation/chosen"])
        json.dumps(res.to_dict())
        small = dict(roof, target_modules=500)
        res = STAGES[2].run(ctx_with({"document": document, "roof": small}))
        self.assertIn("roof_short", [f["field"].split("/")[-1] for f in res.findings])

    def test_an_unknown_roof_is_assumed_flat_and_the_harness_proposes_the_structure_and_the_drawings(self):
        document = PV.doc()
        template = {k: document["arrays"][0][k] for k in ("module", "inverter", "dc_ac_ratio")}
        document["arrays"] = []
        flat = {"width_m": 14.0, "length_m": 8.0, "setback_m": 0.6, "walkway_m": 0.8, "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02, "table": {"rows": 1, "modules_per_row": 4, "orientation": "landscape"},
                "table_gap_m": 0.3, "front_clearance_m": 0.3, "station": {"width_m": 1.0, "depth_m": 1.0}, "inverter_pad": {"width_m": 0.7, "depth_m": 0.4}, "array": template, "target_modules": 12}
        res = STAGES[2].run(ctx_with({"document": document, "flat_roof": flat}))
        self.assertEqual(res.status, "ok")
        proposal = res.outputs["pv"]["flat_roof"]
        self.assertEqual(proposal["assumption"], "flat roof, tilted frames facing the equator")
        self.assertGreaterEqual(proposal["capacity_modules"], 12)
        self.assertIn("layout", res.outputs["pv"])
        self.assertEqual(len([f for f in res.findings if f["field"] == "roof/assumed_flat"]), 1)
        self.assertIn("not calculated", [f for f in res.findings if f["field"] == "roof/assumed_flat"][0]["value"])
        json.dumps(res.to_dict())
        self.assertEqual(STAGES[2].run(ctx_with({"document": document, "flat_roof": {"width_m": 1}})).status, "blocked")

    def test_a_small_flat_roof_shrinks_the_frame_and_a_tiny_one_says_the_minimum_size(self):
        document = PV.doc()
        template = {k: document["arrays"][0][k] for k in ("module", "inverter", "dc_ac_ratio")}
        document["arrays"] = []
        flat = {"width_m": 12.0, "length_m": 8.0, "setback_m": 0.6, "walkway_m": 0.8, "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02, "table": {"rows": 1, "modules_per_row": 8, "orientation": "landscape"},
                "table_gap_m": 0.3, "front_clearance_m": 0.3, "station": {"width_m": 1.0, "depth_m": 1.0}, "inverter_pad": {"width_m": 0.7, "depth_m": 0.4}, "array": template}
        res = STAGES[2].run(ctx_with({"document": document, "flat_roof": flat}))
        self.assertEqual(res.status, "ok")
        self.assertIn("table_shrunk", [f["field"].split("/")[-1] for f in res.findings])
        res = STAGES[2].run(ctx_with({"document": document, "flat_roof": dict(flat, width_m=1.5, length_m=2.0)}))
        self.assertEqual(res.status, "blocked")
        self.assertIn("at least", str(res.to_dict()))

    def _roof_template(self):
        document = PV.doc()
        template = {k: document["arrays"][0][k] for k in ("module", "inverter", "dc_ac_ratio")}
        document["arrays"] = []
        return document, {"module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02, "array": template, "target_modules": 12}

    def test_the_planes_of_a_roof_dxf_become_one_array_each_and_wind_is_said_pending(self):
        import test_roofdxf as TD
        content = TD.dxf([TD.rect("PV-CUBIERTA", 0, 0, 10, 5), TD.text("PV-CUBIERTA-DATOS", 1, 1, "tilt=25 az=0"), TD.rect("PV-CUBIERTA", 12, 0, 20, 5), TD.text("PV-CUBIERTA-DATOS", 13, 1, "tilt=20 az=90")])
        document, roof = self._roof_template()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "plans").mkdir()
            (Path(tmp) / "plans" / "roof.dxf").write_text(content, encoding="utf-8")
            ctx = ctx_with()
            ctx.inputs_dir = tmp
            ctx.engine_inputs = dict(ctx.engine_inputs, pv={"document": document, "roof": roof, "roof_dxf": {"file": "plans/roof.dxf", "setback_m": 0.5}})
            res = STAGES[2].run(ctx)
            self.assertEqual(res.status, "ok")
            self.assertEqual(res.outputs["pv"]["counts"]["arrays"], 2)
            self.assertIn("roof_wind_pending", [f["field"].split("/")[-1] for f in res.findings])
            ctx.engine_inputs["pv"]["roof_dxf"] = {"file": "../x.dxf", "setback_m": 0.5}
            self.assertEqual(STAGES[2].run(ctx).status, "blocked")
            ctx.engine_inputs["pv"]["roof_dxf"] = {"file": "plans/roof.dxf"}
            self.assertEqual(STAGES[2].run(ctx).status, "blocked")

    def test_a_wrong_roof_blocks(self):
        res = STAGES[2].run(ctx_with({"document": PV.doc(), "roof": {"planes": []}}))
        self.assertEqual(res.status, "blocked")


class PvDrawingsTests(unittest.TestCase):
    def test_a_ground_run_raises_the_3d_model_from_the_layout(self):
        document = PV.doc()
        inputs = W.inputs_doc()
        inputs["pv"] = {"document": document, "layout": dict(copy.deepcopy(LAYOUT), front_clearance_m=0.5)}
        with tempfile.TemporaryDirectory() as tmp:
            ctx = W.context(engine_inputs=inputs, work_dir=tmp)
            run(ctx, stop_after=10, run_id="r1")
            res = ctx.results[10]
            self.assertEqual(res.status, "ok")
            self.assertTrue(res.outputs["pv_model_3d"].endswith("_pv_model_3d.dxf"))
            self.assertTrue(any(k.endswith("_pv_equipment_detail_sheet") for k in res.outputs["pv_sheets"]))      # the module format of the fixture has a record, so its detail sheet is drawn
            self.assertTrue(any(str(f.get("path", f.get("name", ""))).endswith("_pv_model_3d.dxf") for f in res.outputs["files"]))

    def test_the_four_drafts_are_written_from_the_engine_geometry(self):
        import epc_pv
        from epc_drawing import pv_diagrams
        document = PV.doc()
        result = epc_pv.run(document, epc_pv.Options()).as_dict()
        geometry = epc_pv.plan_layout(document, result, copy.deepcopy(LAYOUT))
        with tempfile.TemporaryDirectory() as tmp:
            for language in ("en", "es"):
                paths = pv_diagrams.write_all(geometry, result, Path(tmp) / language, "PVT", language=language, stamp_date="2026-11-18")
                self.assertEqual(set(paths), {f"PVT_{k}" for k in ("layout", "stringing", "cabling", "sld")})
                for path in paths.values():
                    self.assertTrue(Path(path).stat().st_size > 0)

    def test_a_roof_run_reaches_stage_10_and_writes_the_three_roof_sheets(self):
        document = PV.doc()
        template = {k: document["arrays"][0][k] for k in ("module", "inverter", "dc_ac_ratio")}
        document["arrays"] = []
        planes = [{"id": "R1", "width_m": 12.0, "slope_m": 6.0, "setback_m": 0.5, "tilt_deg": 25, "azimuth_deg": 0}, {"id": "R2", "width_m": 8.0, "slope_m": 5.0, "setback_m": 0.5, "tilt_deg": 20, "azimuth_deg": 90}]
        roof = {"planes": planes, "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02, "array": template, "target_modules": 28}
        inputs = W.inputs_doc()
        inputs["pv"] = {"document": document, "roof": roof}
        with tempfile.TemporaryDirectory() as tmp:
            ctx = W.context(engine_inputs=inputs, work_dir=tmp)
            run(ctx, stop_after=10, run_id="r1")
            res = ctx.results[10]
        self.assertEqual(res.status, "ok")
        self.assertEqual({k.rsplit("_pv_", 1)[1] for k in res.outputs["pv_sheets"]}, {"roof_layout_sheet", "roof_stringing_sheet", "roof_cabling_sheet"})



    def test_the_layout_names_the_equipment_records_and_the_3d_model_takes_their_detail(self):
        from disciplines.electrical_lv.stages import pv_drawings
        document = PV.doc()
        inputs = W.inputs_doc()
        inputs["pv"] = {"document": document, "layout": dict(copy.deepcopy(LAYOUT), front_clearance_m=0.5)}
        with tempfile.TemporaryDirectory() as tmp:
            ctx = W.context(engine_inputs=inputs, work_dir=tmp)
            run(ctx, stop_after=10, run_id="r1")
            geometry = ctx.results[3].outputs["pv"]["layout"]
            ids = geometry["equipment"]
            self.assertEqual(set(ids), {"module_format", "inverter_records"})
            self.assertEqual(set(ids["inverter_records"]), {a["id"] for a in document["arrays"]})
            parts = pv_drawings.equipment_parts(geometry)
            self.assertEqual(set(parts["inverters"]), {i["id"] for i in geometry["inverters"]})
            self.assertEqual(pv_drawings.equipment_parts({}), {})
            self.assertEqual(parts["module"]["id"], ids["module_format"])                    # the fixture module has a format record with its outline
            known = dict(geometry, equipment={"module_format": None, "inverter_records": {"A1": "sma.stp25000tl-30"}})
            parts = pv_drawings.equipment_parts(known)
            self.assertIsNone(parts["module"])
            self.assertEqual(parts["inverters"]["INV-01"]["id"], "sma.stp25000tl-30")


class PvInverterCountTests(unittest.TestCase):
    """An `auto` inverter count raised for the MPPT input current is said with the count really installed (the `inverter_auto` note states the one of the ratio alone)."""

    def test_the_raised_count_is_stated_with_the_real_ratio_in_both_languages(self):
        from disciplines.electrical_lv.stages import pv_stage
        inverter = {"auto": True, "n_mppt": 6, "pac0_w": 100000.0}
        section = {"document": {"arrays": [{"id": "A1", "inverter": inverter, "n_modules": 100}]}}
        first = {"arrays": [{"inverters": 90, "dc_kwp": 10800.0, "strings": {"strings": 672, "strings_per_mppt": 2, "strings_per_mppt_limit": 1}}], "warnings": []}
        ran = {"arrays": [], "warnings": []}
        real, pv_stage._run = pv_stage._run, lambda sec: ran
        self.addCleanup(setattr, pv_stage, "_run", real)
        _, out = pv_stage._add_inverters_for_current(section, first)
        raised = [w for w in out["warnings"] if w["code"] == "inverters_raised"]
        self.assertEqual(len(raised), 1)
        self.assertIn("112", raised[0]["en"])
        self.assertIn("0.96", raised[0]["en"])
        self.assertTrue(raised[0]["es"] and "112" in raised[0]["es"])

    def test_a_count_that_respects_the_current_is_left_alone(self):
        from disciplines.electrical_lv.stages import pv_stage
        section = {"document": {"arrays": [{"id": "A1", "inverter": {"auto": True, "n_mppt": 6, "pac0_w": 1.0}, "n_modules": 1}]}}
        result = {"arrays": [{"inverters": 1, "dc_kwp": 1.0, "strings": {"strings": 6, "strings_per_mppt": 1, "strings_per_mppt_limit": 1}}], "warnings": []}
        self.assertIs(pv_stage._add_inverters_for_current(section, result)[1], result)


class PvModel3dSizeTests(unittest.TestCase):
    """Big plants are written as parts and a master (a 307 440 module plant ran the single model out of memory); small ones stay one file."""

    def test_the_way_depends_on_the_module_count(self):
        from disciplines.electrical_lv.stages import pv_drawings as D
        self.assertEqual(D.model3d_plan(1000), ("single", None))
        self.assertEqual(D.model3d_plan(D.MODEL3D_SINGLE_MAX_MODULES)[0], "single")
        self.assertEqual(D.model3d_plan(D.MODEL3D_SINGLE_MAX_MODULES + 1)[0], "assembly")
        self.assertTrue(D.MODEL3D_PARTS["en"] and D.MODEL3D_PARTS["es"])


if __name__ == "__main__":
    unittest.main()
