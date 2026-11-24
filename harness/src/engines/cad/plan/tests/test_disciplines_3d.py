"""Every discipline of a building or a plant is drawn in 2D (the plan DXF) and in 3D (solids, scene, section) from its profile alone. Pure: no backend, no network."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_plan import core, dxfout, footprint, scene3d, solid   # noqa: E402

BUILDING_SERVICES = ("pci", "hvac", "sanitaria_cloacas", "sanitaria_pluvial", "sanitaria_agua", "gas", "mecanica")


def drawing(pid, level="L0"):
    """One of every kind of the discipline: the nodes in a row 2 m apart and every kind of line beside them."""
    prof = core.load_profile(pid)
    nodes = [{"id": f"n{i}", "kind": k["id"], "x": 20 * i, "y": 0} for i, k in enumerate(prof["nodos"])]
    lines = [{"id": f"l{i}", "kind": k["id"], "points": [[0, 30 + 20 * i], [100, 30 + 20 * i], [100, 80 + 20 * i]]} for i, k in enumerate(prof["tramos"])]
    return {"schema_version": "1.0", "plan": {"id": "T", "level": level, "origin": [0, 0], "scale": {"p1": [0, 0], "p2": [100, 0], "distance_m": 10}}, "discipline": pid, "nodes": nodes, "lines": lines}


class Profiles(unittest.TestCase):
    def test_the_disciplines_of_a_building_are_there(self):
        self.assertTrue(set(BUILDING_SERVICES) <= set(core.profiles()))

    def test_every_kind_has_a_body_to_draw(self):
        for pid in core.profiles():
            prof = core.load_profile(pid)
            for k in prof["tramos"] + prof["nodos"]:
                g = k["geom"]
                self.assertTrue(g["ancho_m"] > 0 and g["alto_m"] > 0, f"{pid}:{k['id']}")
                if k.get("vertical") and pid in BUILDING_SERVICES:           # a riser of the services stands a storey high until the person says its height (the plenum of the electrical profile asks for it)
                    self.assertGreater(g.get("altura_m", 0), 0, f"{pid}:{k['id']}")

    def test_kind_ids_tags_and_shortcuts_are_consistent(self):
        for pid in core.profiles():
            prof = core.load_profile(pid)
            ids = [k["id"] for k in prof["tramos"] + prof["nodos"]]
            self.assertEqual(len(ids), len(set(ids)), pid)
            self.assertTrue(set(prof["atajos_teclado"].values()) <= set(ids), pid)
            self.assertTrue(all(k["etiqueta"].get("es") and k["etiqueta"].get("en") for k in prof["tramos"] + prof["nodos"]), pid)

    def test_the_new_disciplines_carry_no_norm_and_no_calculation_of_their_own(self):
        for pid in ("sanitaria_pluvial", "sanitaria_agua", "gas"):
            prof = core.load_profile(pid)
            self.assertEqual((prof["normas"], prof["calculos"]), ([], ["longitud", "cantidad"]), pid)


class TwoDimensions(unittest.TestCase):
    def test_every_discipline_is_processed_and_written_as_a_plan_dxf(self):
        import ezdxf
        import epc_dxf
        for pid in BUILDING_SERVICES:
            doc = drawing(pid)
            result = core.process(doc)
            self.assertEqual(len([n for n in result["nodes"] if n.get("placed", True)]), len(doc["nodes"]), pid)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / f"{pid}.dxf"
                self.assertEqual(dxfout.write_dxf(result, path), [], pid)
                layers = {e.dxf.layer for e in ezdxf.readfile(str(path)).modelspace()}
                wanted = {epc_dxf.name("plan." + k["capa_dxf"]) for k in core.load_profile(pid)["tramos"] + core.load_profile(pid)["nodos"]}
                self.assertTrue(wanted <= layers, f"{pid}: {sorted(wanted - layers)}")


class ThreeDimensions(unittest.TestCase):
    def test_every_element_of_every_discipline_has_a_solid(self):
        for pid in BUILDING_SERVICES:
            doc = drawing(pid)
            items = solid.solids(doc, pid)
            self.assertEqual(len(items), len(doc["nodes"]) + len(doc["lines"]), pid)
            for s in items:
                m = solid.mesh(s)
                self.assertTrue(m["vertices"] and m["faces"], f"{pid}:{s['id']}")

    def test_pipes_are_round_and_ducts_gutters_racks_and_shafts_rectangular(self):
        def sections(pid):
            return {s["kind"]: s["section"] for s in solid.solids(drawing(pid), pid) if s["shape"] == "run"}
        self.assertEqual(sections("sanitaria_pluvial"), {"CP": "round", "CN": "rect", "BP": "round"})
        self.assertEqual({k: v for k, v in sections("hvac").items() if k in ("DA", "DR", "AH", "TF", "MD", "MH")}, {"DA": "rect", "DR": "rect", "AH": "round", "TF": "round", "MD": "rect", "MH": "round"})
        self.assertEqual({k: v for k, v in sections("mecanica").items() if k in ("TP", "PR", "AS")}, {"TP": "round", "PR": "rect", "AS": "rect"})
        self.assertEqual(set(sections("gas").values()) | set(sections("sanitaria_agua").values()) | set(sections("pci").values()), {"round"})

    def test_a_riser_stands_a_storey_high_and_the_person_can_change_it(self):
        doc = drawing("pci")
        riser = next(n for n in doc["nodes"] if n["kind"] == "MI")
        s = next(x for x in solid.solids(doc, "F1") if x["id"] == riser["id"])
        self.assertEqual((s["shape"], s["section"], s["width_m"], s["path"][0][2], s["path"][1][2]), ("run", "round", 0.1, 0.0, 3.0))
        riser["attrs"] = {"altura_m": 45.0, "ancho_m": 0.15}                    # the riser of a tall building
        s = next(x for x in solid.solids(doc, "F1") if x["id"] == riser["id"])
        self.assertEqual((s["width_m"], s["path"][1][2]), (0.15, 45.0))
        f = next(x for x in footprint.footprints(doc, "F1") if x["id"] == riser["id"])
        self.assertEqual((f["z0"], f["z1"]), (0.0, 45.0))                        # the clash detection sees the same body

    def test_the_services_of_a_building_make_one_scene_and_are_cut_together(self):
        scenes = [solid.scene(solid.solids(drawing(pid, level), f"{pid}-{level}")) for pid in BUILDING_SERVICES for level in ("L0", "L1")]
        whole = scene3d.merge(scenes)
        self.assertEqual({g["discipline"] for g in scene3d.groups(whole)}, set(BUILDING_SERVICES))
        self.assertTrue(all(g["color"] != core.PARAMS["scene"]["default_color"] for g in scene3d.groups(whole)))
        sec = scene3d.cut(whole, "x", 5.0, "+")                                 # across every horizontal run of both floors
        self.assertEqual({c["discipline"] for c in sec["cut"]}, set(BUILDING_SERVICES))
        water = sorted(c["level_m"] for c in sec["cut"] if c["layer"] == "AGU-TUBERIA")
        self.assertEqual(water, [2.6, 5.6])                                     # the cold water pipe of each storey, a storey (3 m) apart
        with tempfile.TemporaryDirectory() as tmp:
            n = scene3d.write_section_dxf(sec, Path(tmp) / "s.dxf")
            self.assertEqual(n["tags"], len(sec["cut"]))
            self.assertGreater(scene3d.write_dxf(whole, Path(tmp) / "m.dxf"), 0)


if __name__ == "__main__":
    unittest.main()
