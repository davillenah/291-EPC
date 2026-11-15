"""The 3D scene of a project and its outputs (epc_plan.scene3d): plain data in; an OBJ, a 3D DXF and sections through everything out. Pure: no backend, no network."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_plan import core, scene3d, solid   # noqa: E402
import test_solid as S                       # noqa: E402

BOX = {"vertices": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
       "faces": [[3, 2, 1, 0], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]}


def building():
    """A scene as `epc_arch.model3d.building_scene` gives it (the data only: this engine imports no other)."""
    wall = {"id": "PB:w1:1", "tag": "w1", "kind": "wall", "discipline": "arquitectura", "level": "PB", "layer": "A-WALL-CUT", "mesh": json.loads(json.dumps(BOX))}
    return {"schema_version": "1.0", "units": "m", "solids": [wall], "box": [[0, 0, 0], [1, 1, 1]]}


def services():
    return solid.scene(solid.solids(S.sheet(nodes=[S.BOARD], lines=[S.TRAY, S.CONDUIT]), "E1"))


class Scenes(unittest.TestCase):
    def test_the_building_and_the_services_become_one_scene(self):
        both = scene3d.merge([building(), services()])
        self.assertEqual(len(both["solids"]), 4)
        self.assertEqual(both["box"], [[-0.3, -2.025, 0.0], [10.15, 5.0, 2.65]])

    def test_the_groups_are_the_disciplines_and_their_layers(self):
        g = scene3d.groups(scene3d.merge([building(), services()]))
        self.assertEqual([(x["group"], x["solids"]) for x in g],
                         [("arquitectura / A-WALL-CUT", 1), ("electrica_BT / ELEC-TABLERO", 1), ("electrica_BT / ELEC-BANDEJA", 1), ("electrica_BT / ELEC-CANAL", 1)])
        self.assertTrue(all(re.fullmatch(r"#[0-9A-Fa-f]{6}", x["color"]) and 0 < x["opacity"] <= 1 for x in g))

    def test_what_is_not_a_scene_is_refused(self):
        for bad in ({}, {"schema_version": "1.0", "solids": [{"id": "a"}]},
                    {"schema_version": "1.0", "solids": [{"id": "a", "mesh": {"vertices": [[0, 0, 0]], "faces": [[0, 1, 2, 3]]}}]}):
            with self.assertRaises(core.PlanError):
                scene3d.check(bad)


class Sections(unittest.TestCase):
    """The tray runs 10 m along x at y = 0 and z = 2.6 (0.3 x 0.1 m), then 5 m along y at x = 10; the conduit runs along x at y = -2 (50 mm); the wall is the unit box."""

    def both(self):
        return scene3d.merge([building(), services()])

    def test_a_plane_across_the_runs_cuts_the_tray_as_its_rectangle_and_the_conduit_as_its_circle(self):
        sec = scene3d.cut(self.both(), "x", 5.0, "+")
        by_layer = {c["layer"]: c for c in sec["cut"]}
        self.assertEqual(sorted(by_layer), ["ELEC-BANDEJA", "ELEC-CANAL"])
        tray = by_layer["ELEC-BANDEJA"]["loops"][0]
        self.assertEqual((min(p[0] for p in tray), max(p[0] for p in tray), min(p[1] for p in tray), max(p[1] for p in tray)), (-0.15, 0.15, 2.55, 2.65))
        self.assertEqual(by_layer["ELEC-BANDEJA"]["level_m"], 2.6)
        pipe = by_layer["ELEC-CANAL"]["loops"][0]
        self.assertEqual(len(pipe), solid.core.PARAMS["solid"]["sides"])
        for u, z in pipe:
            self.assertAlmostEqual(((u - 2.0) ** 2 + (z - 2.6) ** 2) ** 0.5, 0.025, places=3)       # looking towards +x the right hand is -y: y = -2 is u = 2

    def test_the_building_is_cut_too(self):
        sec = scene3d.cut(self.both(), "x", 0.5, "+")
        wall = next(c for c in sec["cut"] if c["layer"] == "A-WALL-CUT")
        self.assertEqual(sorted(wall["loops"][0]), [[-1.0, 0.0], [-1.0, 1.0], [0.0, 0.0], [0.0, 1.0]])

    def test_what_is_beyond_is_seen_up_to_the_depth(self):
        near = scene3d.cut(self.both(), "x", 5.0, "+", depth_m=1.0)
        self.assertEqual(near["seen"], [])
        far = scene3d.cut(self.both(), "x", 5.0, "+")
        self.assertEqual(sorted(e["layer"] for e in far["seen"]), ["ELEC-BANDEJA", "ELEC-CANAL"])    # the stretch of tray that turns north at x = 10 and the far end of the conduit
        back = scene3d.cut(self.both(), "x", 5.0, "-")
        self.assertIn("A-WALL-CUT", [e["layer"] for e in back["seen"]])                                # looking back: the wall and the board

    def test_looking_the_other_way_mirrors_the_section(self):
        a, b = scene3d.cut(self.both(), "x", 5.0, "+"), scene3d.cut(self.both(), "x", 5.0, "-")
        self.assertEqual(sorted(c["centre"][0] for c in a["cut"]), sorted(-c["centre"][0] for c in b["cut"]))

    def test_a_plane_or_a_look_that_cannot_be(self):
        for args in (("z", 1.0, "+"), ("x", 1.0, "N"), ("x", "1", "+")):
            with self.assertRaises(core.PlanError):
                scene3d.cut(self.both(), *args)

    def test_the_section_dxf_has_the_outlines_the_tags_and_the_levels(self):
        import ezdxf
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "section.dxf"
            n = scene3d.write_section_dxf(scene3d.cut(self.both(), "x", 5.0, "+"), path)
            self.assertEqual((n["outlines"], n["tags"]), (2, 2))
            msp = list(ezdxf.readfile(str(path)).modelspace())
            texts = sorted(e.dxf.text for e in msp if e.dxftype() == "TEXT")
            self.assertTrue(all(t.endswith("+2.60") for t in texts), texts)
            self.assertEqual(sum(1 for e in msp if e.dxftype() == "HATCH"), 2)
            tray = next(e for e in msp if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "ELEC-BANDEJA")
            xs = [p[0] for p in tray.get_points("xy")]
            self.assertAlmostEqual(max(xs) - min(xs), 0.3, places=4)                               # real metres: the tray is 0.3 m wide


class Files(unittest.TestCase):
    def test_the_obj_has_every_vertex_and_face(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scene.obj"
            sc = scene3d.merge([building(), services()])
            n = scene3d.write_obj(sc, path)
            text = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(sum(1 for x in text if x.startswith("v ")), sum(len(s["mesh"]["vertices"]) for s in sc["solids"]))
            self.assertEqual((sum(1 for x in text if x.startswith("f ")), sum(1 for x in text if x.startswith("o "))), (n, 4))
            top = max(int(i) for x in text if x.startswith("f ") for i in x.split()[1:])
            self.assertEqual(top, sum(len(s["mesh"]["vertices"]) for s in sc["solids"]))               # the numbering runs through the whole file
            self.assertTrue(all(len(x.split()) in (4, 5) for x in text if x.startswith("f ")))           # triangles and quads

    def test_the_dxf_has_a_face_per_face_on_the_layer_of_its_solid(self):
        import ezdxf
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scene.dxf"
            n = scene3d.write_dxf(scene3d.merge([building(), services()]), path)
            msp = list(ezdxf.readfile(str(path)).modelspace())
            self.assertEqual((len(msp), {e.dxftype() for e in msp}), (n, {"3DFACE"}))
            self.assertEqual(sum(1 for e in msp if e.dxf.layer == "A-WALL-CUT"), 6)


if __name__ == "__main__":
    unittest.main()
