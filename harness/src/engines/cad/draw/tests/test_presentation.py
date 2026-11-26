"""The plans the harness authors are sheets of a presentation: doors and windows are blocks with a wipeout, and the sheet carries dimension chains, tags, the room and opening schedules, notes,
and (with the heights) an isometric, an elevation and a section. The plans a client gives are not given any of it."""
import io
import re
import unittest

import ezdxf

from epc_draw.arch import ArchError, recognize
from epc_draw.arch.author import architecture_of, building_views, errors_of, plan_dxf
from epc_draw.arch.drawing import build_drawing
from epc_draw.arch.export.export_dxf import to_dxf
from epc_draw.arch.presentation import settings, tag_name
from test_author import floor

HEIGHTS = {"wall_height_m": 3.0, "door_head_m": 2.1, "window_sill_m": 0.9, "window_head_m": 2.1, "slab_m": 0.2, "elevation_m": 0.0}


def doc_of(description=None, **kw):
    arch = architecture_of(description or floor())
    return arch, ezdxf.read(io.StringIO(plan_dxf(arch, **kw)))


def texts(doc, layer=None):
    return [e.dxf.text for e in doc.modelspace().query("TEXT") if layer is None or e.dxf.layer == layer]


class DoorsAndWindowsAreBlocks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arch, cls.doc = doc_of()
        cls.inserts = list(cls.doc.modelspace().query("INSERT"))

    def test_every_door_and_window_is_an_insert_of_a_block(self):
        kinds = sorted(i.dxf.name.split("_")[1] for i in self.inserts)
        self.assertEqual(kinds, ["DOOR"] * 7 + ["WINDOW"] * 6)
        self.assertEqual({i.dxf.layer for i in self.inserts}, {"291-A-DOOR-N", "291-A-GLAZ-N"})

    def test_no_loose_door_or_window_lines_are_left_in_the_model_space(self):
        loose = {e.dxf.layer for e in self.doc.modelspace() if e.dxftype() != "INSERT"}
        self.assertFalse(loose & {"291-A-DOOR-N", "291-A-DOOR-FULL-N", "291-A-GLAZ-N", "291-A-GLAZ-FULL-N", "291-A-ANNO-NPLT"})

    def test_each_block_starts_with_a_wipeout_and_equal_openings_share_a_block(self):
        names = {i.dxf.name for i in self.inserts}
        self.assertLess(len(names), len(self.inserts))
        for n in names:
            blk = self.doc.blocks.get(n)
            self.assertEqual(blk[0].dxftype(), "WIPEOUT", n)
            self.assertEqual(blk[0].dxf.layer, "291-A-ANNO-NPLT")
            self.assertTrue(any(e.dxftype() in ("LWPOLYLINE", "ARC") for e in blk))

    def test_a_door_block_keeps_its_swing_and_a_window_block_its_glass(self):
        for i in self.inserts:
            layers = {e.dxf.layer for e in self.doc.blocks.get(i.dxf.name)}
            self.assertIn("291-A-DOOR-FULL-N" if "DOOR" in i.dxf.name else "291-A-GLAZ-FULL-N", layers)

    def test_the_dxf_audits_clean(self):
        self.assertEqual(len(self.doc.audit().errors), 0)

    def test_the_widths_read_back_from_the_blocks_are_the_authored_ones(self):
        read = recognize(plan_dxf(self.arch).encode("utf-8"), "plan.dxf").architecture
        got = sorted(round(o.width / read.units_per_metre, 2) for o in read.openings)
        self.assertEqual(got, sorted(round(o.width / 1000.0, 2) for o in self.arch.openings))


