"""SYM-01: a library symbol is placed in a DXF as one block definition and one INSERT per use."""
import sys
import unittest
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from epc_dxf import symbol_blocks as SB  # noqa: E402
from epc_draw.symbols import registry as R  # noqa: E402


class TestSymbolBlocks(unittest.TestCase):
    def test_each_use_is_one_insert_and_the_definition_is_imported_once(self):
        doc = ezdxf.new("R2013")
        path, block = R.dxf_block("lv_mccb_basic", "sld")
        SB.insert(doc, path, block, (10, 20), scale=0.5, layer="0", attribs={"TAG": "-Q1"})
        ref = SB.insert(doc, path, block, (30, 20), scale=0.5)
        inserts = list(doc.modelspace().query("INSERT"))
        self.assertEqual([i.dxf.name for i in inserts], [block, block])
        self.assertEqual(ref.dxf.xscale, 0.5)
        self.assertEqual([b.name for b in doc.blocks if not b.name.startswith("*")], [block])

    def test_the_attributes_are_filled_by_tag_and_the_missing_ones_stay_empty(self):
        doc = ezdxf.new("R2013")
        path, block = R.dxf_block("lv_mccb_basic", "sld")
        tags = [a.dxf.tag for a in ezdxf.readfile(str(path)).blocks.get(block).query("ATTDEF")]
        self.assertTrue(tags)
        ref = SB.insert(doc, path, block, (0, 0), attribs={tags[0]: "X1"})
        self.assertEqual({a.dxf.tag: a.dxf.text for a in ref.attribs}[tags[0]], "X1")


if __name__ == "__main__":
    unittest.main()
