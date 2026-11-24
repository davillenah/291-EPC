"""A symbol the library does not have is drawn as a box with its name inside (owner rule, 2026-11-24)."""
import unittest

import epc_symbols
from epc_symbols import SymbolsError, UnknownSymbol, placeholder, resolve


class TestPlaceholder(unittest.TestCase):
    def test_a_box_with_the_name_centred_and_marked_provisional(self):
        p = placeholder("Vacuum breaker", width=30, height=20, text_height=2)
        self.assertTrue(p["provisional"])
        self.assertEqual((p["name"], p["size"], p["text_height"]), ("Vacuum breaker", (30.0, 20.0), 2.0))
        kinds = [e["type"] for e in p["entities"]]
        self.assertEqual(kinds, ["line"] * 4 + ["text"])
        self.assertEqual(p["entities"][-1]["at"], (15.0, 10.0))
        self.assertIn("<rect", p["svg"])
        self.assertIn("Vacuum breaker", p["svg"])

    def test_the_text_shrinks_when_the_name_does_not_fit_and_blanks_are_tidied(self):
        p = placeholder("  a   very long symbol name  ", width=10, height=10, text_height=5)
        self.assertEqual(p["name"], "a very long symbol name")
        self.assertLess(p["text_height"], 5)
        self.assertLessEqual(len("a very long symbol name") * 0.6 * p["text_height"], 10)

    def test_the_text_never_taller_than_the_box(self):
        self.assertLessEqual(placeholder("A", width=50, height=4, text_height=9)["text_height"], 3.6)

    def test_the_name_is_escaped_in_the_svg(self):
        self.assertIn("&lt;MV&gt; &amp; LV", placeholder("<MV> & LV", width=60, height=10, text_height=2)["svg"])

    def test_same_input_same_answer(self):
        self.assertEqual(placeholder("X", width=9, height=9, text_height=2), placeholder("X", width=9, height=9, text_height=2))

    def test_errors_have_a_code_and_two_languages(self):
        with self.assertRaises(SymbolsError) as c:
            placeholder("  ", width=1, height=1, text_height=1)
        self.assertEqual(c.exception.code, "err_placeholder_name")
        self.assertTrue(c.exception.es)
        with self.assertRaises(SymbolsError) as c:
            placeholder("X", width=0, height=1, text_height=1)
        self.assertEqual(c.exception.code, "err_placeholder_size")
        self.assertIn("width", c.exception.en)

    def test_resolve_still_refuses_a_missing_symbol(self):
        with self.assertRaises(UnknownSymbol):
            resolve("no_such_symbol")
        self.assertIn("placeholder", epc_symbols.__all__)


if __name__ == "__main__":
    unittest.main()
