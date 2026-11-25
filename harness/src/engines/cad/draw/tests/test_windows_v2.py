"""A window inside a continuous wall: thin lines between the faces over the span of a window, in a wall that faces outside."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_draw.arch.model import Line, Wall                              # noqa: E402
from epc_draw.arch.pipeline import Context, Hints, scale_for           # noqa: E402
from epc_draw.arch.recognizers.windows_v2 import windows_in_walls       # noqa: E402

SIZE = (3000.0, 2000.0)
WALL = Wall("w1", (0.0, 0.0), (1000.0, 0.0), 40.0, 0.9, "pair")


def _ctx() -> Context:
    return Context(size=SIZE, scale=scale_for(SIZE, None), hints=Hints())


def _line(y: float, x0: float = 300.0, x1: float = 600.0, width: float = 1.0) -> Line:
    return Line((x0, y), (x1, y), width)


class TestWindowsInWalls(unittest.TestCase):
    def find(self, lines, outside=True):
        return windows_in_walls(lines, [WALL], 40.0, _ctx(), lambda at, theta: outside)

    def test_two_panes_between_the_faces_are_a_window(self):
        found = self.find([_line(-5.0), _line(6.0)])
        self.assertEqual(len(found), 1)
        self.assertEqual((round(found[0].at[0]), round(found[0].width)), (450, 300))

    def test_one_pane_is_not_enough(self):
        self.assertEqual(self.find([_line(-5.0)]), [])

    def test_lines_on_the_faces_are_the_wall_not_panes(self):
        self.assertEqual(self.find([_line(-20.0), _line(20.0)]), [])

    def test_a_wall_that_faces_inside_has_no_window_in_it(self):
        self.assertEqual(self.find([_line(-5.0), _line(6.0)], outside=False), [])

    def test_a_thick_stroke_on_the_axis_is_a_wall_drawn_as_a_band(self):
        self.assertEqual(self.find([_line(0.0, width=40.0), _line(4.0, width=40.0)]), [])

    def test_lines_along_the_whole_wall_are_hatching_not_a_window(self):
        self.assertEqual(self.find([_line(-5.0, 0.0, 1000.0), _line(6.0, 0.0, 1000.0)]), [])

    def test_a_gap_counts_as_shut_for_the_outside_test(self):
        from epc_draw.arch.recognizers.openings import Gap, _faces_outside
        wall = Wall("w2", (0.0, 0.0), (1000.0, 0.0), 40.0, 0.9, "pair")
        gate = Gap((500.0, 900.0), 400.0, 0.0, 900.0, 300.0, 700.0, "")                # an opening in a far wall, straight across from the window
        far = Wall("w3", (0.0, 900.0), (300.0, 900.0), 40.0, 0.9, "pair")
        far2 = Wall("w4", (700.0, 900.0), (1000.0, 900.0), 40.0, 0.9, "pair")
        back = Wall("w5", (0.0, -900.0), (1000.0, -900.0), 40.0, 0.9, "pair")
        self.assertTrue(_faces_outside([wall, far, far2, back], [], 40.0)((500.0, 0.0), 0.0))
        self.assertFalse(_faces_outside([wall, far, far2, back], [gate], 40.0)((500.0, 0.0), 0.0))


if __name__ == "__main__":
    unittest.main()
