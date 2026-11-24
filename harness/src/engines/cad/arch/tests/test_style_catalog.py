"""The layers and pens of `epc_arch` are the `arch.*` roles of `harness/config/dxf/layers.json` (DRW-01 stage 1): the mapping from the catalog to the style is explicit and pinned here."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_arch.api import LAYERS_PATH, load_style, style_with   # noqa: E402


class TestStyleCatalog(unittest.TestCase):
    def test_the_catalog_file_is_found_and_has_the_arch_roles(self):
        roles = json.loads(LAYERS_PATH.read_text(encoding="utf-8-sig"))["layers"]
        self.assertEqual(len([r for r in roles if r.startswith("arch.")]), 17)

    def test_layers_and_pens_keep_the_values_they_had_in_the_style_file(self):
        st = load_style()
        self.assertEqual(st.pens, {"pen_050": 0.5, "pen_035": 0.35, "pen_025": 0.25, "pen_018": 0.18, "pen_013": 0.13})
        cut = st.layers["A-WALL-CUT"]
        self.assertEqual((cut.pen, cut.width, cut.linetype, cut.aci, cut.hex), ("pen_050", 0.5, "CONTINUOUS", 7, "#111111"))
        door = st.layers["A-DOOR-SWING"]
        self.assertEqual((door.pen, door.width, door.linetype, door.aci, door.hex), ("pen_018", 0.18, "DASHED", 250, "#333333"))
        for none in ("A-ROOM", "A-WIPEOUT"):
            self.assertEqual((st.layers[none].pen, st.layers[none].width), (None, 0.0))
        self.assertEqual(st.layers["A-GRID"].linetype, "CENTER")
        self.assertEqual(len(st.layers), 17)

    def test_an_organization_can_still_change_a_pen_by_name(self):
        st = style_with({"pens": {"pen_050": 0.6}, "layer_pens": {"A-DOOR": "pen_050"}})
        self.assertEqual(st.layers["A-WALL-CUT"].width, 0.6)
        self.assertEqual(st.layers["A-DOOR"].width, 0.6)


if __name__ == "__main__":
    unittest.main()
