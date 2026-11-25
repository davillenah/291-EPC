"""MIG-3Z: an optional stamp date makes the DXF bytes reproducible; without it the writer is the ezdxf default (clock and random GUIDs)."""
import datetime
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import ezdxf  # noqa: E402
from ezdxf.tools import juliandate  # noqa: E402

from epc_dxf import deliverable, roles, stamp  # noqa: E402

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="200mm" height="100mm" viewBox="0 0 200 100">
<rect id="papel" x="0" y="0" width="200" height="100" fill="#fff"/>
<g id="recuadro"><rect x="5" y="5" width="190" height="90" fill="none" stroke="#000" stroke-width="0.5"/></g>
<g id="dibujo">
<line data-layer="sld.diagram" x1="20" y1="20" x2="80" y2="20" stroke="#0000ff" stroke-width="0.25"/>
<text data-layer="sld.text" x="20" y="40" font-size="2.8" fill="#000000">hola</text>
</g></svg>"""

MIXED_ENTITIES = """
import sys
sys.path.insert(0, sys.argv[2])
from epc_dxf import stamp
s = stamp.parse("2026-03-04", "MIXED")
doc = stamp.new("R2010", s)
msp = doc.modelspace()
msp.add_line((0, 0), (1, 1))
msp.add_lwpolyline([(0, 0), (1, 0), (1, 1)])
msp.add_text("a")
msp.add_mtext("b")
msp.add_circle((0, 0), 1)
msp.add_hatch(color=7).paths.add_polyline_path([(0, 0), (1, 0), (1, 1)], is_closed=True)
blk = doc.blocks.new("B")
blk.add_attdef("T", (0, 0))
msp.add_blockref("B", (0, 0)).add_auto_attribs({"T": "x"})
stamp.save(doc, sys.argv[1], s)
"""


def header(path):
    """The header variables as written in the file (ezdxf itself resets `$TDCREATE` in memory when it loads a file)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    end = lines.index("ENDSEC")
    out, i = {}, 0
    while i < end:
        if lines[i].startswith("$"):
            name, value, i = lines[i].strip(), lines[i + 2].strip(), i + 3
            out[name] = float(value) if lines[i - 2].strip() == "40" else value
        else:
            i += 1
    return out


