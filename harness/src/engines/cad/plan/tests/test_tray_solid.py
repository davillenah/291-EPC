import unittest

from epc_plan import tray_solid as S

P = {"rail": 2.0, "rung": 30.0, "rung_thick": 3.0, "rung_pitch": 300.0}
RUN = [(3000, -3500, 0), (3000, -1500, 0), (3000, -750, 600), (3000, 750, 600), (3000, 1500, 0), (3000, 3500, 0)]


class TestSolid(unittest.TestCase):
    def test_the_path_climbs_to_the_height_of_the_run_and_comes_back(self):
        path = S.path3d(RUN, 300.0, 300.0)
        self.assertAlmostEqual(max(p[2] for p in path), 600.0, places=6)
        self.assertEqual((path[0][2], path[-1][2]), (0.0, 0.0))

    def test_the_mesh_is_made_of_valid_quads(self):
        mesh = S.ladder_mesh(S.path3d(RUN, 300.0, 300.0), 300.0, 100.0, P)
        self.assertGreater(len(mesh["faces"]), 100)
        self.assertTrue(all(len(f) == 4 and all(0 <= i < len(mesh["vertices"]) for i in f) for f in mesh["faces"]))

    def test_a_straight_tray_has_two_rails_and_a_rung_every_pitch(self):
        mesh = S.ladder_mesh([(0.0, 0.0, 0.0), (3000.0, 0.0, 0.0)], 300.0, 100.0, P)
        self.assertEqual(len(mesh["faces"]) // 6, 2 + 10)

    def test_the_same_input_gives_the_same_mesh(self):
        a = S.ladder_mesh(S.path3d(RUN, 300.0, 300.0), 300.0, 100.0, P)
        self.assertEqual(a, S.ladder_mesh(S.path3d(RUN, 300.0, 300.0), 300.0, 100.0, P))


if __name__ == "__main__":
    unittest.main()
