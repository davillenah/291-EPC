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

    def test_a_wrong_roof_blocks(self):
        res = STAGES[2].run(ctx_with({"document": PV.doc(), "roof": {"planes": []}}))
        self.assertEqual(res.status, "blocked")


class PvDrawingsTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
