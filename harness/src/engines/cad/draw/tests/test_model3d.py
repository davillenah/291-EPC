"""The building in three dimensions (`epc_draw.arch.model3d`): from the plan and the heights the person gives."""
import unittest

from epc_draw.arch import ArchError
from epc_draw.arch.author import architecture_of
from epc_draw.arch.model3d import box_mesh, building_scene, building_solids

import test_sections as T


def extent(solid, axis):
    vs = [v[axis] for v in solid["mesh"]["vertices"]]
    return round(min(vs), 3), round(max(vs), 3)


class Building(unittest.TestCase):
    def solids(self, **heights):
        return building_solids(T.arch(), dict(T.H, **heights))

    def test_a_box_has_eight_corners_six_faces_and_y_up(self):
        m = box_mesh((0.0, 1.0, 0.0, 2.0, 3.0, 4.0))
        self.assertEqual((len(m["vertices"]), len(m["faces"])), (8, 6))
        self.assertEqual((min(v[1] for v in m["vertices"]), max(v[1] for v in m["vertices"])), (-3.0, -1.0))     # the plan's y, turned over

    def test_every_kind_of_solid_is_there(self):
        kinds = [s["kind"] for s in self.solids()]
        self.assertEqual((kinds.count("slab"), kinds.count("glass"), kinds.count("room")), (2, 2, 2))
        self.assertTrue(all(len(s["mesh"]["vertices"]) == 8 and len(s["mesh"]["faces"]) == 6 for s in self.solids()))

    def test_a_wall_is_open_at_its_door_and_at_its_window(self):
        walls = [s for s in self.solids() if s["kind"] == "wall"]
        over_door = [s for s in walls if extent(s, 2) == (2.05, 2.8)]
        self.assertEqual(sorted(round(extent(s, 0)[1] - extent(s, 0)[0] + extent(s, 1)[1] - extent(s, 1)[0], 2) for s in over_door), [1.1, 1.2])     # the lintels of the two doors: 0.9 and 1.0 m, plus the wall thickness
        self.assertEqual(len([s for s in walls if extent(s, 2) == (0.0, 0.9)]), 2)                    # under each window
        self.assertEqual(len([s for s in walls if extent(s, 2) == (2.1, 2.8)]), 2)                    # and above it
        glass = [s for s in self.solids() if s["kind"] == "glass"]
        self.assertEqual({extent(s, 2) for s in glass}, {(0.9, 2.1)})

    def test_the_volume_of_the_walls_is_the_wall_minus_its_openings(self):
        def volume(s):
            return (extent(s, 0)[1] - extent(s, 0)[0]) * (extent(s, 1)[1] - extent(s, 1)[0]) * (extent(s, 2)[1] - extent(s, 2)[0])
        south = [s for s in self.solids() if s["kind"] == "wall" and s["tag"] == next(x["tag"] for x in self.solids() if x["kind"] == "wall" and extent(x, 2) == (0.0, 0.9) and extent(x, 0)[1] - extent(x, 0)[0] > 1.9)]
        whole = 10.2 * 0.2 * 2.8
        holes = 1.0 * 0.2 * 2.05 + 2.0 * 0.2 * (2.1 - 0.9)                       # the entrance and the south window
        self.assertAlmostEqual(sum(volume(s) for s in south), whole - holes, places=2)

    def test_the_floor_stands_at_its_level(self):
        up = self.solids(elevation_m=3.0)
        self.assertEqual(min(extent(s, 2)[0] for s in up), 2.8)                    # the slab under the floor: 3.0 - 0.2
        self.assertEqual(max(extent(s, 2)[1] for s in up), 6.0)

    def test_the_heights_are_required(self):
        with self.assertRaises(ArchError):
            building_solids(T.arch(), {})


class Scene(unittest.TestCase):
    def test_two_floors_make_one_scene(self):
        first = dict(T.FLOOR, name="PLANTA ALTA", index=1)
        sc = building_scene([(T.arch(), T.H), (architecture_of(first), dict(T.H, elevation_m=3.0))])
        self.assertEqual((sc["schema_version"], sc["units"]), ("1.0", "m"))
        self.assertEqual(len(sc["solids"]), 2 * len(building_solids(T.arch(), T.H)))
        self.assertEqual((sc["box"][0][2], sc["box"][1][2]), (-0.2, 6.0))
        self.assertEqual(len({s["id"] for s in sc["solids"]}), len(sc["solids"]))                   # every solid has its own id
        self.assertEqual({s["level"] for s in sc["solids"]}, {"PLANTA BAJA", "PLANTA ALTA"})

    def test_the_same_building_gives_the_same_scene(self):
        self.assertEqual(building_scene([(T.arch(), T.H)]), building_scene([(T.arch(), T.H)]))


if __name__ == "__main__":
    unittest.main()
