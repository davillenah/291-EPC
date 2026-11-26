import unittest

from epc_draw.plan import clash_scene as C, tray_solid as S

P = {"rail": 0.002, "rung": 0.03, "rung_thick": 0.003, "rung_pitch": 0.3}


def wall(x0, x1):
    v = [[x, y, z] for z in (0.0, 3.0) for x, y in ((x0, -7.0), (x1, -7.0), (x1, 0.0), (x0, 0.0))]
    return {"id": "w1", "tag": "w1", "kind": "wall", "layer": "A", "level": "PB", "mesh": {"vertices": v, "faces": [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]}}


def tray(ident, run):
    return S.solid(ident, ident, run, "T", 0.3, 0.1, P, 0.3, 0.3, "PB")


class TestClashScene(unittest.TestCase):
    def test_a_tray_through_a_wall_is_a_hard_clash(self):
        scene = {"solids": [wall(3.9, 4.1), tray("T2", [(0.6, -2.0, 2.4), (7.4, -2.0, 2.4)])]}
        (c,) = C.detect(scene)
        self.assertEqual((c["type"], c["severity"]), ("hard", "error"))
        self.assertTrue(3.9 <= c["point_m"][0] <= 4.1)
        self.assertEqual(set(c["text"]), {"en", "es"})

    def test_a_tray_that_stops_short_of_the_wall_does_not_clash(self):
        self.assertEqual(C.detect({"solids": [wall(3.9, 4.1), tray("T2", [(0.6, -2.0, 2.4), (3.0, -2.0, 2.4)])]}), [])

    def test_a_tray_over_another_clashes_only_below_the_clearance(self):
        scene = {"solids": [tray("A", [(0.0, 0.0, 2.4), (4.0, 0.0, 2.4)]), tray("B", [(2.0, -2.0, 2.55), (2.0, 2.0, 2.55)])]}
        self.assertEqual(C.detect(scene), [])
        (c,) = C.detect(scene, clearance_m=0.2)
        self.assertEqual(c["type"], "clearance")

    def test_the_same_scene_gives_the_same_list(self):
        scene = {"solids": [wall(3.9, 4.1), tray("T2", [(0.6, -2.0, 2.4), (7.4, -2.0, 2.4)])]}
        self.assertEqual(C.detect(scene), C.detect(scene))


if __name__ == "__main__":
    unittest.main()
