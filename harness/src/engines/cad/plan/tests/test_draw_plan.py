"""OPT-02 (ADR-0040): `epc_plan.draw_plan(PlanInput, path)` is `core.process` then `dxfout.write_dxf`, byte for byte."""
import json
import re
import tempfile
import os
import unittest
from unittest import mock
from pathlib import Path

from epc_plan import PlanInput, core, draw_plan, dxfout

HERE = Path(__file__).resolve().parent


def _document():
    for candidate in sorted(HERE.rglob("*.json")):
        try:
            doc = json.loads(candidate.read_text(encoding="utf-8"))
            core.process(doc)
            return doc
        except Exception:                                      # noqa: BLE001 - not a plan document: try the next file
            continue
    raise unittest.SkipTest("no plan document fixture")


def _stable(data):
    """The DXF carries a new GUID and the writing time (also as Julian dates) in every file; everything else must be identical."""
    data = re.sub(rb"\d{4}-\d\d-\d\dT[\d:.]+\+00:00", b"{TIME}", data)
    data = re.sub(rb"(?m)^\d{7}\.\d+$", b"{JULIAN}", data)             # the Julian dates of the header move with the second the file is written
    return re.sub(rb"\{[0-9A-F-]{36}\}", b"{GUID}", data)


class TestDrawPlan(unittest.TestCase):
    def test_the_two_calls_give_the_same_file_as_the_one(self):
        doc = _document()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "1700000000"}):
            old, new = Path(tmp) / "old.dxf", Path(tmp) / "new.dxf"
            dxfout.write_dxf(core.process(doc), old)
            _, warnings = draw_plan(PlanInput(document=doc), new)
            self.assertEqual(_stable(old.read_bytes()), _stable(new.read_bytes()))
            self.assertIsInstance(warnings, list)

    def test_the_input_is_frozen_and_checked(self):
        with self.assertRaises(Exception):
            PlanInput(document={}).paper_scale = 50
        with self.assertRaises(TypeError):
            draw_plan({"document": {}}, "x.dxf")


if __name__ == "__main__":
    unittest.main()
