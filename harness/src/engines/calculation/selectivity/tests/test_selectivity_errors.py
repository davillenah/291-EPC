"""The errors of the engine carry a code and a text in both languages (ADR-0039); `str(error)` stays Spanish as it was."""
import unittest

from epc_selectivity import aea_protection as P
from epc_selectivity.errors import SelectivityError


class Errors(unittest.TestCase):
    def test_an_unknown_type_has_a_code_and_both_texts(self):
        with self.assertRaises(SelectivityError) as cm:
            P.i2_convencional(16, "xyz")
        e = cm.exception
        self.assertEqual(e.code, "err_type_unknown")
        self.assertIn("xyz", e.en)
        self.assertIn("desconocido", e.es)
        self.assertEqual(str(e), e.es)
        self.assertIsInstance(e, ValueError)

    def test_a_non_positive_rated_current_is_refused(self):
        with self.assertRaises(SelectivityError) as cm:
            P.i2_convencional(0)
        self.assertEqual((cm.exception.code, cm.exception.en), ("err_rated_current", "In must be positive"))


if __name__ == "__main__":
    unittest.main()
