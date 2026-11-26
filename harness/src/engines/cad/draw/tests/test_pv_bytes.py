"""The PV drawings as bytes (ADR-0042): `render_pv` writes nothing, gives what `draw_pv` writes, and gives the same bytes on four threads."""
import io
import json
import tempfile
import unittest

import ezdxf
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from epc_draw.pv.draw import PvDrawInput, draw_pv, render_pv

PLANT = json.loads((Path(__file__).parent / "fixtures" / "pv_plant.json").read_text(encoding="utf-8"))


def entrada():
    return PvDrawInput(result=PLANT["result"], layout=PLANT["geometry"], language="en", stamp_date="2026-11-18")


class TestPvBytes(unittest.TestCase):
    def test_the_bytes_are_the_files_draw_pv_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            drafts, _ = draw_pv(entrada(), tmp, "PVT")
            made = render_pv(entrada(), "PVT")
            self.assertEqual(sorted(made), sorted(Path(p).name for p in drafts.values()))
            for path in drafts.values():
                self.assertEqual(made[Path(path).name], Path(path).read_bytes())

    def test_four_threads_give_the_same_bytes(self):
        once = render_pv(entrada(), "PVT")
        with ThreadPoolExecutor(4) as pool:
            for got in pool.map(lambda _: render_pv(entrada(), "PVT"), range(4)):
                self.assertEqual(got, once)

    def test_every_2d_drawing_has_its_viewport_on_the_viewport_layer(self):
        for file_name, data in render_pv(entrada(), "PVT").items():
            doc = ezdxf.read(io.StringIO(data.decode()))
            self.assertIn("0-Viewport", doc.layers, file_name)
            self.assertNotIn("sheet.viewport", doc.layers, file_name)
            self.assertTrue([e for e in doc.layout("Layout1") if e.dxf.layer == "0-Viewport"], file_name)

    def test_it_takes_a_pv_draw_input(self):
        with self.assertRaises(TypeError):
            render_pv({"result": {}}, "PVT")


if __name__ == "__main__":
    unittest.main()
