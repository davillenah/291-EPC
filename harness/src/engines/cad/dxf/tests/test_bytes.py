"""ADR-0042: the deliverable is made in memory and comes back as bytes; the bytes are the ones the file call writes, and nothing is left beside the file."""
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from epc_dxf import deliverable  # noqa: E402
from test_deterministic import SVG  # noqa: E402


class DeliverableBytes(unittest.TestCase):
    def test_the_bytes_are_the_file_the_path_call_writes(self):
        with tempfile.TemporaryDirectory() as t:
            svg = Path(t) / "S.svg"
            svg.write_text(SVG, encoding="utf-8")
            made = deliverable.convert(svg, stamp_date="2026-03-04")
            data = deliverable.convert_bytes(SVG, stamp_date="2026-03-04", seed="S")
            self.assertEqual(data["dxf"], Path(made["dxf"]).read_bytes())
            self.assertEqual((data["layers"], data["blocks"]), (made["layers"], made["blocks"]))
            self.assertEqual(sorted(p.name for p in Path(t).iterdir()), ["S.dxf", "S.svg"])

    def test_two_calls_give_the_same_bytes(self):
        a = deliverable.convert_bytes(SVG, stamp_date="2026-03-04", seed="S")["dxf"]
        self.assertEqual(a, deliverable.convert_bytes(SVG, stamp_date="2026-03-04", seed="S")["dxf"])

    def test_a_draft_comes_back_as_the_bytes_the_path_call_writes(self):
        import ezdxf
        def draft():
            doc = ezdxf.new("R2018", setup=False)
            doc.modelspace().add_line((0, 0), (5, 5))
            return doc
        with tempfile.TemporaryDirectory() as t:
            made = deliverable.finish_draft(draft(), Path(t) / "D.dxf", None, "2026-03-04", "D")
            data = deliverable.finish_draft_bytes(draft(), None, "2026-03-04", "D")
            self.assertEqual(data["dxf"], Path(made["dxf"]).read_bytes())
            self.assertEqual((data["layers"], data["blocks"]), (made["layers"], made["blocks"]))


if __name__ == "__main__":
    unittest.main()
