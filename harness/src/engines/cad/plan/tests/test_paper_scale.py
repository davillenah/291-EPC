"""The symbols and the text of a plan are sized for the scale of the sheet it is printed at: the same on paper (mm) at every scale."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import ezdxf   # noqa: E402
from epc_dxf import textstyle   # noqa: E402
from epc_plan import core, dxfout   # noqa: E402
from test_dxf_turn import drawing   # noqa: E402


def written(paper_scale=None):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.dxf"
        dxfout.write_dxf(core.process(drawing({})), path, paper_scale=paper_scale)
        doc = ezdxf.readfile(path)
        block = doc.blocks.get("SYM_LUMINARIA")
        radius = max(e.dxf.radius for e in block if e.dxftype() == "CIRCLE")
        height = [a.dxf.height for a in block if a.dxftype() == "ATTDEF"][0]
        return 2 * radius, height


class TestPaperScale(unittest.TestCase):
    def test_the_symbol_and_the_text_are_the_paper_size_at_the_scale_of_the_sheet(self):
        look = textstyle.load()["heights"]
        for n in (20, 50, 100, 200):
            diameter, height = written(n)
            self.assertAlmostEqual(diameter, look["plan_symbol_mm"] * n / 1000.0, places=6)
            self.assertAlmostEqual(height, look["plan_text_mm"] * n / 1000.0, places=6)

    def test_the_symbol_keeps_its_proportion_to_the_building_at_every_scale(self):
        small, big = written(50)[0], written(100)[0]
        self.assertAlmostEqual(big / small, 2.0, places=6)

    def test_without_the_scale_the_real_sizes_stay(self):
        diameter, height = written(None)
        self.assertAlmostEqual(diameter, 0.6, places=6)
        self.assertAlmostEqual(height, textstyle.load()["heights"]["plan_text_m"], places=6)


if __name__ == "__main__":
    unittest.main()
