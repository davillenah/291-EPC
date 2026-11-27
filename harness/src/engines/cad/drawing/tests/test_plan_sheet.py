"""A plan on the IRAM sheet: the plan is placed inside the free zone of the sheet at a standard scale, the sheet keeps its frame and title block, and a plan that does not fit takes a smaller scale."""
import tempfile
import unittest
from pathlib import Path

import ezdxf

from epc_drawing.export import plan_sheet

REQUEST = {"common": {"proyecto": "Demo", "empresa": "Oficina SA"}, "logos": {}}


def _plan(path: Path, width_m: float, height_m: float) -> None:
    doc = ezdxf.new("R2010")
    doc.units = 6                                                                      # metres
    doc.layers.add("PLAN-ILU")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (width_m, 0), (width_m, height_m), (0, height_m)], close=True, dxfattribs={"layer": "PLAN-ILU"})
    msp.add_text("TAG", height=0.3, dxfattribs={"layer": "PLAN-ILU"}).set_placement((1, 1))
    doc.saveas(path)


def _plan_box(dxf: Path):
    from ezdxf import bbox
    msp = ezdxf.readfile(str(dxf)).modelspace()
    mine = [e for e in msp if e.dxf.layer == "PLAN-ILU"]
    box = bbox.extents(mine, fast=True)
    return box.extmin.x, box.extmin.y, box.extmax.x, box.extmax.y


class TestPlanSheet(unittest.TestCase):
    def test_the_free_zone_is_above_the_title_block_with_a_gap(self):
        from epc_titleblock import sheet_generator
        svg = sheet_generator.build("A1", True, {})["svg"]
        area, height = plan_sheet.free_area(svg)
        self.assertEqual(height, 594.0)
        self.assertEqual((area[0], area[1], area[2]), (35.0, 20.0, 821.0))
        self.assertLess(area[3], 506.5)                                                # above the list of modifications, which is above the title block

    def test_the_scale_is_the_asked_one_when_it_fits_and_a_smaller_one_when_it_does_not(self):
        area = (35.0, 20.0, 821.0, 500.0)                                              # 786 x 480 mm of paper
        self.assertEqual(plan_sheet.fit_scale((30000.0, 20000.0), area, 100), 100)      # 300 x 200 mm at 1:100
        self.assertEqual(plan_sheet.fit_scale((100000.0, 60000.0), area, 100), 150)     # 1000 x 600 mm at 1:100 does not fit: 1:150 does
        self.assertEqual(plan_sheet.fit_scale((30000.0, 20000.0), area, None), 50)      # nothing asked: the largest drawing that fits

    def test_the_plan_lands_inside_the_free_zone_of_the_sheet_with_its_frame_and_title_block(self):
        with tempfile.TemporaryDirectory() as d:
            plan, out = Path(d) / "plan.dxf", Path(d) / "out.dxf"
            _plan(plan, 30.0, 20.0)
            res = plan_sheet.compose(plan, REQUEST, out, "A1", 100, "PLAN_L1")
            self.assertEqual((res["format"], res["scale"]), ("A1", 100))
            x0, y0, x1, y1 = _plan_box(out)
            self.assertAlmostEqual(x1 - x0, 300.0, delta=1.0)                           # 30 m at 1:100 are 300 mm of paper
            self.assertAlmostEqual(y1 - y0, 200.0, delta=1.0)
            self.assertTrue(35.0 <= x0 and x1 <= 821.0 and 594.0 - 506.5 <= y0, (x0, y0, x1, y1))     # inside the free zone (y up in the DXF)
            sheet_layers = {e.dxf.layer for e in ezdxf.readfile(str(out)).modelspace() if e.dxf.layer != "PLAN-ILU"}
            self.assertTrue(sheet_layers)                                                 # the frame and the title block are there too

    def test_a_layer_keeps_its_transparency_on_the_sheet(self):
        with tempfile.TemporaryDirectory() as d:
            plan, out = Path(d) / "plan.dxf", Path(d) / "out.dxf"
            _plan(plan, 30.0, 20.0)
            doc = ezdxf.readfile(str(plan))
            doc.layers.get("PLAN-ILU").transparency = 0.8
            doc.saveas(plan)
            plan_sheet.compose(plan, REQUEST, out, "A1", 100, "PLAN_L1")
            self.assertAlmostEqual(ezdxf.readfile(str(out)).layers.get("PLAN-ILU").transparency, 0.8, delta=0.02)

    def test_a_plan_too_big_for_the_scale_asked_takes_a_smaller_one_and_a_bad_format_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            plan, out = Path(d) / "plan.dxf", Path(d) / "out.dxf"
            _plan(plan, 120.0, 70.0)
            self.assertGreater(plan_sheet.compose(plan, REQUEST, out, "A3", 50)["scale"], 50)
            with self.assertRaises(ValueError):
                plan_sheet.compose(plan, REQUEST, out, "A9", 50)


if __name__ == "__main__":
    unittest.main()
