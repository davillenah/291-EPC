"""The fixes of the sim-01 simulation: automatic names, one layer naming, the review state in the manifest, the files of the five documents, the Spanish report."""
import tempfile
import unittest
from pathlib import Path

from disciplines.electrical_lv import naming, review_state
from disciplines.electrical_lv.stages import rendering


class AutomaticNames(unittest.TestCase):
    def test_numbers_pages_and_levels(self):
        floors = [{"id": "PB", "elevation_m": 0}, {"id": "P1", "elevation_m": 3.5}, {"id": "S1", "elevation_m": -3}]
        got = naming.automatic(["SLD_X_H1", "SLD_X_H2", "SLD_X_TABLA", "X_plan_P1", "X_plan_S1", "X_plan_PB_sheet", "calculation_memo_pdf", "calculation_memo_docx", "boq", "P_tables_xlsx", "X_model_3d", "X_section_A"], floors)
        self.assertEqual([got[f"SLD_X_{p}"]["page"] for p in ("H1", "H2", "TABLA")], [1, 2, 3])
        self.assertEqual({got[f"SLD_X_{p}"]["number"] for p in ("H1", "H2", "TABLA")}, {1})
        self.assertEqual((got["X_plan_P1"]["level"], got["X_plan_PB_sheet"]["level"], got["X_plan_S1"]["level"]), ("L01", "L00", "LS01"))
        self.assertEqual(got["calculation_memo_pdf"], got["calculation_memo_docx"])
        self.assertEqual((got["boq"]["type"], got["P_tables_xlsx"]["type"], got["X_section_A"]["type"]), ("LST", "TAB", "SEC"))
        for entry in got.values():
            self.assertEqual(naming.problems(entry), [])

    def test_a_flat_path_inside_the_kind_folder(self):
        entry = {"type": "SLD", "number": 1, "description": "single_line_diagram", "page": 2}
        self.assertEqual(naming.file_path("2026-ES-ABCD-0001", entry, ".dxf", in_type_folder=True), "2026-ES-ABCD-0001-E-LV-SLD-001_single_line_diagram_P02.dxf")


class LayerNames(unittest.TestCase):
    def test_one_convention(self):
        from epc_dxf import style_unify as U
        self.assertEqual([U.new_layer_name(n) for n in ("291-A-WALL-FULL-N", "291-E-LITE-EQPM-N", "291-E-POWR-WALL-N", "291-E-ANNO-NPLT", "0-Titleblock", "291-E-DIAG-TEXT", "291-A-AREA", "0", "ELEC-X")],
                         ["291-A-WALL-FULL-N", "E-LIGHT", "E-SOCKET", "E-NODE", "0-Titleblock", "E-TEXT", "291-A-AREA", "0", "E-X"])

    def test_a_file_is_rewritten_with_the_new_names_and_one_typeface(self):
        import ezdxf
        from epc_dxf import style_unify as U
        doc = ezdxf.new("R2010")
        doc.layers.add("291-E-LITE-EQPM-N")
        doc.styles.add("OTRO", font="OpenSans-Regular.ttf")
        doc.modelspace().add_line((0, 0), (1, 1), dxfattribs={"layer": "291-E-LITE-EQPM-N"})
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "a.dxf"
            doc.saveas(path)
            self.assertEqual(U.unify(path), {"291-E-LITE-EQPM-N": "E-LIGHT"})
            out = ezdxf.readfile(path)
            self.assertEqual([e.dxf.layer for e in out.modelspace()], ["E-LIGHT"])
            self.assertEqual({s.dxf.font for s in out.styles}, {"arial.ttf"})


MANIFEST = {"transmittal": "TR-001", "mode": "edit", "review_status": "draft", "signed": None}


class ReviewState(unittest.TestCase):
    def test_states_follow_the_workflow(self):
        sub = review_state.reviewed(MANIFEST, "submit_for_review", "x", "d")
        self.assertEqual((sub["review_status"], sub["signed"]), ("for_review", None))
        app = review_state.reviewed(sub, "approve", "ing", "2026-01-01")
        self.assertEqual((app["review_status"], app["signed"]), ("approved", {"signer": "ing", "date": "2026-01-01"}))
        self.assertEqual(review_state.reviewed(app, "issue", "ing", "d")["review_status"], "issued")
        self.assertEqual(review_state.status_after("approve", {}), "approved_for_construction")
        self.assertIsNone(review_state.reviewed(MANIFEST, "record_corrections", "x", "d"))


