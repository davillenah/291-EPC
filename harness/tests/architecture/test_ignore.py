"""No client-data path is trackable: `git check-ignore` says ignored for project data and run results; the template, READMEs and platform files are not ignored."""
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def ignored(path: str) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO).returncode == 0


@unittest.skipUnless(shutil.which("git") and (REPO / ".git").exists(), "needs a git checkout")
class IgnoreRules(unittest.TestCase):
    def test_client_data_is_ignored(self):
        for p in ("projects/ACME-001/project_profile.json", "projects/ACME-001/inputs/plans/p.dxf", "projects/ACME-001/ssot/x.json",
                  "projects/ACME-001/deliverables/R0/mc.docx", "projects/ACME-001/audit/events.jsonl", "projects/ACME-001/runs/abc/log.txt",
                  "projects/ACME-001/README.md", "harness/knowledge/normative/AEA_90364_7_771.pdf", "harness/knowledge/normative/notes.md"):
            with self.subTest(path=p):
                self.assertTrue(ignored(p))

    def test_template_readmes_and_platform_files_are_not_ignored(self):
        for p in ("projects/README.md", "projects/_template/README.md", "projects/_template/inputs/README.md", "projects/_template/runs/README.md",
                  "harness/knowledge/normative/README.md", "harness/CLAUDE.md", "harness/src/platform/cli/README.md", "harness/config/normative/AR/README.md"):
            with self.subTest(path=p):
                self.assertFalse(ignored(p))

    def test_claudeignore_hides_the_same_client_folders(self):
        text = (REPO / ".claudeignore").read_text(encoding="utf-8")
        for needle in ("projects/*", "!projects/_template/", "harness/knowledge/normative/*", "local/"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
