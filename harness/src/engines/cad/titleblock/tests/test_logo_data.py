"""ADR-0042: a logo may come as bytes; the sheet is the same as when the engine is given the file."""
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from epc_titleblock import Logo, render  # noqa: E402


def png(w=4, h=2):
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * w for _ in range(h))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def request(logo):
    return {"schema_version": "1.0", "logos": {"provider": logo}, "common": {}, "sheets": [{"name": "S1", "format": "A3", "fields": {}}]}


class LogoData(unittest.TestCase):
    def test_bytes_and_file_give_the_same_sheet(self):
        data = png()
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "provider-logo.png"
            path.write_bytes(data)
            from_file = render(request(str(path)))
        from_data = render(request(Logo("provider-logo.png", data)))
        self.assertEqual(from_data["sheets"][0]["svg"], from_file["sheets"][0]["svg"])
        self.assertIn("data:image/png;base64", from_data["sheets"][0]["svg"])
        self.assertEqual(from_data["warnings"], [])

    def test_a_missing_file_is_still_a_warning(self):
        out = render(request("/no/such/logo.png"))
        self.assertEqual(len(out["warnings"]), 1)


if __name__ == "__main__":
    unittest.main()
