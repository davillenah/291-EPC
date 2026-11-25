"""One symbol engine (SYM-07, first part): drawing engines ask `epc_symbols` for a symbol and never build a symbol file name.

* A file outside `epc_symbols` that writes the file-name pattern of the symbol libraries (`291_E_LV_SLD_IEC60617_`) or opens the library folder (`library_dir(`) is listed in `ALLOWED`.
  The list only shrinks: a new file fails, and a file that no longer does it must be taken off the list.
Run: python -m unittest discover -s harness/tests/architecture
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ENGINES = REPO / "harness" / "src" / "engines"
PATTERN = re.compile(r"291_E_LV_SLD_IEC60617_|\blibrary_dir\(")
# the generators keep the library folder for the catalogue rows and for a library given by path (SYM-02 pending: the rest of the SLD and MLD symbol handling)
ALLOWED = {
    "harness/src/engines/cad/draw/src/epc_draw/mld/mld_generator.py",
    "harness/src/engines/cad/draw/src/epc_draw/sld/sld_generator.py",
}


def offenders():
    found = set()
    for path in sorted(ENGINES.glob("*/*/src/epc_*/**/*.py")):
        rel = path.relative_to(REPO).as_posix()
        if "/src/epc_draw/symbols/" in rel or "/tests/" in rel:
            continue
        if PATTERN.search(path.read_text(encoding="utf-8-sig")):
            found.add(rel)
    return found


class SymbolAccess(unittest.TestCase):
    def test_no_new_file_builds_a_symbol_path(self):
        self.assertEqual(sorted(offenders() - ALLOWED), [], "ask epc_symbols (resolve, dxf_block, svg_fragment) instead of building a symbol file name")

    def test_the_allowed_list_only_shrinks(self):
        self.assertEqual(sorted(ALLOWED - offenders()), [], "these files no longer build a symbol path: take them off ALLOWED")


if __name__ == "__main__":
    unittest.main()