class Documents(unittest.TestCase):
    def test_findings_line(self):
        f = [{"id": "F-0001", "severity": "major", "document": "earthing"}, {"id": "F-0002", "severity": "major", "document": "earthing"}, {"id": "F-0003", "severity": "note", "document": "x"}]
        self.assertEqual(rendering.findings_text(f), "2 major finding(s) still open. earthing: F-0001 to F-0002 (2). The list is in the manifest.")
        self.assertEqual(rendering.findings_text([]), "")

    def test_the_five_documents_have_a_report(self):
        docs = {"terminal_block_list": {"board": "B", "strips": [{"strip": "X1", "rows": [{"circuit": "C", "terminals": [{"id": "X1:1"}]}]}], "totals": {"terminals": 1, "by_section": {"1.5": 1}}},
                "boq": {"board": "B", "allowance_pct": 5, "items": [{"item_id": "I", "category": "cable", "description": "d", "unit": "m", "quantity": 1}], "totals": {"lines": 1, "cable_m": 1, "devices": 0}},
                "datasheets": {"board": "B", "datasheets": [{"item_id": "I", "kind": "cable", "candidates": [], "review_status": "pending review"}], "totals": {"items": 1, "items_without_candidate": 1}},
                "rfq": {"rfq_id": "R", "terms": {"currency": "USD"}, "issued_for": [{"name": "S", "contact": None}], "lines": [{"line_no": 1, "item_id": "I", "description": "d", "unit": "m", "quantity": 1}]},
                "lighting_study": {"engine": {"name": "e", "version": "1"}, "result": {"counts": {"rooms": 1, "luminaires": 1, "warnings": 0}, "rooms": [{"id": "r"}]}}}
        reports, skipped = rendering._reports(docs, "P")
        self.assertEqual((sorted(n for n, _ in reports), skipped), (sorted(docs), []))
        es, _ = rendering._reports(docs, "P", language="es")
        self.assertEqual(dict(es)["boq"]["title"], "Cómputo de materiales")

    def test_a_spanish_project_gets_the_spanish_title_and_columns(self):
        doc = {"title": "Specification", "sections": [{"id": "1", "title": "t", "items": [{"key": "k", "label": "l", "value": 1, "unit": None, "source": "s"}]}]}
        report = rendering.to_report("specification", doc, "P", "es")
        self.assertEqual(report["title"], "Pliego de especificaciones técnicas")
        self.assertEqual([c for c, _ in report["blocks"][1]["columns"]], ["concepto", "valor", "unidad", "fuente"])


if __name__ == "__main__":
    unittest.main()


class AcceptedMajors(unittest.TestCase):
    FINDINGS = [{"id": "F-0001", "severity": "major", "document": "earthing", "status": "open"}, {"id": "F-0002", "severity": "minor", "document": "x"}]

    def test_a_reason_marks_only_the_open_majors(self):
        out = review_state.reviewed(dict(MANIFEST, findings=self.FINDINGS), "approve", "ing", "d", "checked on site")
        self.assertEqual((out["findings"][0]["status"], out["findings"][0]["accepted_by"], out["findings"][0]["accepted_reason"]), ("accepted", "ing", "checked on site"))
        self.assertNotIn("status", out["findings"][1])

    def test_without_a_reason_findings_are_untouched(self):
        out = review_state.reviewed(dict(MANIFEST, findings=self.FINDINGS), "approve", "ing", "d")
        self.assertEqual(out["findings"], self.FINDINGS)

    def test_the_cover_says_who_accepted_and_why(self):
        done = review_state.accept_majors(dict(MANIFEST, findings=self.FINDINGS), "ing", "checked on site")
        self.assertIn("accepted by ing: checked on site", rendering.accepted_text(done))
        self.assertEqual(rendering.findings_text(done), "")

    def test_approval_marks_the_notes_as_seen(self):
        findings = [{"id": "F-0003", "severity": "note", "document": "x"}, {"id": "F-0004", "severity": "minor", "document": "x"}]
        out = review_state.reviewed(dict(MANIFEST, findings=findings), "approve", "ing", "d")["findings"]
        self.assertEqual((out[0]["status"], out[0]["accepted_reason"]), ("accepted", "seen at approval"))
        self.assertNotIn("status", out[1])
