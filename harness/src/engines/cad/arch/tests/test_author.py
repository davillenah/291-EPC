"""A building drawn from its description (`epc_arch.author`) and read back: the same rooms, codes, names, doors and windows (found by the real simulation of 2026-11-15: SIM-01, SIM-02, SIM-03)."""
import copy
import math
import unittest

from epc_arch import ArchError, recognize
from epc_arch.author import architecture_of, errors_of, floors_of, plan_dxf

BOXES = {"01": [0, 0, 8, 7], "02": [8, 0, 16, 7], "03": [16, 0, 24, 7], "04": [0, 7, 8, 14], "05": [8, 7, 16, 14], "06": [16, 7, 20, 14], "07": [20, 7, 24, 14]}
NAMES = {"01": "Local comercial", "02": "Hall y recepcion", "03": "Sala electrica", "04": "Cafeteria", "05": "Palier y escalera", "06": "Sanitarios", "07": "Deposito"}


def floor(prefix="PB", name="PLANTA BAJA", index=0):
    code = lambda k: f"{prefix}-{k}"                                             # noqa: E731
    return {"name": name, "index": index, "wall_thickness_m": 0.2,
            "rooms": [{"code": code(k), "name": NAMES[k], "box_m": box} for k, box in BOXES.items()],
            "doors": [{"room": code("02"), "side": "S", "width_m": 1.2, "offset_m": 4.0},                      # the entrance, wider than the others
                      {"room": code("01"), "side": "E", "width_m": 0.9}, {"room": code("03"), "side": "W", "width_m": 0.9}, {"room": code("05"), "side": "S", "width_m": 0.9},
                      {"room": code("04"), "side": "E", "width_m": 0.9}, {"room": code("06"), "side": "W", "width_m": 0.9}, {"room": code("07"), "side": "W", "width_m": 0.8}],
            "windows": [{"room": code("01"), "side": "S", "width_m": 2.4}, {"room": code("04"), "side": "N", "width_m": 2.4},
                        {"room": code("01"), "side": "W", "width_m": 2.0}, {"room": code("04"), "side": "W", "width_m": 2.0},   # windows in a vertical outside wall: they left a corner of wall between two windows
                        {"room": code("06"), "side": "N", "width_m": 1.0}, {"room": code("07"), "side": "N", "width_m": 1.0}]}


def plan_primitives(data):
    """The strokes of a plan file as the recognizers get them: without its title block, in the plan space."""
    from epc_arch import pipeline, sources
    from epc_arch.model import Options
    from epc_arch.normalize import normalize
    return normalize(pipeline._without_title(sources.read(data, "plan.dxf", Options())))


def read_back(description):
    arch = architecture_of(description)
    return arch, recognize(plan_dxf(arch).encode("utf-8"), "plan.dxf").architecture


class AuthoredBuilding(unittest.TestCase):
    def test_a_described_floor_becomes_walls_rooms_doors_and_windows(self):
        arch = architecture_of(floor())
        self.assertEqual((len(arch.rooms), arch.counts()["doors"], arch.counts()["windows"]), (7, 7, 6))
        self.assertEqual(len(arch.walls), 8)                                    # 4 outside walls, the middle one, 2 full-height partitions and the short one
        self.assertTrue(all(o.wall for o in arch.openings))
        self.assertAlmostEqual(arch.rooms[0].area_m2, 7.8 * 6.8, places=6)
        self.assertEqual((arch.level.index, arch.level.key), (0, "GROUND_FLOOR"))

    def test_the_plan_is_read_back_with_every_room_its_code_and_its_name(self):
        _, read = read_back(floor())
        self.assertEqual(sorted((r.code, r.name) for r in read.rooms), sorted((f"PB-{k}", NAMES[k]) for k in NAMES))
        self.assertEqual((read.counts()["doors"], read.counts()["windows"], read.counts()["openings"]), (7, 6, 0))

    def test_the_areas_read_back_are_the_authored_ones(self):
        arch, read = read_back(floor())
        authored = {r.code: r.area_m2 for r in arch.rooms}
        for r in read.rooms:
            self.assertAlmostEqual(r.area_m2, authored[r.code], delta=0.03 * authored[r.code], msg=r.code)

    def test_a_code_with_a_digit_in_its_letters_is_read(self):                 # `P1-01`: the first floor (ARQ-28)
        _, read = read_back(floor("P1", "PLANTA ALTA", 1))
        self.assertEqual(sorted(r.code for r in read.rooms), [f"P1-{k}" for k in sorted(NAMES)])

    def test_several_floors_or_one(self):
        self.assertEqual(len(floors_of({"floors": [floor(), floor("P1", "PLANTA ALTA", 1)]})), 2)
        self.assertEqual(len(floors_of(floor())), 1)


