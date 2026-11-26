"""Room labels sit inside their room and touch nothing drawn; round tags that sit on a wall are moved onto a floor."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_draw.arch.drawing import ArcItem, Poly, TextItem, _Map          # noqa: E402
from epc_draw.arch.label_placer import RES, move_round_tags, place_room_labels   # noqa: E402
from epc_draw.arch.model import Room                                       # noqa: E402

M = _Map(1.0, 0.0, 0.0)                                              # plan units are millimetres of paper here


def _room(x0=0.0, y0=0.0, x1=60.0, y1=40.0, name="DORMITORIO") -> Room:
    return Room("r1", (x1 - x0) * (y1 - y0), 17.7, ((x0 + x1) / 2, (y0 + y1) / 2), [(x0, y0, x1, y1)], name, "BEDROOM")


def _bar(x0, y0, x1, y1):
    return Poly(((x0, y0), (x1, y0), (x1, y1), (x0, y1)), "291-A-WALL-FULL-N", closed=True, fill="layer")


def _box_of(t: TextItem):
    h = 1.8
    w = 0.55 * h * len(t.value)
    return t.at[0] - w / 2, t.at[1] - h, t.at[0] + w / 2, t.at[1]


class TestLabelPlacer(unittest.TestCase):
    def test_the_label_is_the_name_over_the_area_in_the_middle_of_a_free_room(self):
        out = place_room_labels([_room()], [], M)
        self.assertEqual([t.value for t in out], ["DORMITORIO", "17,7 m²"])
        self.assertAlmostEqual(sum(t.at[0] for t in out) / 2, 30.0, delta=1.0)

    def test_the_label_moves_off_what_is_drawn_at_its_label_point(self):
        pillar = _bar(25.0, 15.0, 35.0, 25.0)                                      # right where the room's label point is
        out = place_room_labels([_room()], [pillar], M)
        for t in out:
            x0, y0, x1, y1 = _box_of(t)
            self.assertTrue(x1 <= 25.0 or x0 >= 35.0 or y1 <= 15.0 or y0 >= 25.0, t.value)

    def test_the_label_stays_inside_its_room(self):
        for t in place_room_labels([_room()], [], M):
            x0, y0, x1, y1 = _box_of(t)
            self.assertTrue(0.0 <= x0 and x1 <= 60.0 and 0.0 <= y0 and y1 <= 40.0)

    def test_a_room_too_narrow_for_its_name_keeps_the_area_alone(self):
        out = place_room_labels([_room(x1=8.0, y1=40.0, name="ESTACIONAMIENTO")], [], M)
        self.assertEqual([t.value for t in out], ["17,7 m²"])

    def test_a_name_that_the_source_already_wrote_on_a_tag_is_not_repeated(self):
        out = place_room_labels([_room()], [], M, {0})
        self.assertEqual([t.value for t in out], ["17,7 m²"])

    def test_a_round_tag_on_a_wall_is_moved_onto_the_floor(self):
        wall = _bar(28.0, 0.0, 32.0, 40.0)
        circle = ArcItem((30.0, 20.0), 3.0, 0.0, 359.9, "291-A-ANNO")
        text = TextItem("P-01", (30.0, 20.5), "TXT_18", "291-A-ANNO", "middle")
        moved = move_round_tags([wall, circle, text], [_room(x0=0.0, x1=28.0), _room(x0=32.0, x1=60.0)], M)
        c = [i for i in moved if isinstance(i, ArcItem)][0]
        self.assertTrue(c.c[0] + c.r <= 28.0 or c.c[0] - c.r >= 32.0)

    def test_a_round_tag_that_touches_nothing_stays(self):
        circle = ArcItem((10.0, 10.0), 3.0, 0.0, 359.9, "291-A-ANNO")
        moved = move_round_tags([circle], [_room()], M)
        self.assertEqual([i.c for i in moved if isinstance(i, ArcItem)], [(10.0, 10.0)])


if __name__ == "__main__":
    unittest.main()
