"""A device of a circuit shows what its symbol offers about it: the label of its type (MCB, MCCB, KM...) and the data the standard solutions fill (the tag of the circuit, the poles, the curve, the breaking capacity, the rated current)."""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import characterization as C   # noqa: E402
from epc_drawing import board_design as B   # noqa: E402


def drawn() -> str:
    work = Path(tempfile.mkdtemp(prefix="labels_"))
    try:
        B.design(json.loads(json.dumps(C.SMALL)), work, "T1", None, None, 18, ("sld",))
        return (work / "out" / "SLD_T1.svg").read_text(encoding="utf-8")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def texts_of(svg: str, tag: str, idx: int) -> list:
    """The texts of the device at place `idx` of the chain of circuit `tag`."""
    m = re.search(rf'<g class="sym"[^>]*data-tag="{re.escape(tag)}" data-idx="{idx}".*?</g>\s*(?=<g class="sym"|<line|<g data-|</g>)', svg, re.S)
    assert m, (tag, idx)
    return [re.sub(r"<[^>]+>", "", t).strip() for t in re.findall(r"<text[^>]*>.*?</text>", m.group(0), re.S)]


class TestDeviceLabels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svg = drawn()

    def test_a_circuit_breaker_shows_its_type_its_tag_and_all_its_data(self):
        shown = texts_of(self.svg, "G-01-A", 0)
        self.assertIn("MCB", shown)                                                       # the label of the type, that the symbol carries outside its group
        self.assertIn("G-01-A", shown)                                                    # the tag of the circuit
        self.assertTrue(any(re.fullmatch(r"C\d+", x) for x in shown), shown)               # the curve and the rating
        self.assertTrue(any(re.fullmatch(r"[\d.]+ kA", x) for x in shown), shown)         # the breaking capacity
        self.assertTrue(any(re.fullmatch(r"[\d.]+ A", x) for x in shown), shown)          # the rated current

    def test_the_other_devices_show_their_type_too(self):
        for tag, idx, label in (("C-01", 0, "MCCB"), ("M-01", 0, None)):
            shown = texts_of(self.svg, tag, idx)
            if label:
                self.assertIn(label, shown)
        self.assertIn("RCCB", texts_of(self.svg, "G-01", 0))

    def test_what_the_diagram_draws_by_itself_has_no_type_label(self):
        self.assertEqual(self.svg.count(">BUS<"), 2)                                         # the bar is labelled once and the legend names it once: not at every node of the bar
        self.assertNotIn(">CABLE IN<", self.svg)


if __name__ == "__main__":
    unittest.main()
