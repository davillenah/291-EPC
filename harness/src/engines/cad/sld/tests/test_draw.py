"""The public function `epc_sld.draw` (DGM-16): it checks its input with bilingual coded errors and builds the generator environment from the contract, never from the process."""
import os
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINES = HERE.parents[2]
sys.path[:0] = [str(d) for d in sorted(ENGINES.glob("*/*/src"))]

from epc_sld import SldError, SldInput, draw  # noqa: E402
from epc_sld import sld_paginate  # noqa: E402
from unittest import mock  # noqa: E402


class TestDraw(unittest.TestCase):
    def files(self, t):
        names = {k: str(Path(t) / f"{k}.dat") for k in ("xlsx", "calc_json", "detail_json", "figures_json")}
        for p in names.values():
            Path(p).write_text("x")
        return names

    def test_the_input_is_frozen(self):
        with tempfile.TemporaryDirectory() as t:
            entrada = SldInput(**self.files(t))
            with self.assertRaises(FrozenInstanceError):
                entrada.formato = "A3"

    def test_a_missing_file_is_a_coded_error_in_two_languages(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.files(t)
            f["calc_json"] = str(Path(t) / "nope.json")
            with self.assertRaises(SldError) as ctx:
                draw(SldInput(**f), t, "SLD_X")
        self.assertEqual(ctx.exception.code, "err_sld_file_missing")
        self.assertIn("calc_json", ctx.exception.en)
        self.assertIn("no existe", ctx.exception.es)

    def test_an_empty_path_names_the_field(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.files(t)
            f["figures_json"] = ""
            with self.assertRaises(SldError) as ctx:
                draw(SldInput(**f), t, "SLD_X")
        self.assertEqual(ctx.exception.code, "err_sld_field_missing")

    def test_the_format_and_the_sheet_size_are_checked(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.files(t)
            with self.assertRaises(SldError) as a:
                draw(SldInput(formato="A4", **f), t, "SLD_X")
            with self.assertRaises(SldError) as b:
                draw(SldInput(**f), t, "SLD_X", maxl=0)
        self.assertEqual((a.exception.code, b.exception.code), ("err_sld_format_invalid", "err_sld_maxl_invalid"))

    def test_the_environment_comes_from_the_contract_only(self):
        with tempfile.TemporaryDirectory() as t:
            entrada = SldInput(titleblock_json=str(Path(t) / "tb.json"), **self.files(t))
            Path(entrada.titleblock_json).write_text("{}")
            with mock.patch.dict(os.environ, {"SLD_SUBSET": "LEAK"}), mock.patch.object(sld_paginate, "paginate", return_value=["SLD_X"]) as fake:
                self.assertEqual(draw(entrada, t, "SLD_X", 5, "2026-01-02"), ["SLD_X"])
        env = fake.call_args.kwargs["environ"]
        self.assertEqual(sorted(env), ["EPC_TITLEBLOCK_JSON", "SLD_CALC_DETAIL", "SLD_CALC_JSON", "SLD_FIGURES_JSON", "SLD_FORMATO"])
        self.assertEqual((fake.call_args.kwargs["maxl"], fake.call_args.kwargs["stamp_date"]), (5, "2026-01-02"))


if __name__ == "__main__":
    unittest.main()
