"""Read-only verification of a DXF drawing: each rule finds its case, a clean drawing is clean, rules can be switched off, nothing is written."""
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import ezdxf  # noqa: E402

import epc_dxf  # noqa: E402
from epc_draw.core import DxfError, verify  # noqa: E402
from epc_draw.core import verification  # noqa: E402


def document():
    doc = ezdxf.new("R2018")
    doc.layers.add("A")
    return doc


def rules_of(result):
    return sorted(f["rule"] for f in result["findings"])


class RuleTests(unittest.TestCase):
    def test_a_clean_drawing_is_clean(self):
        doc = document()
        doc.modelspace().add_line((0, 0), (10, 0), dxfattribs={"layer": "A"})
        doc.modelspace().add_text("ok", dxfattribs={"layer": "A"})
        result = verify(doc, min_length=0.8)
        self.assertTrue(result["ok"])
        self.assertEqual((result["findings"], sum(result["counts"].values())), ([], 0))

    def test_zero_length_and_tiny_lines(self):
        doc = document()
        msp = doc.modelspace()
        msp.add_line((0, 0), (0, 0), dxfattribs={"layer": "A"})
        msp.add_line((0, 0), (0.5, 0), dxfattribs={"layer": "A"})
        msp.add_line((0, 0), (0.8, 0), dxfattribs={"layer": "A"})
        result = verify(doc, min_length=0.8)
        self.assertEqual(rules_of(result), ["tiny-line", "zero-length"])
        self.assertFalse(result["ok"])
        tiny = next(f for f in result["findings"] if f["rule"] == "tiny-line")
        self.assertIn("0.5", tiny["text"]["en"])
        self.assertTrue(tiny["text"]["es"])

    def test_duplicate_lines_in_either_direction(self):
        doc = document()
        msp = doc.modelspace()
        msp.add_line((0, 0), (5, 5), dxfattribs={"layer": "A"})
        msp.add_line((5, 5), (0, 0), dxfattribs={"layer": "A"})
        msp.add_line((0, 0), (5, 5), dxfattribs={"layer": "0"})
        result = verify(doc, min_length=0.8)
        self.assertEqual(result["counts"]["duplicate-line"], 1)
        self.assertTrue(result["ok"])

    def test_undefined_layer(self):
        doc = document()
        doc.modelspace().add_line((0, 0), (5, 0), dxfattribs={"layer": "NOPE"})
        result = verify(doc, min_length=0.8)
        self.assertEqual(rules_of(result), ["undefined-layer"])
        self.assertFalse(result["ok"])

    def test_undefined_block(self):
        doc = document()
        doc.modelspace().add_blockref("MISSING", (0, 0), dxfattribs={"layer": "A"})
        doc.blocks.new("DEFINED")
        doc.modelspace().add_blockref("DEFINED", (0, 0), dxfattribs={"layer": "A"})
        result = verify(doc, min_length=0.8)
        self.assertEqual(rules_of(result), ["undefined-block"])
        self.assertIn("MISSING", result["findings"][0]["text"]["en"])

    def test_empty_texts(self):
        doc = document()
        msp = doc.modelspace()
        msp.add_text(" ", dxfattribs={"layer": "A"})
        msp.add_mtext("", dxfattribs={"layer": "A"})
        msp.add_mtext("body", dxfattribs={"layer": "A"})
        self.assertEqual(rules_of(verify(doc, min_length=0.8)), ["empty-text", "empty-text"])

    def test_blocks_and_layouts_are_checked(self):
        doc = document()
        doc.blocks.new("LOGO").add_line((0, 0), (0.1, 0), dxfattribs={"layer": "A"})
        doc.layout("Layout1").add_line((0, 0), (0.1, 0), dxfattribs={"layer": "A"})
        wheres = sorted(f["where"] for f in verify(doc, min_length=0.8)["findings"])
        self.assertEqual(wheres, ["Layout1", "block LOGO"])


class OptionTests(unittest.TestCase):
    def test_off_switches_a_rule_out(self):
        doc = document()
        doc.modelspace().add_line((0, 0), (0.1, 0), dxfattribs={"layer": "A"})
        result = verify(doc, min_length=0.8, off=("tiny-line",))
        self.assertNotIn("tiny-line", result["rules"])
        self.assertEqual(result["findings"], [])

    def test_unknown_rule_and_bad_min_length(self):
        doc = document()
        with self.assertRaises(DxfError) as ctx:
            verify(doc, min_length=0.8, off=("nope",))
        self.assertEqual(ctx.exception.code, "err_verify_unknown_rule")
        for bad in (None, 0, -1, "1", True, float("nan")):
            with self.assertRaises(DxfError) as ctx:
                verify(doc, min_length=bad)
            self.assertEqual(ctx.exception.code, "err_verify_min_length")
            self.assertTrue(ctx.exception.en and ctx.exception.es)

    def test_findings_are_capped_but_counts_are_exact(self):
        doc = document()
        for n in range(verification.MAX_PER_RULE + 5):
            doc.modelspace().add_line((n, 0), (n, 0), dxfattribs={"layer": "A"})
        result = verify(doc, min_length=0.8)
        self.assertEqual(result["counts"]["zero-length"], verification.MAX_PER_RULE + 5)
        self.assertEqual(len(result["findings"]), verification.MAX_PER_RULE)
        self.assertEqual(result["truncated"], ["zero-length"])

    def test_a_file_path_is_read_and_nothing_is_written(self):
        doc = document()
        doc.modelspace().add_line((0, 0), (0.1, 0), dxfattribs={"layer": "A"})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.dxf"
            doc.saveas(str(path))
            before = path.read_bytes()
            result = verify(path, min_length=0.8)
            self.assertEqual(rules_of(result), ["tiny-line"])
            self.assertEqual(verify(str(path), min_length=0.8)["counts"], result["counts"])
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["t.dxf"])

    def test_deterministic_and_public(self):
        doc = document()
        doc.modelspace().add_line((0, 0), (0.1, 0), dxfattribs={"layer": "A"})
        self.assertEqual(verify(doc, min_length=0.8), verify(doc, min_length=0.8))
        self.assertIs(epc_dxf.verify, verify)
        self.assertEqual(set(verification.RULES), {"zero-length", "tiny-line", "duplicate-line", "undefined-layer", "undefined-block", "empty-text"})


if __name__ == "__main__":
    unittest.main()
