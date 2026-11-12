import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from epc_standards import common  # noqa: E402


class JurisdictionsDir(unittest.TestCase):
    """Where the jurisdiction files are looked up (MIG-24h): a folder counts only when it holds a `<CC>/jurisdiction.json`."""

    def test_an_empty_or_missing_folder_falls_back_to_the_repository_pack(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(common.jurisdictions_dir(d), common.JURISDICTIONS)
            (Path(d) / "jurisdictions" / "AR").mkdir(parents=True)
            self.assertEqual(common.jurisdictions_dir(d), common.JURISDICTIONS)

    def test_a_test_tree_with_a_jurisdiction_file_wins(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "jurisdictions" / "ZZ").mkdir(parents=True)
            (Path(d) / "jurisdictions" / "ZZ" / "jurisdiction.json").write_text("{}", encoding="utf-8")
            self.assertEqual(common.jurisdictions_dir(d), Path(d) / "jurisdictions")

    def test_the_engine_folder_is_where_the_engines_live(self):
        self.assertEqual(common.ENGINE, common.WORKSPACE / "harness" / "src" / "engines")
        self.assertEqual(common.pack_dir(common.ENGINE, "rules"), common.ENGINE / "validation" / "rules")


if __name__ == "__main__":
    unittest.main()
