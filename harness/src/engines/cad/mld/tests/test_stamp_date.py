"""MIG-3Z: the multi-line generator takes an optional drawing date (title block issue date and DXF stamps); without it, today's date."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ENGINES = Path(__file__).resolve().parents[3]                # harness/src/engines: one folder per group (cad, calculation, ...)
sys.path[:0] = [str(ENGINES / g / a / "src") for g, a in (("cad", "mld"), ("cad", "sld"), ("calculation", "aea90364"), ("cad", "symbols"), ("cad", "titleblock"), ("cad", "dxf"))]

from epc_mld import mld_generator as M   # noqa: E402


class TestDxfStamp(unittest.TestCase):
    def test_the_date_and_the_sheet_name_as_seed_reach_the_dxf_service(self):
        with mock.patch("epc_dxf.deliverable.convert", return_value={"dxf": "x.dxf", "messages": []}) as convert:
            M.Generator.to_dxf(Path("S.svg"), "", Path("."), "MLD_T1", "2026-03-04")
        self.assertEqual((convert.call_args.kwargs["stamp_date"], convert.call_args.kwargs["seed"]), ("2026-03-04", "MLD_T1"))

    def test_without_a_date_the_service_gets_none(self):
        with mock.patch("epc_dxf.deliverable.convert", return_value={"dxf": "x.dxf", "messages": []}) as convert:
            M.Generator.to_dxf(Path("S.svg"), "", Path("."), "MLD_T1")
        self.assertIsNone(convert.call_args.kwargs["stamp_date"])


class TestGenerateOption(unittest.TestCase):
    def date_set_on_generator(self, env, **kw):
        made = mock.MagicMock()
        made.build.return_value = []
        with mock.patch.object(M, "Generator", return_value=made), mock.patch.dict(os.environ, env):
            if "EPC_STAMP_DATE" not in env:
                os.environ.pop("EPC_STAMP_DATE", None)
            M.generate({"board": {}, "circuits": []}, {"datos": {}}, ".", "N", **kw)
        return made.stamp_date

    def test_the_option_is_set_on_the_generator(self):
        self.assertEqual(self.date_set_on_generator({}, stamp_date="2026-03-04"), "2026-03-04")

    def test_the_environment_variable_is_the_fallback_and_nothing_means_none(self):
        self.assertEqual(self.date_set_on_generator({"EPC_STAMP_DATE": "2026-03-05"}), "2026-03-05")
        self.assertIsNone(self.date_set_on_generator({}))

    def test_a_new_generator_has_no_date(self):
        self.assertIsNone(M.Generator({"board": {}, "circuits": []}, {"datos": {}}, lib="x").stamp_date)


if __name__ == "__main__":
    unittest.main()
