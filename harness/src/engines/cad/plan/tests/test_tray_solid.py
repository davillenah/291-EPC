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


def test_rail_web_has_side_slots():
    from epc_plan import tray_solid
    p = {"rail": 0.002, "rung": 0.03, "rung_thick": 0.015, "rung_pitch": 0.3, "foot": 0.015, "curl": 0.012, "slot_pitch": 0.1, "slot": 0.05, "slot_height": 0.012}
    slotted = tray_solid.ladder_mesh([(0, 0, 0), (1, 0, 0)], 0.3, 0.09, p)
    plain = tray_solid.ladder_mesh([(0, 0, 0), (1, 0, 0)], 0.3, 0.09, {k: v for k, v in p.items() if not k.startswith("slot")})
    assert len(slotted["faces"]) > len(plain["faces"])
    assert all(len(f) == 4 for f in slotted["faces"])


def test_cover_adds_a_lid_over_the_rails():
    from epc_plan import tray_solid
    p = {"rail": 0.002, "rung": 0.03, "rung_thick": 0.015, "rung_pitch": 0.3}
    open_tray = tray_solid.ladder_mesh([(0, 0, 0), (1, 0, 0)], 0.3, 0.09, p)
    closed = tray_solid.ladder_mesh([(0, 0, 0), (1, 0, 0)], 0.3, 0.09, dict(p, cover=0.004))
    assert len(closed["faces"]) == len(open_tray["faces"]) + 1
    assert max(v[2] for v in closed["vertices"]) > max(v[2] for v in open_tray["vertices"])


def test_every_tray_kind_has_a_mesh():
    import pytest
    from epc_plan import core, tray_solid
    p = {"rail": 0.002, "rung": 0.03, "rung_thick": 0.015, "rung_pitch": 0.3, "foot": 0.015, "curl": 0.012, "slot_pitch": 0.1, "slot": 0.05, "slot_height": 0.012,
         "floor_margin": 0.02, "wire": 0.004, "wire_pitch": 0.05}
    path = [(0, 0, 0), (1, 0, 0), (1, 1, 0)]
    counts = {k: len(tray_solid.tray_mesh(path, 0.3, 0.09, p, k)["faces"]) for k in ("escalera", "perforada", "ciega", "alambre")}
    assert all(c > 0 for c in counts.values())
    assert counts["perforada"] > counts["ciega"]                     # the slots split the floor
    assert counts["alambre"] > counts["escalera"]                    # a mesh is many wires
    with pytest.raises(core.PlanError):
        tray_solid.tray_mesh(path, 0.3, 0.09, p, "nope")


def test_joints_carry_four_bolts_every_section_length():
    from epc_plan import tray_solid
    p = {"rail": 0.002, "rung": 0.03, "rung_thick": 0.015, "rung_pitch": 0.3, "joint": 3.0, "bolt": 0.016}
    plain = tray_solid.ladder_mesh([(0, 0, 0), (7, 0, 0)], 0.3, 0.09, {k: v for k, v in p.items() if k not in ("joint", "bolt")})
    bolted = tray_solid.ladder_mesh([(0, 0, 0), (7, 0, 0)], 0.3, 0.09, p)
    assert len(bolted["faces"]) - len(plain["faces"]) == 2 * 4 * 6          # joints at 3 m and 6 m, four boxes of six faces each


def test_a_vertical_bend_can_be_a_few_straight_links():
    from epc_plan import tray_solid
    run = [(0, 0, 0), (2, 0, 0), (2, 0, 1)]
    smooth = tray_solid.path3d(run, 0.0, 0.5, 8)
    linked = tray_solid.path3d(run, 0.0, 0.5, 5)
    assert len(linked) < len(smooth)
