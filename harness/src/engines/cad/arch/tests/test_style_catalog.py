"""The layers and pens of `epc_arch` are the `arch.*` roles of `harness/config/dxf/layers.json` (DRW-01 stage 1): the mapping from the catalog to the style is explicit and pinned here."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from epc_arch.api import LAYERS_PATH, load_style, style_with   # noqa: E402


class TestStyleCatalog(unittest.TestCase):
    def test_the_catalog_file_is_found_and_has_the_arch_roles(self):
        roles = json.loads(LAYERS_PATH.read_text(encoding="utf-8-sig"))["layers"]
        self.assertEqual(len([r for r in roles if r.startswith("arch.")]), 17)

    def test_layers_and_pens_keep_the_values_they_had_in_the_style_file(self):
        st = load_style()
        self.assertEqual(st.pens, {"pen_050": 0.5, "pen_035": 0.35, "pen_025": 0.25, "pen_018": 0.18, "pen_013": 0.13})
        cut = st.layers["291-A-WALL-FULL-N"]
        self.assertEqual((cut.pen, cut.width, cut.linetype, cut.aci, cut.hex), ("pen_050", 0.5, "CONTINUOUS", 7, "#111111"))
        door = st.layers["291-A-DOOR-FULL-N"]
        self.assertEqual((door.pen, door.width, door.linetype, door.aci, door.hex), ("pen_018", 0.18, "DASHED", 250, "#333333"))
        for none in ("291-A-AREA", "291-A-ANNO-NPLT"):
            self.assertEqual((st.layers[none].pen, st.layers[none].width), (None, 0.0))
        self.assertEqual(st.layers["291-A-GRID"].linetype, "CENTER")
        self.assertEqual(len(st.layers), 17)

    def test_an_organization_can_still_change_a_pen_by_name(self):
        st = style_with({"pens": {"pen_050": 0.6}, "layer_pens": {"291-A-DOOR-N": "pen_050"}})
        self.assertEqual(st.layers["291-A-WALL-FULL-N"].width, 0.6)
        self.assertEqual(st.layers["291-A-DOOR-N"].width, 0.6)

    def test_every_layer_of_the_dxf_has_a_description(self):
        import io
        import ezdxf
        import helpers
        from epc_arch import Options, recognize
        from epc_arch.api import plan_dxf
        doc = ezdxf.read(io.StringIO(plan_dxf(recognize(helpers.room_dxf(), "flat.dxf", Options()).architecture)))
        layers = [lay for lay in doc.layers if lay.dxf.name not in ("0", "Defpoints")]
        self.assertTrue(layers)
        self.assertEqual([lay.dxf.name for lay in layers if not lay.description], [])


if __name__ == "__main__":
    unittest.main()
