"""A vector PDF can be shown as the page itself: the page is tied to the plan space by the texts that both have, once each."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_arch.backdrop import _opening_layer, _solid_wall, _stroke_kind, _text_kind, _marks_on_page, _to_page, fit    # noqa: E402
from epc_arch.model import Architecture, Line, Marks, Opening, Primitives, Text, Wall    # noqa: E402

K, TX, TY = 2.5, -40.0, 900.0


def _page(values):
    return [Text(v, (100.0 + 70 * i, 50.0 + 33 * i * (-1) ** i)) for i, v in enumerate(values)]


def _plan(page):
    return [Text(t.value, (K * t.at[0] + TX, TY - K * t.at[1])) for t in page]


class TestBackdrop(unittest.TestCase):
    def test_the_page_is_tied_to_the_plan_by_the_texts_written_once(self):
        page = _page(["20,30", "A", "B", "C", "ESC. 1:100", "8,00"])
        tie = fit(page, _plan(page), 3000.0)
        self.assertIsNotNone(tie)
        k, tx, ty = tie
        self.assertAlmostEqual(k, K, places=6)
        self.assertAlmostEqual(tx, TX, places=4)
        self.assertAlmostEqual(ty, TY, places=4)

    def test_a_text_written_more_than_once_is_not_used(self):
        page = _page(["M-01", "M-01", "M-01", "A", "B", "C"])
        self.assertIsNone(fit(page, _plan(page), 3000.0))                  # only three are unique: not enough to tie

    def test_texts_that_do_not_agree_give_no_tie(self):
        page = _page(["a1", "b2", "c3", "d4", "e5"])
        plan = _plan(page)
        plan[2] = Text("c3", (plan[2].at[0] + 400.0, plan[2].at[1] - 300.0))
        self.assertIsNone(fit(page, plan, 3000.0))

    def _arch(self):
        arch = Architecture(source="pdf", size=(1000.0, 600.0), units_per_metre=50.0, scale_hint=None, wall_thickness=10.0,
                            walls=[Wall("w1", (100.0, 300.0), (900.0, 300.0), 10.0, 1.0, "")],
                            openings=[Opening("o1", "door", (500.0, 300.0), 40.0, 0.0, "w1", 0.9, "arc")])
        arch.annotations = {"axes": Marks(lines=[Line((100.0, 50.0), (100.0, 550.0))]), "labels": Marks(texts=[Text("P-01", (300.0, 200.0), 8.0)])}
        return arch

    def test_a_stroke_of_an_axis_is_an_axis_and_a_stroke_of_the_building_is_not(self):
        arch = self._arch()
        marks = _marks_on_page(arch, _to_page((1.0, 0.0, 600.0)))                # the page is the plan turned over: y up
        axis = Primitives(source="pdf")
        axis.lines = [Line((100.0, 550.0), (100.0, 50.0))]
        other = Primitives(source="pdf")
        other.lines = [Line((300.0, 300.0), (400.0, 300.0))]
        self.assertEqual(_stroke_kind(axis, marks), "ARQ-EJES")
        self.assertIsNone(_stroke_kind(other, marks))
        self.assertEqual(_text_kind((299.0, 395.0, 330.0, 405.0), marks), "ARQ-ETIQUETAS")        # a text object that holds the start of a label
        self.assertIsNone(_text_kind((10.0, 10.0, 20.0, 20.0), marks))

    def test_what_is_small_and_near_a_door_is_the_door_and_a_thick_piece_on_a_wall_is_the_wall(self):
        arch = self._arch()
        self.assertEqual(_opening_layer(arch, (510.0, 320.0), 30.0), "ARQ-PUERTAS")
        self.assertIsNone(_opening_layer(arch, (510.0, 320.0), 300.0))             # too big to be a part of the door
        tie = (1.0, 0.0, 600.0)
        self.assertTrue(_solid_wall(arch, (200.0, 295.0, 260.0, 305.0), tie))        # as thick as the wall (10) and on it
        self.assertFalse(_solid_wall(arch, (200.0, 299.8, 260.0, 300.2), tie))       # a thin stroke along it (an axis, a dimension)

    def test_without_the_option_the_pdf_is_drawn_by_the_engine(self):
        import helpers
        from epc_arch import Options, recognize
        res = recognize(helpers.room_pdf(), "flat.pdf", Options())
        self.assertNotIn("ARQ-ORIGINAL", res.svg)


if __name__ == "__main__":
    unittest.main()
