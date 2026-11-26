"""Raceways and pipes in three dimensions (epc_plan.solid): from the same footprint as the plan and the clash detection. Pure: no backend, no network."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_draw.plan import footprint, solid   # noqa: E402


def sheet(level="L0", discipline="electrica_BT", nodes=(), lines=(), scale=True):
    """A drawing where 10 view units are 1 m."""
    plan = {"id": "T", "level": level, "origin": [0, 0], **({"scale": {"p1": [0, 0], "p2": [100, 0], "distance_m": 10}} if scale else {})}
    return {"schema_version": "1.0", "plan": plan, "discipline": discipline, "nodes": list(nodes), "lines": list(lines)}


def line(i, kind, *points, **attrs):
    return {"id": i, "kind": kind, "points": list(points), **({"attrs": attrs} if attrs else {})}


TRAY = line("l1", "BN", [0, 0], [100, 0], [100, -50])          # a tray 10 m east, then 5 m north
CONDUIT = line("l2", "CN", [0, 20], [100, 20])
BOARD = {"id": "n1", "kind": "TB", "x": 0, "y": 0}


class Solids(unittest.TestCase):
    def test_a_tray_is_a_rectangle_swept_at_its_height(self):
        s = solid.solids(sheet(lines=[TRAY]), "E1")[0]
        self.assertEqual((s["shape"], s["section"], s["width_m"], s["height_m"], s["layer"]), ("run", "rect", 0.3, 0.1, "ELEC-BANDEJA"))
        self.assertEqual(s["path"], [[0.0, 0.0, 2.6], [10.0, 0.0, 2.6], [10.0, 5.0, 2.6]])

    def test_a_conduit_and_a_pipe_are_round(self):
        self.assertEqual(solid.solids(sheet(lines=[CONDUIT]), "E1")[0]["section"], "round")
        pipe = solid.solids(sheet(discipline="sanitaria_cloacas", lines=[line("p", "CC", [0, 0], [100, 0])]), "S1")[0]
        self.assertEqual((pipe["section"], pipe["path"][0][2]), ("round", -0.6))

    def test_it_agrees_with_the_footprint(self):
        doc = sheet(level="L1", lines=[line("l1", "BN", [0, 0], [100, 0], z_m=3.0, ancho_m=0.6)])
        f, s = footprint.footprints(doc, "E1")[0], solid.solids(doc, "E1")[0]
        self.assertEqual((s["width_m"], s["path"][0][2]), (f["width_m"], round((f["z0"] + f["z1"]) / 2, 4)))
        self.assertEqual(s["path"][0][2], 6.0)                                 # one storey up (3 m) plus its elevation

    def test_a_board_is_a_box_from_its_bottom_to_its_top(self):
        s = solid.solids(sheet(nodes=[BOARD]), "E1")[0]
        self.assertEqual((s["shape"], s["width_m"]), ("box", 0.6))
        self.assertEqual(s["path"], [[0.0, 0.0, 0.9], [0.0, 0.0, 2.1]])

    def test_a_drawing_without_scale_has_no_solids(self):
        self.assertEqual(solid.solids(sheet(lines=[TRAY], scale=False), "E1"), [])


class Meshes(unittest.TestCase):
    def test_each_stretch_of_a_tray_is_a_box_of_its_size(self):
        m = solid.mesh(solid.solids(sheet(lines=[TRAY]), "E1")[0])
        self.assertEqual((len(m["vertices"]), len(m["faces"])), (16, 12))       # two stretches: 8 corners and 6 faces each
        first = m["vertices"][:8]
        self.assertEqual((min(v[1] for v in first), max(v[1] for v in first)), (-0.15, 0.15))        # 0.3 m wide, across the run
        self.assertEqual((min(v[2] for v in first), max(v[2] for v in first)), (2.55, 2.65))         # 0.1 m high, about its height
        self.assertEqual((min(v[0] for v in first), max(v[0] for v in first)), (0.0, 10.0))

    def test_a_conduit_is_a_cylinder_of_its_diameter(self):
        m = solid.mesh(solid.solids(sheet(lines=[CONDUIT]), "E1")[0])
        sides = solid.core.PARAMS["solid"]["sides"]
        self.assertEqual(len(m["vertices"]), 2 * sides + 2)
        ring = m["vertices"][:sides]
        for v in ring:
            self.assertAlmostEqual(((v[1] + 2.0) ** 2 + (v[2] - 2.6) ** 2) ** 0.5, 0.025, places=3)   # radius 25 mm about the axis (y = -2 m, z = 2.6 m)
        self.assertTrue(all(0 <= i < len(m["vertices"]) for f in m["faces"] for i in f))

    def test_a_vertical_run_has_its_section_in_the_plan(self):
        riser = {"id": "r", "tag": "R", "kind": "BN", "discipline": "electrica_BT", "level": "L0", "sheet": "E1", "layer": "ELEC-BANDEJA", "shape": "run", "section": "rect",
                 "width_m": 0.3, "height_m": 0.1, "path": [[1.0, 1.0, 0.0], [1.0, 1.0, 3.0]]}
        m = solid.mesh(riser)
        self.assertEqual((min(v[2] for v in m["vertices"]), max(v[2] for v in m["vertices"])), (0.0, 3.0))
        self.assertEqual((min(v[0] for v in m["vertices"]), max(v[0] for v in m["vertices"])), (0.85, 1.15))

    def test_the_scene_holds_every_solid_and_its_box(self):
        sc = solid.scene(solid.solids(sheet(nodes=[BOARD], lines=[TRAY, CONDUIT]), "E1"))
        self.assertEqual(len(sc["solids"]), 3)
        self.assertEqual(sc["box"][1][2], 2.65)
        self.assertEqual(sc, solid.scene(solid.solids(sheet(nodes=[BOARD], lines=[TRAY, CONDUIT]), "E1")))    # the same drawing gives the same scene


class Outputs(unittest.TestCase):
    def test_the_isometric_view_keeps_the_heights(self):
        iso = solid.isometric(solid.solids(sheet(lines=[TRAY]), "E1"))[0]
        self.assertEqual(len(iso["edges"]), 24)                                 # 12 edges per box
        self.assertEqual(iso["axis"][0], [0.0, 2.6])                            # the origin, 2.6 m up
        self.assertAlmostEqual(iso["axis"][1][0], 8.6603, places=3)             # 10 m to the east, seen at 30 degrees

    def test_the_3d_dxf_has_an_axis_and_faces_per_solid(self):
        import ezdxf
        items = solid.solids(sheet(lines=[TRAY, CONDUIT]), "E1")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "raceways_3d.dxf"
            self.assertEqual(solid.write_dxf_3d(items, path), [])
            msp = ezdxf.readfile(str(path)).modelspace()
            kinds = [e.dxftype() for e in msp]
            self.assertEqual(kinds.count("POLYLINE"), 2)
            self.assertEqual(kinds.count("3DFACE"), 12 + 3 * solid.core.PARAMS["solid"]["sides"])
            tray = next(e for e in msp if e.dxftype() == "POLYLINE")
            self.assertEqual([tuple(round(c, 3) for c in v.dxf.location) for v in tray.vertices], [(0.0, 0.0, 2.6), (10.0, 0.0, 2.6), (10.0, 5.0, 2.6)])


if __name__ == "__main__":
    unittest.main()
