"""The workbook of tables: one sheet per table, valid and unique sheet names."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from epc_drawing.export import tables_xlsx   # noqa: E402


class SheetNames(unittest.TestCase):
    def test_forbidden_characters_length_and_repeats(self):
        self.assertEqual(tables_xlsx.sheet_name("a/b:c", []), "a_b_c")
        self.assertEqual(len(tables_xlsx.sheet_name("x" * 50, [])), 31)
        self.assertEqual(tables_xlsx.sheet_name("cables", ["cables"]), "cables~2")
        self.assertEqual(tables_xlsx.sheet_name("", []), "sheet")


class Workbook(unittest.TestCase):
    def test_a_sheet_per_table_with_its_columns_first(self):
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.xlsx"
            self.assertTrue(tables_xlsx.write_tables(path, [("one", ["a", "b"], [[1, 2], [3, 4]]), ("one", ["c"], [["x"]])]))
            book = load_workbook(path)
            self.assertEqual(book.sheetnames, ["one", "one~2"])
            self.assertEqual([[c.value for c in row] for row in book["one"].iter_rows()], [["a", "b"], [1, 2], [3, 4]])

    def test_without_tables_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.xlsx"
            self.assertFalse(tables_xlsx.write_tables(path, []))
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
