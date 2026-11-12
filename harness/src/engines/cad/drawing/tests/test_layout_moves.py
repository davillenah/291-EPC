"""The circuits and the whole set of a single-line diagram can be moved by hand: the positions are given to the generator (`layout`), the SVG keeps each circuit in its own group and the DXF is drawn where they were left."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import characterization as C   # noqa: E402
from epc_drawing import board_design as B   # noqa: E402


def make(layout=None):
    data = json.loads(json.dumps(C.SMALL))
    if layout is not None:
        data["layout"] = layout
    work = Path(tempfile.mkdtemp(prefix="layout_"))
    try:
        B.design(data, work, "T1", None, None, 18, ("sld",))
        out = work / "out"
        return (out / "SLD_T1.svg").read_text(encoding="utf-8"), (out / "SLD_T1.dxf").read_text(encoding="utf-8", errors="replace")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def canon(dxf: str) -> list:
    """The drawing without what changes every run (dates, ids) and without the order of its table objects."""
    return sorted(C.normalize("a.dxf", dxf.encode("utf-8")).split(chr(10)))


def xs(dxf: str) -> list:
    """The X of every point (group code 10) of the drawing."""
    lines = [ln.strip() for ln in dxf.replace("\r\n", "\n").split("\n")]
    return [float(lines[i + 1]) for i in range(0, len(lines) - 1) if lines[i] == "10" and lines[i + 1].replace(".", "", 1).replace("-", "", 1).isdigit()]


class TestLayoutMoves(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_svg, cls.base_dxf = make()

    def test_each_circuit_and_the_whole_set_are_groups_of_the_svg(self):
        self.assertIn('<g data-block="all">', self.base_svg)
        for tag in ("C-01", "M-01", "G-01"):
            self.assertIn(f'data-circuit="{tag}"', self.base_svg)
        self.assertNotIn("transform=\"translate(0.00,0)\"", self.base_svg)                          # nothing is moved until somebody moves it

    def test_a_layout_of_zeros_changes_nothing_in_the_dxf(self):
        _, dxf = make({"all": [0, 0], "circuits": {"M-01": [0, 0]}})
        self.assertEqual(canon(dxf), canon(self.base_dxf))          # what changes every run (dates, ids) aside

    def test_a_moved_circuit_is_drawn_where_it_was_left(self):
        svg, dxf = make({"all": [0, 0], "circuits": {"M-01": [40, 0]}})
        self.assertIn('<g data-circuit="M-01" transform="translate(40.00,0)">', svg)
        self.assertNotEqual(canon(dxf), canon(self.base_dxf))
        self.assertGreater(max(xs(dxf)), max(xs(self.base_dxf)) - 1e-6)                          # something is further to the right than before

    def test_the_whole_set_moves_in_both_directions(self):
        svg, dxf = make({"all": [0, 15], "circuits": {}})
        self.assertIn('<g data-block="all" transform="translate(0.00,15.00)">', svg)
        self.assertNotEqual(canon(dxf), canon(self.base_dxf))

    def test_the_bus_reaches_a_circuit_moved_to_the_left_of_the_service(self):
        svg, _ = make({"all": [0, 0], "circuits": {"M-01": [-100, 0]}})
        self.assertIn('translate(-100.00,0)', svg)
        bar = [ln for ln in svg.split("\n") if 'stroke-width="0.7"' in ln and "<line" in ln][0]
        x1 = float(bar.split('x1="')[1].split('"')[0])
        self.assertLess(x1, 70.0)                                                           # the bar starts at the leftmost circuit, not at the service


if __name__ == "__main__":
    unittest.main()
