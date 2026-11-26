"""What an organization changes of the IRAM sheet: margins, pens, text heights and the title block element by element. With no changes the sheet is the standard one; the title block drawn again from
its own elements is the same drawing."""
import copy
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from epc_draw.titleblock import layout, service, sheet_generator          # noqa: E402


def block_of(svg: str) -> str:
    return svg[svg.index('<g id="rotulo_IRAM4508"'):svg.index('<g id="dibujo"')]


class TestSheetConfig(unittest.TestCase):
    def test_the_elements_of_the_standard_block_draw_the_standard_block_again(self):
        for fmt in ("A0", "A1", "A3", "A4"):
            standard = sheet_generator.build(fmt)
            again = sheet_generator.build(fmt, config={"block": {"elements": copy.deepcopy(standard["block_elements"])}})
            self.assertEqual(standard["svg"], again["svg"], fmt)
            self.assertEqual(standard["block_elements"], again["block_elements"], fmt)

    def test_the_standard_block_has_its_lines_texts_symbol_and_logo_boxes(self):
        kinds = {}
        for e in sheet_generator.build("A1")["block_elements"]:
            kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
        self.assertGreater(kinds["line"], 15)
        self.assertGreater(kinds["text"], 40)
        self.assertEqual((kinds["rect"], kinds["symbol"], kinds["logo"]), (1, 1, 2))
        ids = [e["id"] for e in sheet_generator.build("A1")["block_elements"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_the_pens_and_the_frame_of_the_organization_are_used(self):
        built = sheet_generator.build("A1", config={"pens": {"frame": 1.4, "cell": 0.5}, "frame": {"margin_left": 30, "margin": 12, "strip": 6}, "text": {"coordinates": 4.0}})
        svg = built["svg"]
        self.assertIn('data-zona-util="36 18 823 576"', svg)                       # 30 + 6, 12 + 6, 841 - 12 - 6, 594 - 12 - 6
        self.assertIn('width="799" height="570" fill="none" stroke-width="1.4"', svg)
        self.assertEqual(built["geometry"]["zone"], [36, 18, 823, 576])
        self.assertIn('stroke-width="0.5"', block_of(svg))
        standard = sheet_generator.build("A1")["svg"]
        self.assertNotEqual(svg, standard)

    def test_an_element_moved_and_made_thicker_is_drawn_where_and_as_it_was_left(self):
        base = sheet_generator.build("A1")["block_elements"]
        elements = copy.deepcopy(base)
        line = next(e for e in elements if e["kind"] == "line")
        line.update(x1=10.0, x2=20.0, y1=5.0, y2=5.0, w=0.9)
        label = next(e for e in elements if e["kind"] == "text" and e["text"] == "FECHA")
        label.update(h=3.0)
        svg = sheet_generator.build("A1", config={"block": {"elements": elements}})["svg"]
        self.assertIn('<line x1="10" y1="5" x2="20" y2="5" stroke-width="0.9"/>', svg)
        self.assertRegex(svg, r'font-size="4\.167"[^>]*>FECHA<')                    # 3 mm of capital height is 4,167 mm of font
        self.assertEqual(len(re.findall(r">FECHA<", svg)), 1)

    def test_a_deleted_element_is_not_drawn_and_an_added_one_is(self):
        elements = copy.deepcopy(sheet_generator.build("A1")["block_elements"])
        elements = [e for e in elements if not (e["kind"] == "text" and e["text"] == "RESPONSABLE")]
        elements.append({"id": "n1", "kind": "text", "group": "txt", "x": 3, "y": 3, "text": "OBRA N°", "h": 2, "bold": True})
        svg = sheet_generator.build("A1", config={"block": {"elements": elements}})["svg"]
        self.assertNotIn(">RESPONSABLE<", svg)
        self.assertIn(">OBRA N°<", svg)

    def test_the_logo_boxes_keep_their_logo_and_their_legend(self):
        elements = copy.deepcopy(sheet_generator.build("A1")["block_elements"])
        self.assertIn("LOGO EMPRESA", sheet_generator.build("A1", config={"block": {"elements": elements}})["svg"])
        box = next(e for e in elements if e["kind"] == "logo" and e["slot"] == "client")
        box.update(x=100.0)
        again = sheet_generator.build("A1", config={"block": {"elements": elements}})["block_elements"]
        self.assertEqual(next(e for e in again if e["kind"] == "logo" and e["slot"] == "client")["x"], 100.0)

    def test_what_is_not_valid_is_said_field_by_field(self):
        self.assertEqual(layout.validate(None), {})
        self.assertEqual(layout.validate({}), {})
        errors = layout.validate({"pens": {"cell": 9, "thick": 1}, "frame": {"margin": -1}, "text": {"block": "big"}, "block": {"width": 10}, "color": "red"})
        for key in ("pens.cell", "pens.thick", "frame.margin", "text.block", "block.width", "color"):
            self.assertIn(key, errors)
        bad = {"block": {"elements": [{"id": "a", "kind": "line", "x1": 0, "y1": 0, "x2": "far", "y2": 0}, {"id": "a", "kind": "oval"}, {"id": "b", "kind": "text", "x": 1, "y": 1, "h": 99, "anchor": "up"}]}}
        errors = layout.validate(bad)
        self.assertIn("block.elements[0].x2", errors)
        self.assertIn("block.elements[1]", errors)
        self.assertIn("block.elements[2].h", errors)
        self.assertIn("block.elements[2].anchor", errors)
        with self.assertRaises(ValueError):
            sheet_generator.build("A1", config={"pens": {"cell": 9}})

    def test_the_text_and_the_symbols_of_the_block_are_safe_markup(self):
        self.assertTrue(layout.markup_ok('<tspan font-weight="bold">CUIT:</tspan> {empresa_cuit}'))
        self.assertTrue(layout.markup_ok("Ley 11.723. Q&amp;A &lt;3"))
        for bad in ("<script>alert(1)</script>", "a & b", '<tspan onclick="x()">t</tspan>', "{open"):
            self.assertFalse(layout.markup_ok(bad), bad)
        self.assertTrue(layout.symbol_ok('<circle cx="1" cy="2" r="3" fill="none" stroke-width="{pen}"/>'))
        for bad in ('<script/>', '<image href="x"/>', '<circle onload="x" r="1"/>', '<circle r="1"'):
            self.assertFalse(layout.symbol_ok(bad), bad)
        elements = copy.deepcopy(sheet_generator.build("A1")["block_elements"])
        elements.append({"id": "bad1", "kind": "text", "x": 1, "y": 1, "h": 2, "text": "<b>x</b>"})
        elements.append({"id": "bad2", "kind": "symbol", "svg": "<script/>"})
        errors = layout.validate({"block": {"elements": elements}})
        self.assertIn(f"block.elements[{len(elements) - 2}].text", errors)
        self.assertIn(f"block.elements[{len(elements) - 1}].svg", errors)

    def test_the_standard_block_is_valid_markup(self):
        self.assertEqual(layout.validate({"block": {"elements": sheet_generator.build("A1")["block_elements"]}}), {})

    def test_the_service_draws_each_sheet_with_the_configuration_of_its_format(self):
        request = {"schema_version": "1.0", "common": {"empresa": "ACME"}, "sheets": [{"name": "P1", "format": "A1"}, {"name": "P2", "format": "A3"}],
                   "sheet_config": {"A1": {"pens": {"frame": 1.6}}}}
        done = service.render(request)
        self.assertIn('stroke-width="1.6"', done["sheets"][0]["svg"])
        self.assertNotIn('stroke-width="1.6"', done["sheets"][1]["svg"])           # A3 has none: it is the standard
        self.assertIn("ACME", done["sheets"][0]["svg"])
        bad = {**request, "sheet_config": {"A1": {"pens": {"frame": 99}}}}
        with self.assertRaises(service.RequestError):
            service.render(bad)


if __name__ == "__main__":
    unittest.main()