class TheSheetOfAPresentation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arch, cls.doc = doc_of()

    def test_dimension_chains_hold_the_measures_between_wall_axes_and_the_overall_one(self):
        figures = sorted(set(texts(self.doc, "291-A-ANNO-DIMS")))
        self.assertIn("24.00", figures)                                   # overall width: 0 to 24 m
        self.assertIn("14.00", figures)                                   # overall depth
        self.assertIn("8.00", figures)

    def test_the_chains_are_south_and_east_so_the_plan_keeps_its_origin_at_the_building_corner(self):
        walls = [e for e in self.doc.modelspace().query("LWPOLYLINE") if e.dxf.layer == "291-A-WALL-FULL-N"]
        left = min(p[0] for e in walls for p in e.get_points("xy"))
        top = max(p[1] for e in walls for p in e.get_points("xy"))
        dims = [p for e in self.doc.modelspace().query("LWPOLYLINE") if e.dxf.layer == "291-A-ANNO-DIMS" for p in e.get_points("xy")]
        self.assertTrue(dims)
        self.assertGreaterEqual(min(p[0] for p in dims), left - 1e-6)
        self.assertLessEqual(max(p[1] for p in dims), top + 1e-6)

    def test_every_door_and_window_has_a_tag_and_a_width(self):
        notes = texts(self.doc, "291-A-ANNO")
        for o in self.arch.openings:
            self.assertIn(tag_name(o), notes)
        self.assertIn("1.20", notes)

    def test_the_schedules_name_every_room_with_its_area_and_the_openings(self):
        everything = " | ".join(texts(self.doc))
        for room in self.arch.rooms:
            self.assertIn(room.name, everything)
            self.assertIn(f"{room.area_m2:.2f}", everything)
        self.assertIn("TOTAL", everything)
        self.assertIn("Puerta", everything)
        self.assertIn("Ventana", everything)

    def test_every_title_of_the_panel_and_every_note_has_english_and_spanish(self):
        notes = [t for t in texts(self.doc, "291-A-ANNO") if re.match(r"^\d\. ", t) or t == "GENERAL NOTES / NOTAS GENERALES"]
        self.assertGreaterEqual(len(notes), 5)
        for t in notes:
            self.assertIn(" / ", t)

    def test_the_plan_is_read_back_with_its_rooms_and_names_in_spite_of_the_tags_and_tables(self):
        read = recognize(plan_dxf(self.arch).encode("utf-8"), "plan.dxf").architecture
        self.assertEqual(sorted(r.name for r in read.rooms), sorted(r.name for r in self.arch.rooms))
        self.assertEqual((read.counts()["doors"], read.counts()["windows"]), (7, 6))

    def test_the_sizes_are_in_the_style_not_in_the_code(self):
        self.assertEqual(set(settings()), {"panel_mm", "panel_gap_mm", "dim_offset_mm", "dim_step_mm", "dim_tick_mm", "dim_ext_gap_mm", "tag_offset_mm", "row_mm", "column_pad_mm",
                                           "wipeout_margin", "iso_angle_deg", "iso_fill"})

    def test_a_plan_that_is_not_authored_gets_no_presentation(self):
        d = build_drawing(self.arch, sheet="A1")
        self.assertFalse([i for i in d.items if i.layer in ("291-A-ANNO-DIMS",)])
        self.assertFalse([i for i in d.items if i.layer == "291-A-ANNO" and getattr(i, "value", "").startswith("GENERAL")])

    def test_the_plan_is_drawn_at_the_biggest_scale_that_fits_beside_the_panel(self):
        d = build_drawing(self.arch, sheet="A1", presentation=True)
        self.assertLessEqual(d.scale, 100)


class ViewsOfTheBuilding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.description = dict(floor(), heights_m=HEIGHTS)
        cls.arch = architecture_of(cls.description)
        cls.views = building_views([cls.description], [cls.arch])

    def test_the_isometric_an_elevation_and_a_section_are_written_with_the_heights(self):
        self.assertEqual(sorted(self.views), ["ELEV_S_PB.dxf", "ISO.dxf", "SEC_A_PB.dxf"])

    def test_without_the_heights_there_are_no_views_and_nothing_is_assumed(self):
        self.assertEqual(building_views([floor()], [architecture_of(floor())]), {})

    def test_the_isometric_is_filled_faces_with_the_level_named_and_no_roof(self):
        doc = ezdxf.read(io.StringIO(self.views["ISO.dxf"]))
        faces = [e for e in doc.modelspace().query("HATCH") if e.dxf.layer in ("291-A-WALL-FULL-N", "291-A-WALL-PATT-N", "291-A-GLAZ-FULL-N", "291-A-AREA")]
        self.assertGreater(len(faces), 50)
        self.assertTrue(any("PLANTA BAJA" in t for t in texts(doc, "291-A-ANNO")))
        slab = [e for e in doc.modelspace().query("LWPOLYLINE") if e.dxf.layer == "291-A-WALL-PATT-N"]
        self.assertLessEqual(len(slab), 3)                                 # only the floor slab: at most its top, south and east faces (a roof slab would add three more)

    def test_the_isometric_title_has_english_and_spanish(self):
        self.assertIn("ISOMÉTRICO / ISOMETRIC", self.views["ISO.dxf"])

    def test_heights_that_are_not_valid_are_reported(self):
        bad = dict(floor(), heights_m={"wall_height_m": 3.0})
        self.assertTrue([e for e in errors_of(bad) if e.startswith("heights_m")])
        with self.assertRaises(ArchError):
            architecture_of(bad)

    def test_the_dxf_of_the_views_audit_clean(self):
        for name, text in self.views.items():
            self.assertEqual(len(ezdxf.read(io.StringIO(text)).audit().errors), 0, name)


class TwoFloors(unittest.TestCase):
    def test_the_isometric_stacks_the_floors_at_their_levels(self):
        upper = dict(floor("P1", "PLANTA ALTA", 1), heights_m=dict(HEIGHTS, elevation_m=3.2))
        lower = dict(floor(), heights_m=HEIGHTS)
        views = building_views([lower, upper], [architecture_of(lower), architecture_of(upper)])
        doc = ezdxf.read(io.StringIO(views["ISO.dxf"]))
        labels = texts(doc, "291-A-ANNO")
        self.assertTrue(any("PLANTA ALTA" in t and "3.20" in t for t in labels))
        self.assertTrue(any("PLANTA BAJA" in t for t in labels))
        self.assertIn("ELEV_S_P1.dxf", views)


if __name__ == "__main__":
    unittest.main()
