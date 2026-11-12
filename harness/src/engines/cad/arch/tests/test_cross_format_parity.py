"""The same plan, written as SVG, DXF and PNG by the truth generator (`scripts/planta_prueba.py`), is read as the same plan. What holds today is locked here; what does not (the other counts of a PNG) is
measured by `scripts/parity_check.py`."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE.parent / "scripts"))

import planta_prueba as gen                                       # noqa: E402
from epc_arch import Options, recognize                           # noqa: E402

KEYS = ("walls", "doors", "windows", "openings")


def _read(path: Path):
    a = recognize(path.read_bytes(), path.name, Options(background=False)).architecture
    return {**a.counts(), "rooms": len(a.rooms), "metres": bool(a.units_per_metre)}


class TestCrossFormatParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.root = Path(cls.dir.name)

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def files(self, pid: str, *kinds: str):
        p = gen.plano(pid)
        out = {}
        if "svg" in kinds:
            (self.root / f"{pid}.svg").write_text(gen.svg(pid, p), encoding="utf-8")
            out["svg"] = self.root / f"{pid}.svg"
        if "dxf" in kinds:
            gen.dxf(p, self.root / f"{pid}.dxf")
            out["dxf"] = self.root / f"{pid}.dxf"
        if "png" in kinds:
            gen.png(p, self.root / f"{pid}.png")
            out["png"] = self.root / f"{pid}.png"
        return out

    def test_svg_and_dxf_give_the_same_plan(self):
        for pid in ("p1", "p3"):
            f = self.files(pid, "svg", "dxf")
            self.assertEqual(_read(f["svg"]), _read(f["dxf"]), pid)

    def test_a_png_gives_the_counts_of_the_dxf_where_it_is_known_to_(self):
        for pid in ("p5",):                                                 # a PNG takes seconds to read: one plan
            f = self.files(pid, "dxf", "png")
            dxf, png = _read(f["dxf"]), _read(f["png"])
            for k in ("doors", "windows", "openings", "rooms", "metres"):
                self.assertEqual(png[k], dxf[k], f"{pid} {k}")


if __name__ == "__main__":
    unittest.main()
