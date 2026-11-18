"""The CCPM schedule, the specification and project verifiers and the canvas export give what they gave when the refactoring started (golden/documents.json)."""
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import characterization as C   # noqa: E402

def _portable(x):
    """The golden file was recorded on Windows: the system temp folder of the error messages is replaced by `<tmp>` on both sides."""
    text = json.dumps(x, ensure_ascii=False)
    text = re.sub(r"(?:[A-Za-z]:)?(?:\\\\|/)[^\"]*?(?:\\\\|/)(no_such_\w+_folder_xyz)", r"<tmp>/\1", text)
    return json.loads(text)


GOLDEN = _portable(json.loads(C.GOLDEN.read_text(encoding="utf-8"))) if C.GOLDEN.is_file() else {}
CURRENT = _portable(C.all_results())


class TestDocumentsCharacterization(unittest.TestCase):
    def test_every_area_is_in_the_golden_file(self):
        self.assertEqual(sorted(GOLDEN), sorted(CURRENT))

    def test_ccpm(self):
        self.assertEqual(CURRENT["ccpm"], GOLDEN["ccpm"])

    def test_specification_verifier(self):
        self.assertEqual(CURRENT["specification"], GOLDEN["specification"])

    def test_project_verifier(self):
        self.assertEqual(CURRENT["project"], GOLDEN["project"])

    def test_canvas(self):
        self.assertEqual(CURRENT["canvas"], GOLDEN["canvas"])


if __name__ == "__main__":
    unittest.main()
