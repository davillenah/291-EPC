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

    def test_a_tray_is_a_solid_of_the_scene(self):
        from epc_plan import scene3d
        sol = S.solid("T1", "T1", [(0.0, 0.0, 2.4), (3.0, 0.0, 2.4)], "291-E-CABL-TRAY-N", 0.3, 0.1, {"rail": 0.002, "rung": 0.03, "rung_thick": 0.003, "rung_pitch": 0.3}, 0.3, 0.3, "PB")
        self.assertEqual((sol["kind"], sol["layer"]), ("tray", "291-E-CABL-TRAY-N"))
        scene3d.check({"schema_version": "1.0", "units": "m", "solids": [sol], "box": None})


if __name__ == "__main__":
    unittest.main()


def test_rail_section_is_a_c_with_foot_and_rolled_edge():
    from epc_plan import tray_solid
    section = tray_solid.rail_section(0.09, 0.015, 0.012)
    assert section[0] == (0.015, 0.0) and section[1] == (0.0, 0.0)          # foot turned in, then the web
    assert max(h for _, h in section) == 0.09                                # up to the rail height
    mesh = tray_solid.ladder_mesh([(0, 0, 0), (1, 0, 0)], 0.3, 0.09, {"rail": 0.002, "rung": 0.03, "rung_thick": 0.015, "rung_pitch": 0.3, "foot": 0.015, "curl": 0.012})
    assert len(mesh["faces"]) >= 2 * (len(section) - 1)
