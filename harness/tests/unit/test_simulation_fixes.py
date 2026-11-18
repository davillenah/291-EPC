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


class RoomsNamedAsThePlanNamesThem(unittest.TestCase):
    """SIM-03 and SIM-04: room data by the code on the plan, and the board, the shaft and the main board by the room they are in."""
    ARCH = {"rooms": [{"id": "r1", "code": "PB-01", "name": "OFICINA", "box_m": [0.0, 0.0, 4.0, 5.0]}, {"id": "r2", "code": "PB-02", "name": "HALL", "box_m": [4.0, 0.0, 7.0, 4.0]},
                      {"id": "r3", "code": "", "name": "HALL 2", "box_m": [0.0, 5.0, 5.0, 10.0]}]}

    def building(self, **floor):
        return {"floors": [dict({"id": "PB", "architecture": self.ARCH}, **floor)]}

    def resolve(self, **floor):
        from disciplines.electrical_lv.intake.building import resolve_rooms
        return resolve_rooms(self.building(**floor))["floors"][0]

    def test_room_data_by_code_is_keyed_by_room_id(self):
        out = self.resolve(rooms={"PB-01": {"a": 1}, "r3": {"b": 2}}, special={"PB-02": {"type": "bathroom"}}, emergency={"PB-01": {}}, exclude=["PB-02", "r3"])
        self.assertEqual((out["rooms"], out["special"], out["emergency"], out["exclude"]), ({"r1": {"a": 1}, "r3": {"b": 2}}, {"r2": {"type": "bathroom"}}, {"r1": {}}, ["r2", "r3"]))

    def test_a_board_in_a_room_is_put_at_its_centre(self):
        out = self.resolve(board={"room": "PB-02"}, shaft={"room": "HALL 2"})
        self.assertEqual((out["board"], out["shaft"]), ({"x_m": 5.5, "y_m": 2.0}, {"x_m": 2.5, "y_m": 7.5}))

    def test_a_point_is_left_as_it_is(self):
        self.assertEqual(self.resolve(board={"x_m": 1.0, "y_m": 2.0})["board"], {"x_m": 1.0, "y_m": 2.0})

    def test_the_main_board_by_room(self):
        from disciplines.electrical_lv.intake.building import resolve_rooms
        b = dict(self.building(), main_board={"floor": "PB", "room": "r1"})
        self.assertEqual(resolve_rooms(b)["main_board"], {"floor": "PB", "x_m": 2.0, "y_m": 2.5})

    def test_a_room_that_is_not_on_the_plan_is_an_error(self):
        from disciplines.electrical_lv.intake.building import BuildingError
        with self.assertRaises(BuildingError) as ctx:
            self.resolve(board={"room": "PB-99"})
        self.assertIn("no room 'PB-99'", str(ctx.exception))

    def test_the_inputs_are_not_changed(self):
        from disciplines.electrical_lv.intake.building import resolve_rooms
        b = self.building(board={"room": "PB-02"})
        resolve_rooms(b)
        self.assertEqual(b["floors"][0]["board"], {"room": "PB-02"})


if __name__ == "__main__":
    unittest.main()


class PresentationSheetsTests(unittest.TestCase):
    """The isometric, elevations and sections of the architecture go to 03_ARCHITECTURE of the transmittal when the building lists them."""

    class Store:
        def __init__(self, inputs):
            self.inputs_dir = inputs

    class Context:
        def __init__(self, inputs, sheets):
            self.store = PresentationSheetsTests.Store(inputs)
            self.engine_inputs = {"building": {"floors": [{"id": "PB", "plan": "plans/PB.dxf"}], "presentation_sheets": sheets}}

    def project(self, tmp):
        plans = Path(tmp) / "plans"
        plans.mkdir()
        for name in ("PB.dxf", "ISO.dxf", "ELEV_S_PB.dxf"):
            (plans / name).write_text(name, encoding="utf-8")
        return tmp

    def test_a_listed_sheet_that_exists_is_a_supporting_file_of_the_architecture_folder(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            items = PS._architecture(self.Context(self.project(tmp), ["plans/ISO.dxf", "plans/ISO.dxf", "plans/none.dxf"]))
        self.assertEqual([i["path"] for i in items], ["03_ARCHITECTURE/PB.dxf", "03_ARCHITECTURE/ISO.dxf"])
        self.assertTrue(all(i["support"] and i["folder"] == "03_ARCHITECTURE" for i in items))

    def test_without_the_key_only_the_floor_plans_are_copied(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            items = PS._architecture(self.Context(self.project(tmp), None))
        self.assertEqual([i["path"] for i in items], ["03_ARCHITECTURE/PB.dxf"])
