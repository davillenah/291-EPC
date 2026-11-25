"""The dynamic layers outside the NCS / AIA convention: `0-Logo-<Company>` per company of the project, and the catalog's `0-Viewport`."""
import re
import unittest

import ezdxf

from epc_draw.core import add_logo_layer, layers as L, logo_layer_name


class TestLogoLayers(unittest.TestCase):
    def test_the_name_is_the_company_without_spaces(self):
        self.assertEqual(logo_layer_name("Energy Sapiens"), "0-Logo-EnergySapiens")
        self.assertEqual(logo_layer_name("Ford"), "0-Logo-Ford")
        self.assertEqual(logo_layer_name("ACME S.A. 2"), "0-Logo-ACMESA2")
        with self.assertRaises(Exception):
            logo_layer_name(" -. ")

    def test_the_layer_has_a_description_in_the_document(self):
        doc = ezdxf.new("R2018")
        name = add_logo_layer(doc, "Energy Sapiens", "provider")
        self.assertIn(name, doc.layers)
        self.assertTrue(doc.layers.get(name).description)

    def test_the_viewport_layer_is_in_the_catalog_and_not_plotted(self):
        a = L.get("sheet.viewport")
        self.assertEqual(a["name"], "0-Viewport")
        self.assertFalse(a["plot"])
        self.assertTrue(re.match(r"^0-[A-Za-z]+(-[A-Za-z0-9]+)?$", a["name"]))


class TestSheetLayers(unittest.TestCase):
    """The converted sheet: logos on `0-Logo-<company>` and the viewport of the sheet on `0-Viewport` (owner rule, 2026-11-25)."""
    SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="5mm" viewBox="0 0 10 5"><rect width="10" height="5" fill="#00f"/></svg>'

    def sheet(self):
        from epc_draw.core import deliverable
        from epc_draw.titleblock import Logo, render
        result = render({"schema_version": "1.0", "common": {"empresa": "Energy Sapiens", "cliente": "Cliente Uno S.A."},
                         "logos": {"provider": Logo("p.svg", self.SVG.encode()), "client": Logo("c.svg", self.SVG.encode())},
                         "sheets": [{"name": "S1", "format": "A3", "fields": {}}]})
        out = deliverable.convert_bytes(result["sheets"][0]["svg"], stamp_date="2026-11-25")
        import io
        return out, ezdxf.read(io.StringIO(out["dxf"].decode("utf-8", "surrogateescape")))

    def test_each_logo_is_on_the_layer_of_its_company(self):
        out, _ = self.sheet()
        self.assertGreater(out["layers"]["0-Logo-EnergySapiens"], 0)
        self.assertGreater(out["layers"]["0-Logo-ClienteUnoSA"], 0)

    def test_the_viewport_helper_puts_the_viewport_of_the_sheet_on_its_layer(self):
        """The helper exists and is tested; it is not wired into the converted sheets yet: that changes the bytes of every sheet, so it waits for the owner (goldens)."""
        doc = ezdxf.new("R2018")
        L.add_sheet_viewport(doc, 420.0, 297.0)
        self.assertEqual(L.apply_viewport(doc, L.load()), "0-Viewport")
        found = [e.dxf.layer for layout in doc.layouts if layout.name != "Model" for e in layout if e.dxftype() == "VIEWPORT"]
        self.assertIn("0-Viewport", found)
        self.assertNotIn("sheet.viewport", [lay.dxf.name for lay in doc.layers])
        self.assertIsNone(L.apply_viewport(ezdxf.new("R2018"), L.load()))

    def test_a_sheet_without_company_names_keeps_its_logos_on_layer_0(self):
        from epc_draw.core import deliverable
        from epc_draw.titleblock import Logo, render
        result = render({"schema_version": "1.0", "common": {}, "logos": {"provider": Logo("p.svg", self.SVG.encode())},
                         "sheets": [{"name": "S1", "format": "A3", "fields": {}}]})
        out = deliverable.convert_bytes(result["sheets"][0]["svg"])
        self.assertFalse([name for name in out["layers"] if name.startswith("0-Logo-")])


if __name__ == "__main__":
    unittest.main()
