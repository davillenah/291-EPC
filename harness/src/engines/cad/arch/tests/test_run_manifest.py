"""A run of the v2 command leaves a manifest that says what it was: engine version, hashes of the input, the params, the style and each output, and the options."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from epc_arch import __version__                                  # noqa: E402
from epc_arch.cli_v2 import main                                  # noqa: E402
import helpers                                                    # noqa: E402


class TestRunManifest(unittest.TestCase):
    def test_the_manifest_hashes_input_and_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "flat.dxf", Path(tmp) / "out"
            data = helpers.room_dxf()
            src.write_bytes(data)
            self.assertEqual(main([str(src), "--out", str(out), "--formats", "svg,dxf", "--sheet", "A4"]), 0)
            m = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(m["version"], __version__)
            self.assertEqual(m["input"]["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(m["options"]["sheet"], "A4")
            self.assertEqual({o["file"].rsplit(".", 1)[1] for o in m["outputs"]}, {"svg", "dxf"})
            for o in m["outputs"]:
                self.assertEqual(o["sha256"], hashlib.sha256((out / o["file"]).read_bytes()).hexdigest())
            for k in ("params_sha256", "style_sha256", "run_at"):
                self.assertTrue(m[k])

    def test_the_run_time_can_be_handed_in_so_the_manifest_repeats(self):
        from datetime import datetime, timezone
        from epc_arch.cli_v2 import _manifest
        import argparse
        a = argparse.Namespace(sheet="A4", scale=None, dpi=None, page=None, sheet_svg=None, field=[])
        moment = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "flat.dxf"
            src.write_bytes(b"x")
            first = _manifest(src, b"x", a, ["svg"], [], Path(tmp), now=moment)
            second = _manifest(src, b"x", a, ["svg"], [], Path(tmp), now=moment)
        self.assertEqual(first, second)
        self.assertEqual(first["run_at"], "2026-01-02T03:04:05+00:00")

    def test_an_unknown_format_is_refused(self):
        self.assertEqual(main(["x.dxf", "--formats", "gif"]), 1)


if __name__ == "__main__":
    unittest.main()
