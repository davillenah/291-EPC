"""Elevations and sections derived from a plan and the heights the person gives (`epc_draw.arch.sections`, ADR-0032 decisions 3 and 4)."""
import unittest

from epc_draw.arch import ArchError, recognize
from epc_draw.arch.author import architecture_of, plan_dxf
from epc_draw.arch.sections import Label, Rect, elevation, heights_errors, section, stack, view_drawing, view_dxf

H = {"wall_height_m": 2.8, "door_head_m": 2.05, "window_sill_m": 0.9, "window_head_m": 2.1, "slab_m": 0.2, "elevation_m": 0.0}
# two rooms side by side, 10 x 5 m between axes: a door between them, the entrance in the south wall of A, a window in the south wall of B and one in the east wall of B
FLOOR = {"name": "PLANTA BAJA", "index": 0, "wall_thickness_m": 0.2,
         "rooms": [{"code": "PB-01", "name": "Hall", "box_m": [0, 0, 5, 5]}, {"code": "PB-02", "name": "Oficina", "box_m": [5, 0, 10, 5]}],
         "doors": [{"room": "PB-01", "side": "S", "width_m": 1.0, "offset_m": 1.5}, {"room": "PB-01", "side": "E", "width_m": 0.9, "offset_m": 2.5}],
         "windows": [{"room": "PB-02", "side": "S", "width_m": 2.0, "offset_m": 2.5}, {"room": "PB-02", "side": "E", "width_m": 1.5, "offset_m": 2.5}]}


def arch():
    return architecture_of(FLOOR)


def spans(view, role):
    return sorted((round(r.u0, 2), round(r.z0, 2), round(r.u1, 2), round(r.z1, 2)) for r in view.of(role) if isinstance(r, Rect))


class Heights(unittest.TestCase):
    def test_every_height_is_an_input(self):
        self.assertEqual(heights_errors(H), [])
        for key in H:
            self.assertTrue(any(key in e for e in heights_errors({k: v for k, v in H.items() if k != key})), key)

    def test_heights_that_cannot_be(self):
        self.assertTrue(heights_errors(dict(H, door_head_m=3.0)))
        self.assertTrue(heights_errors(dict(H, window_sill_m=2.2)))
        self.assertTrue(heights_errors(dict(H, extra=1)))

    def test_a_view_without_heights_or_units_is_refused(self):
        with self.assertRaises(ArchError):
            elevation(arch(), "S", {})
        a = arch()
        a.units_per_metre = None
        with self.assertRaises(ArchError):
            elevation(a, "S", H)


class Elevations(unittest.TestCase):
    def test_the_south_elevation_shows_its_wall_its_door_and_its_window(self):
        v = elevation(arch(), "S", H)
        self.assertEqual(spans(v, "seen"), [(0.0, 0.0, 10.2, 2.8), (0.0, 2.8, 10.2, 3.0)])           # the wall in sight and the slab above
        self.assertEqual(spans(v, "door"), [(1.1, 0.0, 2.1, 2.05)])
        self.assertEqual(spans(v, "window"), [(6.6, 0.9, 8.6, 2.1)])
        self.assertEqual(len(v.of("ground")), 1)

    def test_the_north_elevation_is_mirrored_and_has_no_openings(self):
        v = elevation(arch(), "N", H)
        self.assertEqual(spans(v, "seen")[0], (-10.2, 0.0, 0.0, 2.8))
        self.assertEqual((spans(v, "door"), spans(v, "window")), ([], []))

    def test_the_east_elevation_shows_the_window_of_the_east_wall_only(self):
        v = elevation(arch(), "E", H)
        self.assertEqual(len(spans(v, "window")), 1)
        self.assertEqual(spans(v, "door"), [])                                  # the door between the rooms is hidden by the east wall
        w = spans(v, "window")[0]
        self.assertAlmostEqual(w[2] - w[0], 1.5, places=2)

    def test_a_wrong_side(self):
        with self.assertRaises(ArchError):
            elevation(arch(), "NE", H)


