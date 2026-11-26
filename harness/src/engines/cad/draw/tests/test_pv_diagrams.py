"""The PV drawings: the four drafts are written from the layout geometry and the yield result of the PV engine (a stored engine output), in English and Spanish, on the `pv.*` layer roles."""
import json
import tempfile
import unittest
from pathlib import Path

import ezdxf

from epc_draw.pv import diagrams as pv_diagrams

PLANT = json.loads((Path(__file__).parent / "fixtures" / "pv_plant.json").read_text(encoding="utf-8"))
NAMES = {"layout", "stringing", "cabling", "sld"}


class TestPvDiagrams(unittest.TestCase):
    def test_four_drafts_in_both_languages(self):
        with tempfile.TemporaryDirectory() as tmp:
            for language in ("en", "es"):
                paths = pv_diagrams.write_all(PLANT["geometry"], PLANT["result"], Path(tmp) / language, "PVT", language=language, stamp_date="2026-11-18")
                self.assertEqual(set(paths), {f"PVT_{k}" for k in NAMES})
                for path in paths.values():
                    self.assertGreater(Path(path).stat().st_size, 0)

    def test_the_plans_draw_on_the_pv_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = pv_diagrams.write_all(PLANT["geometry"], PLANT["result"], Path(tmp), "PVT", stamp_date="2026-11-18")
            used = {e.dxf.layer for e in ezdxf.readfile(str(paths["PVT_layout"])).modelspace()}
            self.assertTrue({"291-WC-PROP-N", "291-WS-MNTG-N"} <= used)
            sld = {e.dxf.layer for e in ezdxf.readfile(str(paths["PVT_sld"])).modelspace()}
            self.assertIn("291-WP-DIAG", sld)

    def test_the_tables_are_drawn_where_the_engine_put_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = pv_diagrams.write_all(PLANT["geometry"], PLANT["result"], Path(tmp), "PVT", stamp_date="2026-11-18")
            boxes = [e for e in ezdxf.readfile(str(paths["PVT_layout"])).modelspace() if e.dxf.layer == "291-WS-MNTG-N" and e.dxftype() == "LWPOLYLINE"]
            self.assertGreaterEqual(len(boxes), len(PLANT["geometry"]["tables"]))

    def test_each_inverter_shows_its_combiner_string_fuse_and_ac_protection_as_blocks(self):
        data = pv_diagrams.render_all(PLANT["geometry"], PLANT["result"], "PVT", "en", "2026-11-26")["PVT_sld.dxf"]
        import io
        doc = ezdxf.read(io.StringIO(data.decode("utf-8", "ignore")))
        used = {e.dxf.name for e in doc.modelspace().query("INSERT")}
        for part in ("pv_combiner_box", "fuse", "mccb_basic", "spd_varistor"):
            self.assertTrue(any(part in name for name in used), part)


if __name__ == "__main__":
    unittest.main()

