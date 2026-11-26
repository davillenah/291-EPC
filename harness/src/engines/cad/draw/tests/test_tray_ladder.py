"""A tray with a width is drawn as what it is (ladder, perforated, solid, wire mesh) with rails, joints and bends."""
import math
import unittest

import ezdxf

from epc_draw.plan import core, dxfout as D, tray_draw as T

SIZES = {"lip": 15.0, "rung_pitch": 300.0, "rung_width": 30.0, "slot_pitch": 100.0, "slot_length": 60.0, "wire_pitch": 100.0, "radius": 300.0, "joint_pitch": 3000.0, "support_spacing": 1500.0, "support_channel": 41.0, "support_overhang": 25.0, "support_rod": 10.0}
TRAYS = {"default_kind": "escalera", "lip_mm": 15.0, "rung_pitch_mm": 300.0, "rung_width_mm": 30.0, "slot_pitch_mm": 100.0, "slot_length_mm": 60.0, "wire_pitch_mm": 100.0,
         "radius_mm": 300.0, "joint_length_mm": 3000.0, "support_spacing_mm": 1500.0, "support_channel_mm": 41.0, "support_overhang_mm": 25.0, "support_rod_mm": 10.0}
STRAIGHT = [(0.0, 0.0), (6500.0, 0.0)]


def across(lines):
    return [ln for ln in lines if abs(ln[0][0] - ln[1][0]) < 1e-9]


class TestPath(unittest.TestCase):
    def test_a_corner_with_room_is_rounded_with_the_radius(self):
        path = T.fillet_path([(0.0, 0.0), (3000.0, 0.0), (3000.0, 3000.0)], 300.0)
        self.assertEqual((path[0], path[-1]), ((0.0, 0.0), (3000.0, 3000.0)))
        centre = (2700.0, 300.0)
        arc = [p for p in path if 2700.0 < p[0] < 3000.0 or 0.0 < p[1] < 300.0]
        self.assertTrue(arc)
        self.assertTrue(all(math.isclose(math.dist(p, centre), 300.0, abs_tol=1e-6) for p in path[1:-1]))

    def test_a_corner_without_room_stays_square_and_a_short_path_is_left_alone(self):
        self.assertEqual(T.fillet_path([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)], 300.0), [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)])
        self.assertEqual(T.fillet_path([(0.0, 0.0), (5.0, 0.0)], 300.0), [(0.0, 0.0), (5.0, 0.0)])
        self.assertEqual(T.fillet_path([(0.0, 0.0), (1000.0, 0.0), (2000.0, 0.0)], 300.0)[1], (1000.0, 0.0))

    def test_a_turn_to_the_other_side_is_rounded_too(self):
        path = T.fillet_path([(0.0, 0.0), (3000.0, 0.0), (3000.0, -3000.0)], 300.0)
        self.assertTrue(all(math.isclose(math.dist(p, (2700.0, -300.0)), 300.0, abs_tol=1e-6) for p in path[1:-1]))

    def test_the_edges_of_a_bend_meet_at_the_corner(self):
        pts = [(0.0, 0.0), (3000.0, 0.0), (3000.0, 2000.0)]
        self.assertEqual(T.offset_path(pts, 150.0), [(0.0, 150.0), (2850.0, 150.0), (2850.0, 2000.0)])
        self.assertEqual(T.offset_path(pts, -150.0), [(0.0, -150.0), (3150.0, -150.0), (3150.0, 2000.0)])

    def test_repeated_points_a_single_point_and_a_fold_back_do_not_break_it(self):
        self.assertEqual(T.offset_path([(1.0, 1.0), (1.0, 1.0)], 5.0), [(1.0, 1.0)])
        self.assertTrue(all(math.isfinite(c) for p in T.offset_path([(0.0, 0.0), (1000.0, 0.0), (0.0, 0.0)], 10.0) for c in p))

    def test_stations_are_by_length_and_never_at_the_ends(self):
        self.assertEqual([p for p, _ in T.stations([(0.0, 0.0), (1000.0, 0.0)], 250.0)], [(250.0, 0.0), (500.0, 0.0), (750.0, 0.0)])
        self.assertEqual([p for p, _ in T.stations([(0.0, 0.0), (1000.0, 0.0)], 500.0)], [(500.0, 0.0)])
        along_two = [p for p, _ in T.stations([(0.0, 0.0), (600.0, 0.0), (600.0, 600.0)], 500.0)]
        self.assertEqual(along_two, [(500.0, 0.0), (600.0, 400.0)])


