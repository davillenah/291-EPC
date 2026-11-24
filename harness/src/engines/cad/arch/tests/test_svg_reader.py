"""The SVG reader: strokes become lines, `A` arcs become arcs, fills are not read, the written scale gives metres, and a plan exported by the v2 drawing reads back as the same plan."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from epc_arch import Options, recognize                          # noqa: E402
from epc_arch.drawing import build_drawing                        # noqa: E402
from epc_arch.export.export_raster import to_pdf                  # noqa: E402
from epc_arch.export.export_svg import to_svg                     # noqa: E402
from epc_arch.model import Options as Opts                         # noqa: E402
from epc_arch.sources import detect_kind, read                    # noqa: E402
import helpers                                                    # noqa: E402

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" viewBox="0 0 297 210"><title>Planta 1:100</title>'
       '<g transform="translate(10 20)"><line x1="0" y1="0" x2="50" y2="0" stroke="#000" stroke-width="0.5"/>'
       '<rect x="0" y="0" width="10" height="10" fill="#eee" stroke="none"/>'
       '<path d="M0 0 A10 10 0 0 1 10 10" fill="none" stroke="#000" stroke-width="0.2"/></g></svg>')


class TestSvgReader(unittest.TestCase):
    def test_a_stroke_is_a_line_and_a_fill_is_not_read(self):
        p = read(SVG.encode(), "x.svg", Opts())
        self.assertEqual(len(p.lines), 1)
        self.assertEqual((p.lines[0].a, p.lines[0].b), ((10.0, 20.0), (60.0, 20.0)))

    def test_an_arc_command_is_an_arc_in_the_group_frame(self):
        a = read(SVG.encode(), "x.svg", Opts()).arcs[0]
        self.assertAlmostEqual(a.r, 10.0)
        self.assertEqual((round(a.c[0]), round(a.c[1])), (10, 30))
        self.assertEqual((round(a.start), round(a.end)), (270, 0))

    def test_the_written_scale_and_the_paper_size_give_the_units(self):
        p = read(SVG.encode(), "x.svg", Opts())
        self.assertEqual(p.scale, 100)
        self.assertAlmostEqual(p.units_per_metre, 10.0)               # 1 unit = 1 mm of paper = 0.1 m of the building

    def test_a_dark_solid_fill_is_a_shape_and_an_outlined_fill_gives_its_edges_once(self):
        solid = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="0" y="0" width="50" height="10" fill="#555" stroke="none"/></svg>'
        self.assertEqual(len(read(solid.encode(), "x.svg", Opts()).lines), 4)
        both = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="0" y="0" width="50" height="10" fill="#555" stroke="none"/><rect x="0" y="0" width="50" height="10" fill="none" stroke="#000" stroke-width="1"/></svg>'
        self.assertEqual(len(read(both.encode(), "x.svg", Opts()).lines), 4)

    def test_the_paper_and_the_tints_are_not_shapes(self):
        paper = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#ffffff"/><rect width="50" height="10" fill="url(#p)"/><rect width="5" height="5" fill="none"/></svg>'
        self.assertEqual(read(paper.encode(), "x.svg", Opts()).lines, [])

    def test_the_kind_is_svg(self):
        self.assertEqual(detect_kind(SVG.encode(), "x.svg"), "svg")

    def test_a_plan_exported_as_svg_reads_back_the_same(self):
        arch = recognize(helpers.room_dxf(), "flat.dxf", Options()).architecture
        d = build_drawing(arch, sheet="A4")                               # a small room on a big sheet would not be a view of it
        back = recognize(to_svg(d).encode(), "x.svg", Options()).architecture
        self.assertEqual(back.counts(), arch.counts())
        self.assertTrue(back.units_per_metre)

    def test_the_same_plan_as_pdf_reads_in_metres_with_its_walls(self):
        """Known gap (PRD R3): the doors and windows of a small PDF are not all found yet; the walls and the scale are."""
        arch = recognize(helpers.room_dxf(), "flat.dxf", Options()).architecture
        back = recognize(to_pdf(build_drawing(arch, sheet="A4")), "x.pdf", Options()).architecture
        self.assertGreaterEqual(back.counts()["walls"], 5)
        self.assertTrue(back.units_per_metre)

class TestScaleHint(unittest.TestCase):
    def test_a_confident_hint_is_applied_and_a_weak_one_is_not(self):
        from epc_arch.pipeline import _confident
        self.assertTrue(_confident({"units_per_metre": 120.0, "basis": "5 door leaves", "confidence": 0.65}))
        self.assertFalse(_confident({"units_per_metre": 120.0, "basis": "2 door leaves", "confidence": 0.45}))
        self.assertFalse(_confident(None))


class TestStandardDoors(unittest.TestCase):
    def test_the_usual_door_is_within_the_standard_widths(self):
        from epc_arch.config import PARAMS
        m = PARAMS["metres"]
        every = [w for ws in (m["standard_door_widths"]["IRAM_nominal"], m["standard_door_widths"]["UNE_56801_leaf"]) for w in ws]
        self.assertTrue(min(every) <= m["typical_door_leaf"] <= max(every))
        self.assertTrue(m["door_radius"][0] <= m["typical_door_leaf"] <= m["door_radius"][1])


class TestTitleLayers(unittest.TestCase):
    def test_the_layers_named_for_the_title_block_are_not_part_of_the_plan(self):
        from epc_arch.model import Line, Primitives
        from epc_arch.pipeline import _without_title
        prims = Primitives(source="svg", lines=[Line((0.0, 0.0), (1.0, 0.0), 0.0, "A-MUROS-30"), Line((0.0, 0.0), (9.0, 0.0), 0.0, "A-ROTULO"), Line((0.0, 1.0), (9.0, 1.0), 0.0, "0-Titleblock"), Line((0.0, 2.0), (1.0, 2.0), 0.0, "A-VENTANAS")])
        self.assertEqual([l.layer for l in _without_title(prims).lines], ["A-MUROS-30", "A-VENTANAS"])

    def test_a_drawing_with_no_such_layer_is_left_as_it_is(self):
        from epc_arch.model import Line, Primitives
        from epc_arch.pipeline import _without_title
        prims = Primitives(source="dxf", lines=[Line((0.0, 0.0), (1.0, 0.0), 0.0, "0")])
        self.assertIs(_without_title(prims), prims)


class TestExportedSvg(unittest.TestCase):
    """What the programs that export drawings write: strokes by class in a style sheet, and shapes drawn again with `<use>`."""
    def test_strokes_given_by_a_class_are_read(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><style>.cls-1{fill:none;stroke:#000;stroke-width:.5px}.cls-2, .cls-3 { stroke:#333 }</style>'
               '<line class="cls-1" x1="0" y1="0" x2="50" y2="0"/><line class="cls-3" x1="0" y1="5" x2="50" y2="5"/><line x1="0" y1="9" x2="50" y2="9"/></svg>')
        lines = read(svg.encode(), "x.svg", Opts()).lines
        self.assertEqual(len(lines), 2)                                                # the third has no stroke
        self.assertAlmostEqual(lines[0].width, 0.5)

    def test_a_style_attribute_wins_over_the_class(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><style>.a{stroke:#000}</style><line class="a" style="stroke:none" x1="0" y1="0" x2="5" y2="0"/></svg>'
        self.assertEqual(read(svg.encode(), "x.svg", Opts()).lines, [])

    def test_a_use_draws_what_it_points_at_where_it_says(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 100 100"><defs><g id="w"><line x1="0" y1="0" x2="10" y2="0" stroke="#000"/></g>'
               '<symbol id="s"><line x1="0" y1="0" x2="0" y2="10" stroke="#000"/></symbol></defs><use xlink:href="#w" x="20" y="5"/><use href="#s" x="40" y="0"/><use href="#nothing"/></svg>')
        lines = read(svg.encode(), "x.svg", Opts()).lines
        self.assertEqual([(l.a, l.b) for l in lines], [((20.0, 5.0), (30.0, 5.0)), ((40.0, 0.0), (40.0, 10.0))])

    def test_a_use_that_points_at_itself_does_not_loop(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><g id="a"><use href="#a"/><line x1="0" y1="0" x2="1" y2="0" stroke="#000"/></g></svg>'
        self.assertGreaterEqual(len(read(svg.encode(), "x.svg", Opts()).lines), 1)


if __name__ == "__main__":
    unittest.main()
