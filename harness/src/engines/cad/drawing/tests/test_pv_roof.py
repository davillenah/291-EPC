"""The roof drawings: layout, stringing and cabling are written from the roof placement and the yield result of the PV engine (stored engine outputs), in English and Spanish, on the `pv.*` roof layers."""
import json
import tempfile
import unittest
from pathlib import Path

import ezdxf

from epc_drawing import pv_roof

ROOF = json.loads((Path(__file__).parent / "fixtures" / "pv_roof.json").read_text(encoding="utf-8"))
NAMES = {"roof_layout", "roof_stringing", "roof_cabling", "roof_sld"}


def layers_of(path):
    return [e.dxf.layer for e in ezdxf.readfile(str(path)).modelspace()]


class TestPvRoof(unittest.TestCase):
    def write(self, tmp, language="en"):
        return pv_roof.write_all(ROOF["roof"], ROOF["result"], Path(tmp) / language, "PVR", language=language, stamp_date="2026-11-19")

    def test_four_drafts_in_both_languages(self):
        with tempfile.TemporaryDirectory() as tmp:
            for language in ("en", "es"):
                paths = self.write(tmp, language)
                self.assertEqual(set(paths), {f"PVR_{k}" for k in NAMES})
                self.assertTrue(all(Path(p).stat().st_size > 0 for p in paths.values()))

    def test_the_language_changes_the_texts(self):
        with tempfile.TemporaryDirectory() as tmp:
            texts = {}
            for language in ("en", "es"):
                path = self.write(tmp, language)["PVR_roof_layout"]
                texts[language] = " ".join(e.dxf.text for e in ezdxf.readfile(str(path)).modelspace() if e.dxftype() == "TEXT")
            self.assertIn("PV ROOF LAYOUT", texts["en"])
            self.assertIn("IMPLANTACIÓN FOTOVOLTAICA EN CUBIERTA", texts["es"])

    def test_every_placed_module_obstacle_and_plane_is_drawn(self):
        with tempfile.TemporaryDirectory() as tmp:
            used = layers_of(self.write(tmp)["PVR_roof_layout"])
        placed = sum(p["modules"] for p in ROOF["roof"]["planes"])
        self.assertEqual(used.count("PV-MODULOS"), placed)
        self.assertEqual(used.count("PV-CUBIERTA-OBST"), sum(len(p["obstacles"]) for p in ROOF["roof"]["planes"]))
        self.assertGreaterEqual(used.count("PV-CUBIERTA"), 2 * len(ROOF["roof"]["planes"]))      # outline and setback line of each plane

    def test_the_cabling_plan_has_a_raceway_and_a_drop_per_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            used = layers_of(self.write(tmp)["PVR_roof_cabling"])
        self.assertEqual(used.count("PV-CANALIZACION"), len(ROOF["roof"]["planes"]))
        self.assertEqual(used.count("PV-CABLE-CC"), sum(a["strings"]["strings"] for a in ROOF["result"]["arrays"]))

    def test_the_stringing_plan_colours_modules_by_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = ezdxf.readfile(str(self.write(tmp)["PVR_roof_stringing"]))
        colours = {e.dxf.color for e in doc.modelspace() if e.dxf.layer == "PV-MODULOS"}
        self.assertTrue(colours and 256 not in colours)


if __name__ == "__main__":
    unittest.main()


class TestRoofSld(unittest.TestCase):
    def test_the_single_line_has_one_inverter_per_array_unit_and_the_library_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pv_roof.write_all(ROOF["roof"], ROOF["result"], Path(tmp), "PVR", stamp_date="2026-11-21")["PVR_roof_sld"]
            doc = ezdxf.readfile(str(path))
            inserts = [e for e in doc.modelspace() if e.dxftype() == "INSERT"]
            texts = " ".join(e.dxf.text for e in doc.modelspace() if e.dxftype() == "TEXT")
        names = [e.dxf.name.split("IEC60617_")[-1] for e in inserts]
        units = sum(int(a["inverters"]) for a in ROOF["result"]["arrays"])
        self.assertEqual(names.count("inverter"), units)
        self.assertEqual(names.count("pv_module"), units)
        self.assertEqual(names.count("dc_disconnect"), units)
        self.assertEqual(names.count("energy_meter_kwh"), len(ROOF["result"]["arrays"]))
        for a in ROOF["result"]["arrays"]:
            self.assertIn(f"{a['id']}-INV1", texts)
