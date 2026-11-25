"""Doors are put where they are: a corridor that cuts a line of wall is not an opening, and a door drawn with its open leaf is in the wall that its shut leaf lies along."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_draw.arch.model import Arc, Wall                               # noqa: E402
from epc_draw.arch.pipeline import Context, Hints, scale_for           # noqa: E402
from epc_draw.arch.recognizers.openings import _is_a_passage, _wall_and_closed_end, find_gaps   # noqa: E402

SIZE = (3000.0, 2000.0)
T = 40.0
CTX = Context(size=SIZE, scale=scale_for(SIZE, None), hints=Hints())


def _w(i, a, b):
    return Wall(i, a, b, T, 0.9, "pair")


class TestPassagesAndDoors(unittest.TestCase):
    def test_a_corridor_between_two_walls_that_cut_a_line_is_not_an_opening(self):
        north, south = _w("n", (0.0, 400.0), (2000.0, 400.0)), _w("s", (0.0, 800.0), (2000.0, 800.0))
        up, down = _w("u", (1000.0, 0.0), (1000.0, 400.0)), _w("d", (1000.0, 800.0), (1000.0, 1200.0))
        walls = [north, south, up, down]
        self.assertTrue(_is_a_passage((1000.0, 400.0), (1000.0, 800.0), 90.0, walls, T, CTX))
        self.assertEqual([g for g in find_gaps(walls, T, CTX) if abs(g.at[0] - 1000.0) < 5], [])

    def test_a_door_gap_with_free_jambs_is_an_opening(self):
        left, right = _w("l", (0.0, 400.0), (900.0, 400.0)), _w("r", (1000.0, 400.0), (2000.0, 400.0))
        self.assertFalse(_is_a_passage((900.0, 400.0), (1000.0, 400.0), 0.0, [left, right], T, CTX))
        self.assertEqual(len(find_gaps([left, right], T, CTX)), 1)

    def test_the_shut_leaf_is_the_end_opposite_the_drawn_open_leaf(self):
        horizontal, cross = _w("h", (0.0, 400.0), (820.0, 400.0)), _w("v", (900.0, 0.0), (900.0, 800.0))
        arc = Arc((880.0, 400.0), 60.0, 90.0, 180.0)                                            # from the end down (880,460) round to the end along the wall (820,400)
        open_leaf = (880.0, 460.0)
        wall, shut = _wall_and_closed_end(arc, open_leaf, [horizontal, cross], T)
        self.assertEqual(wall.id, "h")
        self.assertAlmostEqual(shut[0], 820.0, delta=1.0)


if __name__ == "__main__":
    unittest.main()