class TestStampValue(unittest.TestCase):
    def test_a_date_a_datetime_and_iso_text_are_the_same_moment(self):
        moments = {stamp.moment_of(v) for v in ("2026-03-04", datetime.date(2026, 3, 4), datetime.datetime(2026, 3, 4), "2026-03-04T00:00:00")}
        self.assertEqual(moments, {datetime.datetime(2026, 3, 4)})

    def test_a_time_zone_is_converted_to_utc(self):
        self.assertEqual(stamp.moment_of("2026-03-04T03:00:00+03:00"), datetime.datetime(2026, 3, 4))

    def test_no_date_is_no_stamp_and_a_bad_one_is_an_error(self):
        self.assertIsNone(stamp.parse(None))
        self.assertIsNone(stamp.moment_of(None))
        for bad in ("yesterday", 20260304, "2026-13-01"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                stamp.moment_of(bad)

    def test_the_guids_follow_the_date_and_the_seed_and_look_like_ezdxf_ones(self):
        one, same, other_seed, other_day = (stamp.parse("2026-03-04", "A"), stamp.parse("2026-03-04", "A"), stamp.parse("2026-03-04", "B"), stamp.parse("2026-03-05", "A"))
        self.assertEqual(one.guid("version"), same.guid("version"))
        self.assertEqual(len({one.guid("version"), other_seed.guid("version"), other_day.guid("version"), one.guid("fingerprint")}), 4)
        self.assertRegex(one.guid("version"), r"^\{[0-9A-F]{8}(-[0-9A-F]{4}){3}-[0-9A-F]{12}\}$")


class TestPinnedDocument(unittest.TestCase):
    def doc(self, s):
        doc = stamp.new("R2010", s)
        doc.modelspace().add_line((0, 0), (10, 5))
        return doc

    def test_two_documents_with_the_same_stamp_are_byte_identical(self):
        s = stamp.parse("2026-03-04", "SHEET-1")
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t, "a.dxf"), Path(t, "b.dxf")
            stamp.save(self.doc(s), a, s)
            stamp.save(self.doc(s), b, s)
            self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_the_header_carries_the_date_and_the_derived_guids(self):
        s = stamp.parse("2026-03-04", "SHEET-1")
        with tempfile.TemporaryDirectory() as t:
            path = Path(t, "a.dxf")
            stamp.save(self.doc(s), path, s)
            h = header(path)
            for var in ("$TDCREATE", "$TDUCREATE", "$TDUPDATE", "$TDUUPDATE"):
                self.assertAlmostEqual(h[var], juliandate(datetime.datetime(2026, 3, 4)), places=6, msg=var)
            self.assertEqual((h["$FINGERPRINTGUID"], h["$VERSIONGUID"]), (s.guid("fingerprint"), s.guid("version")))
            self.assertIn("2026-03-04", path.read_text(encoding="utf-8"))               # the ezdxf marker strings of the metadata dictionary

    def test_saving_again_keeps_the_pinned_values(self):
        s = stamp.parse("2026-03-04", "X")
        with tempfile.TemporaryDirectory() as t:
            path = Path(t, "a.dxf")
            stamp.save(self.doc(s), path, s)
            first = path.read_bytes()
            stamp.save(ezdxf.readfile(str(path)), path, s)                                  # the pipeline reads and writes the file several times
            self.assertEqual(path.read_bytes(), first)

    def test_another_seed_or_date_gives_another_file(self):
        with tempfile.TemporaryDirectory() as t:
            made = []
            for i, s in enumerate((stamp.parse("2026-03-04", "A"), stamp.parse("2026-03-04", "B"), stamp.parse("2026-03-05", "A"))):
                path = Path(t, f"{i}.dxf")
                stamp.save(self.doc(s), path, s)
                made.append(path.read_bytes())
            self.assertEqual(len(set(made)), 3)

    def test_the_order_of_the_class_records_does_not_depend_on_the_python_process(self):
        with tempfile.TemporaryDirectory() as t:
            script = Path(t, "mixed.py")
            script.write_text(MIXED_ENTITIES, encoding="utf-8")
            files = []
            for seed in ("1", "2", "3", "4", "5", "6"):
                out = Path(t, f"h{seed}.dxf")
                env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=os.pathsep.join(sys.path))
                run = subprocess.run([sys.executable, str(script), str(out), str(SRC)], env=env, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                files.append(out.read_bytes())
            self.assertEqual(len(set(files)), 1)


class TestDefaultUnchanged(unittest.TestCase):
    """Without a stamp the writer is `Doc.saveas`: the clock and random GUIDs of ezdxf."""

    def test_no_stamp_means_the_clock_and_random_guids(self):
        with tempfile.TemporaryDirectory() as t:
            heads = []
            for i in range(2):
                doc = stamp.new("R2010")
                doc.modelspace().add_line((0, 0), (1, 1))
                path = Path(t, f"{i}.dxf")
                stamp.save(doc, path)
                heads.append(header(path))
            now = juliandate(datetime.datetime.now())
            for h in heads:
                self.assertLess(abs(h["$TDUPDATE"] - now), 1.0 / 24)                     # written within the hour
            self.assertNotEqual(heads[0]["$VERSIONGUID"], heads[1]["$VERSIONGUID"])
            self.assertNotEqual(heads[0]["$FINGERPRINTGUID"], heads[1]["$FINGERPRINTGUID"])

    def test_converting_without_a_date_is_not_reproducible_and_with_a_date_it_is(self):
        with tempfile.TemporaryDirectory() as t:
            svg = Path(t, "HOJA.svg")
            svg.write_text(roles.tag_iram_sheet(SVG), encoding="utf-8")
            plain = []
            for i in range(2):
                done = deliverable.convert(svg, Path(t, f"plain{i}.dxf"))
                plain.append(Path(done["dxf"]).read_bytes())
            self.assertNotEqual(plain[0], plain[1])
            pinned = [Path(deliverable.convert(svg, Path(t, f"pinned{i}.dxf"), stamp_date="2026-03-04")["dxf"]).read_bytes() for i in range(2)]
            self.assertEqual(pinned[0], pinned[1])
            as_date = Path(deliverable.convert(svg, Path(t, "dt.dxf"), stamp_date=datetime.date(2026, 3, 4))["dxf"]).read_bytes()
            self.assertEqual(as_date, pinned[0])
            other = Path(deliverable.convert(svg, Path(t, "other.dxf"), stamp_date="2026-03-04", seed="OTHER")["dxf"]).read_bytes()
            self.assertNotEqual(other, pinned[0])

    def test_the_pinned_file_is_the_same_drawing(self):
        with tempfile.TemporaryDirectory() as t:
            svg = Path(t, "HOJA.svg")
            svg.write_text(roles.tag_iram_sheet(SVG), encoding="utf-8")
            plain = deliverable.convert(svg, Path(t, "plain.dxf"))
            pinned = deliverable.convert(svg, Path(t, "pinned.dxf"), stamp_date="2026-03-04")
            self.assertEqual(plain["layers"], pinned["layers"])
            self.assertEqual(plain["blocks"], pinned["blocks"])

    def test_finish_draft_accepts_the_stamp(self):
        with tempfile.TemporaryDirectory() as t:
            outs = []
            for i in range(2):
                doc = ezdxf.new("R2010")
                doc.modelspace().add_line((0, 0), (1, 1))
                path = Path(t, f"d{i}", "draft.dxf")
                deliverable.finish_draft(doc, path, stamp_date="2026-03-04")
                outs.append(path.read_bytes())
            self.assertEqual(outs[0], outs[1])


if __name__ == "__main__":
    unittest.main()
