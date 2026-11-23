"""OPT-02 (ADR-0040): `epc_mld.draw(MldInput, ...)` hands the input to `generate` unchanged."""
import sys
import unittest
from pathlib import Path
from unittest import mock

ENGINES = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ENGINES / g / a / "src") for g, a in (("cad", "mld"), ("cad", "sld"), ("calculation", "aea90364"), ("cad", "symbols"), ("cad", "titleblock"), ("cad", "dxf"))]

from epc_mld import MldInput, contract, draw   # noqa: E402


class TestDraw(unittest.TestCase):
    def test_the_input_reaches_generate_as_it_is(self):
        entrada = MldInput(data={"board": {}, "circuits": []}, calc={"datos": {}}, stamp_date="2026-03-04", titleblock_request={"x": 1})
        notes = []
        with mock.patch.object(contract, "generate", return_value=[{"name": "N"}]) as gen:
            made = draw(entrada, "out", "N", log=notes)
        self.assertEqual(made, [{"name": "N"}])
        args, kw = gen.call_args
        self.assertEqual((args[0], args[1], args[2], args[3]), ({"board": {}, "circuits": []}, {"datos": {}}, "out", "N"))
        self.assertEqual((kw["stamp_date"], kw["titleblock_request"], kw["log"], kw["lib"]), ("2026-03-04", {"x": 1}, notes, None))

    def test_the_input_is_frozen_and_checked(self):
        entrada = MldInput(data={}, calc={})
        with self.assertRaises(Exception):
            entrada.lib = "x"
        with self.assertRaises(TypeError):
            draw({"data": {}}, "out", "N")


if __name__ == "__main__":
    unittest.main()