class Sections(unittest.TestCase):
    def test_a_plane_across_both_rooms_cuts_three_walls_and_passes_through_the_door(self):
        v = section(arch(), "y", 2.7, "N", H)                                   # y = 2.7 m from the top: through the door between the rooms (its middle is 2.5 m from the south end) and the east window
        cut = spans(v, "cut")
        self.assertIn((0.0, 0.0, 0.2, 2.8), cut)                                # the west wall, whole
        self.assertIn((5.0, 2.05, 5.2, 2.8), cut)                               # the middle wall, only above the door
        self.assertIn((10.0, 0.0, 10.2, 0.9), cut)                              # the east wall under the window...
        self.assertIn((10.0, 2.1, 10.2, 2.8), cut)                              # ...and above it
        self.assertNotIn((5.0, 0.0, 5.2, 2.8), cut)
        self.assertEqual(sorted(l.value for l in v.items if isinstance(l, Label) and l.role == "room"), ["Hall", "Oficina"])

    def test_the_slabs_are_cut_under_and_over_the_floor(self):
        cut = spans(section(arch(), "y", 2.7, "N", H), "cut")
        self.assertIn((0.0, -0.2, 10.2, 0.0), cut)
        self.assertIn((0.0, 2.8, 10.2, 3.0), cut)

    def test_the_wall_beyond_is_seen_with_what_it_has(self):
        north = section(arch(), "y", 2.7, "N", H)                               # looking north: the north wall, blank
        self.assertEqual((spans(north, "door"), spans(north, "window")), ([], []))
        self.assertEqual(spans(north, "seen")[0], (0.0, 0.0, 10.2, 2.8))
        south = section(arch(), "y", 2.7, "S", H)                               # looking south: the entrance and the south window, mirrored
        self.assertEqual((len(spans(south, "door")), len(spans(south, "window"))), (1, 1))
        self.assertLess(spans(south, "seen")[0][0], 0)

    def test_a_plane_along_the_building(self):
        v = section(arch(), "x", 2.6, "E", H)                                   # x = 2.6 m: through room A only, looking at the wall between the rooms and its door
        self.assertEqual(len([c for c in spans(v, "cut") if c[1] == 0.0 and c[3] == 2.8]), 2)        # the north and the south wall
        self.assertEqual(len(spans(v, "door")), 1)
        self.assertEqual([l.value for l in v.items if isinstance(l, Label) and l.role == "room"], ["Hall"])

    def test_a_plane_that_misses_the_building_or_a_wrong_look(self):
        with self.assertRaises(ArchError):
            section(arch(), "x", 40.0, "E", H)
        with self.assertRaises(ArchError):
            section(arch(), "x", 2.6, "N", H)

    def test_a_plan_read_from_a_file_gives_the_same_section(self):
        read = recognize(plan_dxf(arch()).encode("utf-8"), "plan.dxf").architecture
        authored, again = section(arch(), "y", 2.7, "N", H), section(read, "y", 2.7, "N", H)
        self.assertEqual(len(spans(again, "cut")), len(spans(authored, "cut")))
        for a, b in zip(spans(authored, "cut"), spans(again, "cut")):
            for p, q in zip(a, b):
                self.assertAlmostEqual(p, q, delta=0.06)


class Floors(unittest.TestCase):
    def test_floors_are_stacked_by_their_level(self):
        ground = elevation(arch(), "S", H)
        first = elevation(arch(), "S", dict(H, elevation_m=3.0))
        both = stack([(first, 3.0), (ground, 0.0)])
        self.assertEqual(len(both.items), 2 * len(ground.items))
        self.assertEqual(both.box()[3], 6.0)
        self.assertIn((6.6, 3.9, 8.6, 5.1), spans(both, "window"))


class Sheets(unittest.TestCase):
    def test_a_view_is_drawn_on_the_sheet_with_the_layers_of_the_style(self):
        from epc_draw.arch.drawing import load_style
        d = view_drawing(section(arch(), "y", 2.7, "N", H), arch(), sheet="A3")
        self.assertEqual(d.scale, 100)
        self.assertTrue({i.layer for i in d.items} <= set(load_style().layers))
        self.assertTrue(d.of("291-A-WALL-FULL-N") and d.of("291-A-ELEV-N") and d.of("291-A-AREA-IDEN"))

    def test_the_dxf_is_in_real_metres(self):
        import io
        import ezdxf
        doc = ezdxf.read(io.StringIO(view_dxf(elevation(arch(), "S", H), arch(), "A3")))
        boxes = [list(e.get_points("xy")) for e in doc.modelspace() if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "291-A-GLAZ-N"]
        self.assertEqual(len(boxes), 1)
        xs, ys = [p[0] for p in boxes[0]], [p[1] for p in boxes[0]]
        self.assertAlmostEqual(max(xs) - min(xs), 2.0, places=3)                # the window is 2 m wide...
        self.assertAlmostEqual(max(ys) - min(ys), 1.2, places=3)                # ...and 1.2 m high (sill 0.9, head 2.1)


if __name__ == "__main__":
    unittest.main()
