"""Every layer of a plan DXF is named in English by the NCS / AIA convention (`291-...`) or is `0-*`, and has a description (owner rule)."""
import re
import tempfile
import unittest
from pathlib import Path

import ezdxf

from epc_draw.plan import core, dxfout
from test_draw_plan import _document

NAME = re.compile(r"^(291-[A-Z]{1,2}(-[A-Z]{4}){1,3}(-[A-Z0-9])?|0-[A-Za-z]+(-[A-Za-z0-9]+)?)$")


class TestLayerNames(unittest.TestCase):
    def test_the_layers_of_the_plan_are_english_ncs_names_with_a_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.dxf"
            dxfout.write_dxf(core.process(_document()), path)
            layers = [lay for lay in ezdxf.readfile(str(path)).layers if lay.dxf.name not in ("0", "Defpoints")]
        self.assertTrue(layers)
        self.assertEqual([lay.dxf.name for lay in layers if not NAME.match(lay.dxf.name)], [])
        self.assertEqual([lay.dxf.name for lay in layers if not lay.description], [])


if __name__ == "__main__":
    unittest.main()
