"""Fixes found by the real simulation of 2026-11-15 (BACKLOG SIM)."""
import unittest
from pathlib import Path

from disciplines.electrical_lv.stages import output_stages as OS
from disciplines.electrical_lv.stages import package_stage as PS


class CatalogPathTests(unittest.TestCase):
    def test_relative_name_is_looked_up_in_the_repository_catalogs(self):
        self.assertTrue(Path(OS.catalog_path("manufacturers")).is_dir())

    def test_absolute_path_is_kept(self):
        p = str(Path(OS.REPO_CATALOGS / "manufacturers").resolve())
        self.assertEqual(OS.catalog_path(p), p)

    def test_unknown_name_is_left_as_given(self):
        self.assertEqual(OS.catalog_path("no_such_folder_xyz"), "no_such_folder_xyz")


class DeliverablesDedupTests(unittest.TestCase):
    def test_structured_document_with_rendered_files_is_listed_once(self):
        ctx = object()
        orig = (PS._drawings, PS._rendered, PS._documents)
        try:
            PS._drawings = lambda c: []
            PS._rendered = lambda c: [{"name": "calculation_memo_pdf"}, {"name": "calculation_memo_docx"}]
            PS._documents = lambda c: [{"name": "calculation_memo"}, {"name": "boq"}]
            self.assertEqual([d["name"] for d in PS.deliverables(ctx)], ["calculation_memo_pdf", "calculation_memo_docx", "boq"])
        finally:
            PS._drawings, PS._rendered, PS._documents = orig


class OpenFindingsTests(unittest.TestCase):
    class Store:
        def read_manifests(self):
            return [("a", {"superseded_by": "TR-002", "findings": [{"id": "F-1", "severity": "blocking"}]}),
                    ("b", {"superseded_by": None, "findings": [{"id": "F-2", "severity": "blocking"}, {"id": "F-3", "severity": "major"}]})]

    def test_only_the_manifests_in_force_count(self):
        from epc_platform.workflow.machine import open_findings
        self.assertEqual(open_findings(self.Store(), "blocking"), ["F-2"])
        self.assertEqual(open_findings(self.Store(), "major"), ["F-3"])


if __name__ == "__main__":
    unittest.main()
