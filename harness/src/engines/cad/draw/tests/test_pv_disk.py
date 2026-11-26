"""The irradiation disk drawing: blocks, layers, viewport, palettes, both languages, same bytes every time."""
import io
import unittest
from concurrent.futures import ThreadPoolExecutor

import ezdxf

from epc_draw.core.errors import DxfError
from epc_draw.pv import disk


def sample(tilts=(0.0, 30.0, 60.0, 90.0), azimuths=(0.0, 90.0, 180.0, 270.0)):
    pct = [[100.0 - 0.3 * t - (0.2 * min(a, 360 - a) if t else 0.0) for a in azimuths] for t in tilts]
    return {"tilt_deg": list(tilts), "azimuth_deg": list(azimuths), "pct": pct, "best": {"tilt_deg": 30.0, "azimuth_deg": 0.0, "kwh_m2": 1500.0}, "hours": 8760}


def read(data):
    return ezdxf.read(io.StringIO(data.decode()))


class TestPvDisk(unittest.TestCase):
    def test_one_file_with_its_name_and_the_viewport(self):
        out = disk.render(sample(), "DEMO", "en")
        self.assertEqual(list(out), ["DEMO_irradiation_disk.dxf"])
        doc = read(out["DEMO_irradiation_disk.dxf"])
        self.assertIn("0-Viewport", doc.layers)
        self.assertTrue([e for e in doc.layout("Layout1") if e.dxf.layer == "0-Viewport"])

    def test_everything_is_a_block_inserted_in_the_model(self):
        doc = read(disk.render(sample(), "D", "en")["D_irradiation_disk.dxf"])
        names = {b.name for b in doc.blocks}
        self.assertTrue({"PVD-GRID", "PVD-LEGEND", "PVD-BEST"} <= names)
        self.assertTrue([n for n in names if n.startswith("PVD-BAND-")])
        inserted = {e.dxf.name for e in doc.modelspace() if e.dxftype() == "INSERT"}
        self.assertTrue({n for n in names if n.startswith("PVD-")} <= inserted)
        self.assertFalse([e for e in doc.modelspace() if e.dxftype() in ("HATCH", "LINE", "CIRCLE")])

    def test_the_layers_are_the_disk_roles_of_the_catalog(self):
        doc = read(disk.render(sample(), "D", "en")["D_irradiation_disk.dxf"])
        for name in ("291-WP-DISK-FILL", "291-WP-DISK-GRID", "291-WP-DISK-TEXT"):
            self.assertIn(name, doc.layers)
        self.assertNotIn("pv.DISK_FILL", doc.layers)

    def test_the_two_languages_and_the_two_palettes_differ(self):
        en, es = (disk.render(sample(), "D", lang)["D_irradiation_disk.dxf"] for lang in ("en", "es"))
        self.assertIn(b"IRRADIATION DISK", en)
        self.assertIn("DISCO DE IRRADIACI", es.decode())
        grey = disk.render(sample(), "D", "en", "grey")["D_irradiation_disk.dxf"]
        self.assertNotEqual(en, grey)

    def test_a_bad_palette_is_an_error(self):
        with self.assertRaises(DxfError) as ctx:
            disk.render(sample(), "D", "en", "pink")
        self.assertIn("pink", ctx.exception.en)
        self.assertIn("paleta", ctx.exception.es)

    def test_same_bytes_on_four_threads(self):
        once = disk.render(sample(), "D", "en", "color", "2026-11-26")
        with ThreadPoolExecutor(4) as pool:
            for got in pool.map(lambda _: disk.render(sample(), "D", "en", "color", "2026-11-26"), range(4)):
                self.assertEqual(got, once)

    def test_the_polar_position_north_up_east_right(self):
        self.assertEqual(disk.point(90, 0), (0.0, disk.RADIUS_MM))
        self.assertEqual(disk.point(90, 90), (disk.RADIUS_MM, 0.0))
        self.assertEqual(disk.point(0, 123), (0.0, 0.0))
        x, y = disk.point(45, 180)
        self.assertAlmostEqual(y, -disk.RADIUS_MM / 2)

    def test_bands_and_colours(self):
        self.assertEqual(disk.band_of(100.0), 95)
        self.assertEqual(disk.band_of(87.4), 85)
        self.assertEqual(disk.rgb(25, "grey", 25), (245, 245, 245))
        self.assertEqual(disk.rgb(95, "grey", 25), (20, 20, 20))
        self.assertEqual(disk.rgb(25, "color", 25), (0, 0, 140))
        self.assertEqual(disk.rgb(95, "color", 25), (150, 0, 0))


if __name__ == "__main__":
    unittest.main()
