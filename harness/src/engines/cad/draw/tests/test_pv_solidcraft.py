"""The 3D model of a PV plant as a SolidCraft script: parts defined once, plant as instances, materials from the equipment records, nothing invented, deterministic bytes."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from epc_draw.pv import solidcraft
from tests.test_pv_model3d import PLANT, geometry, records


def commands(made):
    return json.loads(made["bytes"])["commands"]


class TestPvSolidcraft(unittest.TestCase):
    def test_every_table_is_an_instance_of_a_part_defined_once(self):
        g = geometry()
        made = solidcraft.render(g, PLANT["result"], "PVT", parts=records())
        cmds = commands(made)
        kinds = [c["command"] for c in cmds]
        types = {(t["array"], t["modules"], t["width_m"]) for t in g["tables"]}
        self.assertEqual(sum(1 for c in cmds if c["command"] == "component.create" and c["params"]["name"].startswith("Table ")), len(types))
        self.assertEqual(kinds.count("occurrence.move") + sum(1 for c in cmds if c["command"] == "occurrence.copy" and c["params"]["component"].startswith("Table ")), len(g["tables"]))
        self.assertEqual(sum(1 for c in cmds if c["command"] == "solid.box" and c["params"]["body_name"].startswith("Laminate")), 1)       # one module part for one tilt
        modules = sum(t["modules"] for t in g["tables"])
        self.assertEqual(sum(1 for c in cmds if c["command"] == "occurrence.copy" and c["params"]["component"].startswith("Module")), sum(t["modules"] for t in {(t["array"], t["modules"], t["width_m"]): t for t in g["tables"]}.values()) - 1)
        self.assertGreater(modules, 0)

    def test_the_material_comes_from_the_datasheet_mass_and_a_part_without_one_is_pending(self):
        made = solidcraft.render(geometry(), PLANT["result"], "PVT", parts=records())
        cmds = commands(made)
        created = [c["params"] for c in cmds if c["command"] == "material.create"]
        self.assertTrue(created and all(p["density_g_cm3"] > 0 for p in created))
        self.assertTrue(any(c["command"] == "material.assign" for c in cmds))
        pending = [m for m in made["materials"] if m["status"] == "pending review"]
        self.assertTrue({"ground", "station"} <= {m["part"] for m in pending})
        bare = solidcraft.render(geometry(), PLANT["result"], "PVT")
        self.assertFalse(any(c["command"] == "material.create" for c in commands(bare)))

    def test_same_input_same_bytes_and_the_arguments_name_the_sc_and_the_step(self):
        a, b = solidcraft.render(geometry(), PLANT["result"], "PVT", parts=records()), solidcraft.render(copy.deepcopy(geometry()), PLANT["result"], "PVT", parts=records())
        self.assertEqual(a["bytes"], b["bytes"])
        self.assertEqual(solidcraft.run_arguments(a["file"], "PVT")[-5:-1], ["--save", "PVT_pv_model_3d.sc", "--out", "PVT_pv_model_3d.step"])
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(solidcraft.write(geometry(), PLANT["result"], tmp, "PVT")["script"].exists())

    def test_a_layout_without_tables_is_refused(self):
        g = geometry()
        g["tables"] = []
        with self.assertRaises(ValueError):
            solidcraft.render(g, PLANT["result"], "PVT")
