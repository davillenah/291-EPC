"""aea_catalog: the formula catalog is built by introspection of the modules (also of those that moved in MIG-37b) and its command line prints it."""
import contextlib
import io
import json
import unittest

from epc_aea90364 import aea_catalog as CAT


def _printed(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        CAT.main(list(argv))
    return out.getvalue()


class TestCatalog(unittest.TestCase):
    def test_every_listed_module_gives_rows_with_its_own_functions(self):
        rows = CAT.catalogo()
        self.assertEqual({r["modulo"] for r in rows} - set(CAT.MODULES), set())
        for name in ("aea_demand", "aea_earthing", "aea_conductors", "aea_protection", "aea_tables"):      # modules that now live in other packages
            self.assertTrue([r for r in rows if r["modulo"] == name], name)

    def test_the_command_line_prints_json_markdown_search_and_help(self):
        data = json.loads(_printed("--json"))
        self.assertEqual(len(data["formulas"]), len(CAT.catalogo()))
        self.assertIn("## `aea_demand`", _printed("--md"))
        self.assertIn("aea_icc_decay", _printed("--buscar", "kappa"))
        self.assertIn("CAL-022", _printed())


if __name__ == "__main__":
    unittest.main()
