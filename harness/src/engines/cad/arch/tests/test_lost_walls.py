"""A long wall that the kept reading lost and another reading found whole is brought back."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_arch.model import Wall                                    # noqa: E402
from epc_arch.pipeline import Context, Hints, scale_for           # noqa: E402
from epc_arch.recognizers.lost_walls import lost_walls            # noqa: E402

SIZE = (3000.0, 2000.0)


def _w(i, a, b, t=40.0):
    return Wall(i, a, b, t, 0.9, "pair")


class TestLostWalls(unittest.TestCase):
    ctx = Context(size=SIZE, scale=scale_for(SIZE, None), hints=Hints())
    kept = [_w("v1", (0.0, 0.0), (0.0, 1000.0)), _w("v2", (2000.0, 0.0), (2000.0, 1000.0))]

    def test_a_long_wall_with_nothing_kept_along_it_comes_back(self):
        north = _w("n", (0.0, 0.0), (2000.0, 0.0))
        self.assertEqual(lost_walls([north], self.kept, 40.0, self.ctx), [north])

    def test_a_wall_that_is_kept_does_not_come_back(self):
        self.assertEqual(lost_walls([self.kept[0]], self.kept, 40.0, self.ctx), [])

    def test_a_short_wall_or_one_of_another_thickness_does_not_come_back(self):
        self.assertEqual(lost_walls([_w("s", (500.0, 500.0), (600.0, 500.0))], self.kept, 40.0, self.ctx), [])
        self.assertEqual(lost_walls([_w("t", (500.0, 500.0), (1500.0, 500.0), t=400.0)], self.kept, 40.0, self.ctx), [])


if __name__ == "__main__":
    unittest.main()
