"""Stage 10 writes the 3D model, the detail sections and the take-off of a building run when the engineer gives `engine_inputs["model3d"]` (nothing is assumed: without it nothing is written)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_building_intake as B  # noqa: E402
import test_pipeline_wiring as W  # noqa: E402
from disciplines.electrical_lv.intake.building import derive_all  # noqa: E402
from disciplines.electrical_lv.pipeline import run  # noqa: E402
from disciplines.electrical_lv.stages import model3d  # noqa: E402

HEIGHTS = {"wall_height_m": 2.8, "door_head_m": 2.05, "window_sill_m": 0.9, "window_head_m": 2.1, "slab_m": 0.2, "elevation_m": 0.0}
FLOOR = {"name": "PLANTA BAJA", "index": 0, "wall_thickness_m": 0.2,
         "rooms": [{"code": "PB-01", "name": "OFICINA", "box_m": [0, 0, 6, 5]}, {"code": "PB-02", "name": "HALL", "box_m": [6, 0, 10, 5]}],
         "doors": [{"room": "PB-02", "side": "S", "width_m": 1.0}, {"room": "PB-01", "side": "E", "width_m": 0.9}],
         "windows": [{"room": "PB-01", "side": "N", "width_m": 2.0}]}


def architecture():
    from epc_arch.author import architecture_of
    return architecture_of(FLOOR).as_dict()


def building():
    data = dict(B.DATA, receptacles=dict(B.PLUGS))
    floor = {"id": "PB", "name": "Ground floor", "phases": 1, "length": {"value": 20, "unit": "m"}, "architecture": architecture(), "by_name": {"OFICINA": dict(data), "HALL": dict(data)},
             "receptacles_load": {"phases": 1, "length": {"value": 25, "unit": "m"}}, "board": {"room": "HALL"}}
    return {"luminaires": [dict(B.LUM)], "receptacles": [dict(B.TUG)], "floors": [floor]}


def stage10(**extra):
    done = derive_all(building(), B.loads())
    ins = dict(W.inputs_doc(), lighting=done["lighting"], routing=done["routing"], **extra)
    ins["circuits"] = dict(ins["circuits"], **done["circuits"])
    with tempfile.TemporaryDirectory() as tmp:
        res = run(W.context(engine_inputs=ins, loads=done["loads"], work_dir=tmp), stop_after=10, run_id="r10").results[9]
        files = sorted(f["path"] for f in res.outputs.get("files", []))
        texts = {}
        for f in files:
            if "_section_" in f:
                import ezdxf
                texts[f] = [e.dxf.text for e in ezdxf.readfile(str(Path(tmp) / res.outputs["directory"] / f)).modelspace() if e.dxftype() == "TEXT"]
        return res, files, texts, done["routing"]


MODEL = {"floors": {"PB": HEIGHTS}, "supports": {"spacing_m": 1.5}, "sections": [{"name": "A", "axis": "x", "at_m": 3.0, "look": "+", "depth_m": 2.0}]}


class Model3dInTheRun(unittest.TestCase):
    def test_without_the_section_nothing_is_written(self):
        res, files, _, _ = stage10()
        self.assertEqual(res.status, "ok", res.message)
        self.assertNotIn("model3d", res.outputs)
        self.assertFalse([f for f in files if "model_3d" in f or "_section_" in f])

    def test_the_model_the_section_and_the_takeoff_come_out_of_the_run(self):
        res, files, texts, _ = stage10(model3d=MODEL)
        self.assertEqual(res.status, "ok", res.message)
        self.assertEqual(len([f for f in files if f.endswith("_model_3d.dxf")]), 1, files)
        self.assertEqual(len([f for f in files if f.endswith("_section_A.dxf")]), 1, files)
        out = res.outputs["model3d"]
        self.assertGreater(out["faces"], 0)
        self.assertTrue(out["takeoff"]["straights"] and out["takeoff"]["supports"])
        self.assertEqual(sorted(out["sections"]), ["A"])
        self.assertGreater(out["sections"]["A"]["outlines"], 0)
        calls = [c["function"] for c in res.engine_calls]
        self.assertTrue({"epc_arch.model3d.building_solids", "epc_plan.detail.parts", "epc_plan.scene3d.write_dxf"} <= set(calls))

    def test_the_section_names_what_it_cuts_with_its_level(self):
        res, _, texts, _ = stage10(model3d=MODEL)
        tags = next(iter(texts.values()))
        self.assertTrue(tags, "the plane cuts no service")
        self.assertTrue(all("(BOT " in t for t in tags), tags)

    def test_the_elevations_come_out_on_their_sheet(self):
        res, files, _, _ = stage10(model3d=dict(MODEL, elevations=[{"floor": "PB", "side": "S"}, {"floor": "PB", "side": "E"}]))
        self.assertEqual(res.status, "ok", res.message)
        self.assertEqual(sorted(res.outputs["model3d"]["elevations"]), ["PB_E", "PB_S"])
        self.assertEqual(len([f for f in files if "_elevation_PB_" in f]), 2, files)
        self.assertIn("epc_arch.sections.elevation", [c["function"] for c in res.engine_calls])

    def test_a_wrong_elevation_blocks(self):
        for bad in ([{"floor": "P9", "side": "S"}], [{"floor": "PB", "side": "X"}], [{"floor": "PB"}], [{"floor": "PB", "side": "S"}] * 2, "S"):
            res, _, _, _ = stage10(model3d=dict(MODEL, elevations=bad))
            self.assertEqual(res.status, "blocked", bad)

    def test_no_supports_without_a_spacing(self):
        res, _, _, _ = stage10(model3d={"floors": {"PB": HEIGHTS}})
        self.assertEqual(res.status, "ok", res.message)
        self.assertEqual(res.outputs["model3d"]["takeoff"]["supports"], [])

    def test_the_heights_of_every_routed_floor_are_required(self):
        for bad in ({"floors": {}}, {"floors": {"PB": {k: v for k, v in HEIGHTS.items() if k != "slab_m"}}}, {"floors": {"PB": HEIGHTS, "P9": HEIGHTS}}, {"floors": {"PB": HEIGHTS}, "supports": {}},
                    {"floors": {"PB": HEIGHTS}, "sections": [{"name": "A", "axis": "x"}]}, {"floors": {"PB": HEIGHTS}, "other": 1}):
            res, _, _, _ = stage10(model3d=bad)
            self.assertEqual(res.status, "blocked", bad)

    def test_a_plane_that_cannot_be_blocks(self):
        res, _, _, _ = stage10(model3d=dict(MODEL, sections=[{"name": "A", "axis": "z", "at_m": 1.0, "look": "+"}]))
        self.assertEqual(res.status, "blocked")


class Errors(unittest.TestCase):
    def test_the_section_is_checked_against_the_routed_floors(self):
        self.assertEqual(model3d.errors_of(MODEL, {"PB": {}}), [])
        self.assertTrue(any("P1" in e for e in model3d.errors_of(MODEL, {"PB": {}, "P1": {}})))
        self.assertTrue(any("twice" in e for e in model3d.errors_of(dict(MODEL, sections=MODEL["sections"] * 2), {"PB": {}})))


if __name__ == "__main__":
    unittest.main()


class WholePipeline(unittest.TestCase):
    """The platform run from the first stage to the last, with the building drawn from a description: every stage runs and the transmittal carries the 3D model and the detail section."""

    def test_the_twelve_stages_run_and_the_package_carries_the_3d_files(self):
        import test_platform_api as A
        from epc_platform import api
        done = B.derive_all(building(), B.loads())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api.init_project(root, "API-1", A.ANSWERS, clock=A.CLOCK, actor=A.ORC)
            ins = dict(W.inputs_doc(), building=building(), transformer={"demand_kva": 40, "reserve_pct": 20, "secondary_v": 400}, model3d=MODEL)
            res = api.run_pipeline(root / "API-1", loads=B.loads(), engine_inputs=ins, clock=A.CLOCK, actor=A.ORC)
            self.assertTrue(res["ok"], res)
            self.assertEqual(res["data"]["run"]["summary"]["by_status"], {"ok": 12})
            files = sorted(p.name for p in (root / "API-1" / "deliverables" / "TR-001").glob("*/*"))
            self.assertTrue([f for f in files if f.endswith("_model_3d.dxf")], files)
            self.assertTrue([f for f in files if f.endswith("_section_A.dxf")], files)
            self.assertTrue([f for f in files if f.startswith("SLD_")] and [f for f in files if f.endswith("_tables.xlsx")], files)
            drawings = res["data"]["run"]["results"][9]["outputs"]["model3d"]
            self.assertGreater(drawings["solids"], 0)
        self.assertTrue(done["routing"])