class DescriptionErrors(unittest.TestCase):
    def bad(self, change):
        d = copy.deepcopy(floor())
        change(d)
        return errors_of(d)

    def test_a_good_description_has_no_errors(self):
        self.assertEqual(errors_of(floor()), [])

    def test_nothing_is_assumed(self):
        self.assertTrue(any("wall_thickness_m" in e for e in self.bad(lambda d: d.pop("wall_thickness_m"))))
        self.assertTrue(any("box_m" in e for e in self.bad(lambda d: d["rooms"][0].pop("box_m"))))
        self.assertTrue(any("width_m" in e for e in self.bad(lambda d: d["doors"][0].pop("width_m"))))

    def test_rooms_that_overlap_or_repeat_a_code(self):
        self.assertTrue(any("overlap" in e for e in self.bad(lambda d: d["rooms"][1].update(box_m=[7, 0, 16, 7]))))
        self.assertTrue(any("used twice" in e for e in self.bad(lambda d: d["rooms"][1].update(code="PB-01"))))

    def test_an_opening_that_does_not_fit_or_names_no_room(self):
        self.assertTrue(any("does not fit" in e for e in self.bad(lambda d: d["windows"][0].update(width_m=9.0))))
        self.assertTrue(any("room" in e for e in self.bad(lambda d: d["doors"][0].update(room="XX-99"))))
        self.assertTrue(any("unknown key" in e for e in self.bad(lambda d: d["windows"][0].update(opens="in"))))

    def test_a_bad_description_is_refused(self):
        with self.assertRaises(ArchError):
            architecture_of({"name": "PLANTA BAJA"})


class ReviewOfAPlan(unittest.TestCase):
    def test_each_door_joins_two_rooms_or_a_room_and_the_outside(self):
        from epc_arch.review import connections
        arch = architecture_of(floor())
        doors = {tuple(c["rooms"]) for c in connections(arch) if c["kind"] == "door"}
        self.assertIn(("PB-02", ""), doors)                                    # the entrance
        self.assertIn(("PB-02", "PB-01"), doors)
        self.assertTrue(all(c["rooms"][1] == "" for c in connections(arch) if c["kind"] == "window"))

    def test_a_room_no_door_reaches_is_noted(self):
        from epc_arch.review import notes
        self.assertEqual(notes(architecture_of(floor())), [])
        shut = floor()
        shut["doors"] = [d for d in shut["doors"] if d["room"] != "PB-07"]
        self.assertEqual([(n["rule"], n["room"]) for n in notes(architecture_of(shut))], [("no_door", "PB-07")])

    def test_the_plan_read_back_has_nothing_to_note(self):
        from epc_arch import review
        _, read = read_back(floor())
        self.assertEqual(review(read)["notes"], [])


class WallsAreNotLabels(unittest.TestCase):
    def test_a_corner_between_two_windows_is_not_a_label_even_without_layer_names(self):
        """The corner of the building between a window of the south wall and one of the west wall is a closed loop of short strokes with the name of the room inside its box:
        it used to be taken for the box of a tag (2 rooms of 7 were lost)."""
        from dataclasses import replace
        from epc_arch.model import Options, Primitives
        from epc_arch.recognizers import annotations
        prims, size = plan_primitives(plan_dxf(architecture_of(floor())).encode("utf-8"))
        prims = Primitives(**{**prims.__dict__, "lines": [replace(l, layer="") for l in prims.lines], "arcs": [replace(a, layer="") for a in prims.arcs]})
        _, marks = annotations.split(prims, size)
        longest = max((math.hypot(l.b[0] - l.a[0], l.b[1] - l.a[1]) for l in marks["labels"].lines), default=0.0)
        self.assertLess(longest, 0.05 * max(size))                             # nothing as long as a stretch of wall (2.5 m of 24 m) is a label


class DxfCircles(unittest.TestCase):
    def test_a_circle_is_read_as_a_whole_turn(self):                        # ARQ-27: the bubbles of the grid axes were not read
        import io
        import ezdxf
        from epc_arch.model import Options
        from epc_arch.sources import read
        doc = ezdxf.new()
        doc.modelspace().add_circle((5, 5), 0.4)
        doc.modelspace().add_line((0, 0), (10, 0))
        out = io.StringIO()
        doc.write(out)
        prims = read(out.getvalue().encode("utf-8"), "c.dxf", Options())
        self.assertEqual([(a.r, a.start, a.end) for a in prims.arcs], [(0.4, 0.0, 360.0)])
        self.assertFalse(any("circle" in w for w in prims.warnings))


if __name__ == "__main__":
    unittest.main()