class TestKinds(unittest.TestCase):
    def test_a_ladder_has_two_rails_with_lip_rungs_and_a_joint_every_section(self):
        lines = T.tray_lines(STRAIGHT, "escalera", 300.0, SIZES)
        along = [ln for ln in lines if ln[0][1] == ln[1][1]]
        self.assertEqual(sorted({ln[0][1] for ln in along}), [-150.0, -135.0, 135.0, 150.0])
        rungs = across(lines)
        self.assertIn(3000.0, {ln[0][0] for ln in rungs})                                        # a joint
        self.assertIn(6000.0, {ln[0][0] for ln in rungs})
        self.assertEqual(len([ln for ln in rungs if abs(ln[0][1] - ln[1][1]) < 300.0 - 2 * 15.0 + 1e-6]), 2 * 21)   # two edges for each of the 21 rungs

    def test_perforated_and_solid_floors_differ_by_their_slots(self):
        solid = T.tray_lines(STRAIGHT, "ciega", 300.0, SIZES)
        perforated = T.tray_lines(STRAIGHT, "perforada", 300.0, SIZES)
        self.assertGreater(len(perforated), len(solid))
        self.assertTrue(all(ln[0][1] == ln[1][1] or ln[0][0] == ln[1][0] for ln in solid))

    def test_a_wire_mesh_has_longitudinal_and_cross_wires(self):
        lines = T.tray_lines(STRAIGHT, "alambre", 300.0, SIZES)
        self.assertEqual(len({ln[0][1] for ln in lines if ln[0][1] == ln[1][1]}), 5)
        self.assertGreater(len(across(lines)), 60)

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(core.PlanError):
            T.tray_lines(STRAIGHT, "x", 300.0, SIZES)

    def test_every_kind_draws_a_bend(self):
        for kind in T.KINDS:
            lines = T.tray_lines([(0.0, 0.0), (4000.0, 0.0), (4000.0, 4000.0)], kind, 300.0, SIZES)
            self.assertTrue(all(math.isfinite(c) for ln in lines for p in ln for c in p), kind)


class TestSupports(unittest.TestCase):
    def test_a_hanger_every_spacing_with_a_bar_and_two_rods(self):
        shapes = T.support_shapes(STRAIGHT, 300.0, SIZES)
        self.assertEqual(len(shapes["circles"]), 2 * 4)                                           # 1500, 3000, 4500, 6000 on a 6500 mm run
        self.assertEqual(len(shapes["lines"]), 4 * 4)
        xs = sorted({c[0][0] for c in shapes["circles"]})
        self.assertEqual(xs, [1500.0, 3000.0, 4500.0, 6000.0])
        self.assertEqual(sorted({round(c[0][1], 6) for c in shapes["circles"]}), [-175.0, 175.0])   # the tray width plus 25 mm on each side
        self.assertTrue(all(r == 5.0 for _, r in shapes["circles"]))

    def test_a_run_shorter_than_the_spacing_has_none(self):
        self.assertEqual(T.support_shapes([(0.0, 0.0), (1000.0, 0.0)], 300.0, SIZES), {"lines": [], "circles": []})


class TestInTheDrawing(unittest.TestCase):
    def lines(self, attrs, trays=TRAYS, support_layer=None):
        doc = ezdxf.new("R2018")
        blk = doc.blocks.new("T")
        D._add_tray_detail(blk, {"attrs": attrs}, [(0.0, 0.0), (3.0, 0.0)], (0.0, 0.0), 1.0, trays, "L", support_layer)      # scale 1: drawing unit = metre
        return [e for e in blk if e.dxftype() == "LINE"]

    def test_only_a_tray_with_a_width_is_drawn_with_detail(self):
        self.assertTrue(self.lines({"ancho_mm": 300}))
        self.assertEqual(self.lines({}), [])
        self.assertEqual(self.lines({"ancho_mm": "x"}), [])

    def test_the_kind_comes_from_the_stretch_or_the_default(self):
        self.assertGreater(len(self.lines({"ancho_mm": 300, "tipo_bandeja": "perforada"})), len(self.lines({"ancho_mm": 300, "tipo_bandeja": "ciega"})))
        self.assertEqual(len(self.lines({"ancho_mm": 300})), len(self.lines({"ancho_mm": 300, "tipo_bandeja": "escalera"})))

    def test_the_hangers_go_on_their_own_layer_and_can_be_switched_off(self):
        doc = ezdxf.new("R2018")
        blk = doc.blocks.new("T")
        D._add_tray_detail(blk, {"attrs": {"ancho_mm": 300}}, [(0.0, 0.0), (4.0, 0.0)], (0.0, 0.0), 1.0, TRAYS, "L", "SUP")
        self.assertEqual({e.dxf.layer for e in blk if e.dxftype() == "CIRCLE"}, {"SUP"})
        self.assertEqual(len([e for e in blk if e.dxftype() == "CIRCLE"]), 4)                     # hangers at 1.5 and 3 m
        off = ezdxf.new("R2018").blocks.new("U")
        D._add_tray_detail(off, {"attrs": {"ancho_mm": 300}}, [(0.0, 0.0), (4.0, 0.0)], (0.0, 0.0), 1.0, dict(TRAYS, supports=False), "L", "SUP")
        self.assertEqual([e for e in off if e.dxftype() == "CIRCLE"], [])

    def test_an_unknown_kind_is_an_error_in_two_languages(self):
        with self.assertRaises(core.PlanError) as c:
            self.lines({"ancho_mm": 300, "tipo_bandeja": "madera"})
        self.assertEqual(c.exception.code, "err_tray_kind")
        self.assertIn("madera", c.exception.en)
        self.assertTrue(c.exception.es)


if __name__ == "__main__":
    unittest.main()
