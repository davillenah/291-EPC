"""The PRD copy in harness/docs/prsad/ exists, and the governance and roadmap documents exist."""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
COPY = REPO / "harness" / "docs" / "prsad" / "PRD.md"


class PrdCopy(unittest.TestCase):
    def test_prd_exists(self):
        self.assertTrue(COPY.is_file())

    def test_governance_and_roadmap_files_exist(self):
        for rel in ("docs/governance/RACI.md", "docs/governance/approvals.md", "docs/governance/segregation_of_duties.md",
                    "docs/governance/change_policy.md", "roadmap/phase_1.md", "roadmap/phase_2.md", "roadmap/phase_3.md"):
            with self.subTest(file=rel):
                self.assertTrue((REPO / "harness" / rel).is_file())

    def test_phase_1_is_low_voltage_only(self):
        self.assertIn("Low voltage only", (REPO / "harness" / "roadmap" / "phase_1.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
