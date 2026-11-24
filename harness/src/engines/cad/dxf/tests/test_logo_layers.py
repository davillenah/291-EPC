"""The dynamic layers outside the NCS / AIA convention: `0-Logo-<Company>` per company of the project, and the catalog's `0-Viewport`."""
import re
import unittest

import ezdxf

from epc_dxf import add_logo_layer, layers as L, logo_layer_name


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


if __name__ == "__main__":
    unittest.main()
