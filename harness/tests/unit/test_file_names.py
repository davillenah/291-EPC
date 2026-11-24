"""The file-name convention guard (check_file_names.py): what it flags and what it lets through."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "ci"))
import check_file_names as C  # noqa: E402


class FileNames(unittest.TestCase):
    def test_kebab_and_capitals_in_data_files_are_flagged(self):
        bad = C.offenders(["a/my-file.json", "a/Other.py", "b/good_name.json", "b/__init__.py", "b/x.schema.json"])
        self.assertEqual(bad, {"a/my-file.json", "a/Other.py"})

    def test_a_folder_mixing_separators_is_flagged(self):
        bad = C.offenders(["d/one_two.md", "d/three-four.md", "e/five_six.md", "e/seven_eight.md"])
        self.assertEqual(bad, {"d/one_two.md", "d/three-four.md"})

    def test_fixed_names_pass(self):
        self.assertEqual(C.offenders(["x/README.md", "x/.gitignore", "x/ADR-0001-some-title.md", "x/requirements-dev.txt"]), set())

    def test_the_repository_has_no_new_offender(self):
        legacy = set(__import__("json").loads(C.LEGACY.read_text()))
        self.assertEqual(C.offenders(C.tracked()) - legacy, set())
