"""harness/CLAUDE.md stays at 200 lines or fewer (PRD §14.1) and carries the owner rules, the language rule and the migration pointer."""
import unittest
from pathlib import Path

TEXT = (Path(__file__).resolve().parents[2] / "CLAUDE.md").read_text(encoding="utf-8")


class HarnessClaudeMd(unittest.TestCase):
    def test_at_most_200_lines(self):
        self.assertLessEqual(len(TEXT.splitlines()), 200)

    def test_carries_the_required_sections(self):
        for needle in ("No git writes", "No deletes", "`local/` is off limits", "never approve", "Everything new is written in English",
                       "ssot/", "deliverables/", "manifest"):
            with self.subTest(needle=needle):
                self.assertIn(needle, TEXT)


if __name__ == "__main__":
    unittest.main()
