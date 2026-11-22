"""SYM-01: the one API over the symbol libraries (resolve, aliases, terminals, DXF block, insert) and the catalogue schema."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from epc_symbols import KINDS, library_dir, registry as R  # noqa: E402


class TestResolve(unittest.TestCase):
    def test_every_alias_of_a_symbol_gives_the_same_record(self):
        by_id = R.resolve("lv_mccb_basic", "sld")
        for alias in ("electrical-lv.lv_mccb_basic", "291_E_LV_SLD_IEC60617_mccb_basic", "291_E_LV_SLD_IEC60617_mccb_basic.svg"):
            self.assertEqual(R.resolve(alias, "sld"), by_id, alias)
        self.assertEqual((by_id.domain, by_id.view, by_id.library), ("electrical-lv", "sld", "sld-lv-symbol"))

    def test_an_unknown_symbol_is_an_error_in_both_languages_never_a_stand_in(self):
        with self.assertRaises(R.UnknownSymbol) as caught:
            R.resolve("lv_does_not_exist")
        self.assertIn("is not in the symbol library", str(caught.exception))
        self.assertIn("no está en la biblioteca", str(caught.exception))

    def test_the_view_narrows_and_a_missing_view_is_reported(self):
        with self.assertRaises(R.UnknownSymbol):
            R.resolve("lv_mccb_basic", "mld")

    def test_every_catalogue_symbol_resolves_by_its_qualified_id_and_has_a_block(self):
        records = [R.resolve(i) for i in R.list_ids()]
        self.assertGreater(len(records), 200)
        self.assertEqual([r.id for r in records if r.dxf is None], [])
        self.assertTrue(all(r.svg.is_file() for r in records))

    def test_list_filters_by_domain_and_view(self):
        mv = R.list_ids("electrical-mv", "sld")
        self.assertTrue(mv and all(i.startswith("electrical-mv.") for i in mv))
        self.assertEqual(set(R.list_ids("electrical-lv")) & set(mv), set())
        self.assertEqual(R.list_ids("nope"), [])

    def test_the_block_name_is_the_one_defined_in_the_dxf_file(self):
        import ezdxf
        for sid in ("lv_mccb_basic", "lv_contactor", "lv_motor_3ph"):
            path, block = R.dxf_block(sid, "sld")
            names = [b.name for b in ezdxf.readfile(str(path)).blocks if not b.name.startswith("*")]
            self.assertEqual(names, [block], sid)

    def test_terminals_are_the_ports_of_the_catalogue(self):
        ports = R.terminals("lv_mccb_basic", "sld")
        self.assertEqual({p["id"] for p in ports}, {"top", "bottom"})

    def test_svg_fragment_is_the_group_of_the_symbol(self):
        self.assertEqual(R.svg_fragment("lv_mccb_basic", "sld").get("id"), "lv_mccb_basic")


class TestInsert(unittest.TestCase):
    def test_insert_places_one_block_reference_per_call_and_one_definition(self):
        import ezdxf
        doc = ezdxf.new("R2013")
        R.insert(doc, "lv_mccb_basic", "sld", (10, 20), scale=0.5, layer="0", attribs={"TAG": "-Q1"})
        ref = R.insert(doc, "lv_mccb_basic", "sld", (30, 20), scale=0.5)
        inserts = list(doc.modelspace().query("INSERT"))
        self.assertEqual(len(inserts), 2)
        self.assertEqual(inserts[0].dxf.name, R.resolve("lv_mccb_basic", "sld").block)
        self.assertEqual(ref.dxf.xscale, 0.5)
        self.assertEqual([b.name for b in doc.blocks if not b.name.startswith("*")], [inserts[0].dxf.name])

    def test_insert_of_an_unknown_symbol_raises_and_adds_nothing(self):
        import ezdxf
        doc = ezdxf.new("R2013")
        with self.assertRaises(R.UnknownSymbol):
            R.insert(doc, "lv_does_not_exist", "sld", (0, 0))
        self.assertEqual(len(doc.modelspace()), 0)


class TestCatalogueSchema(unittest.TestCase):
    def test_every_catalogue_validates_against_the_schema(self):
        import jsonschema
        schema = json.loads((Path(R.__file__).parent / "schema" / "symbol_catalog.schema.json").read_text(encoding="utf-8"))
        for kind in KINDS:
            catalog = library_dir(kind) / "_catalog.json"
            if catalog.is_file():
                jsonschema.validate(json.loads(catalog.read_text(encoding="utf-8-sig")), schema)


if __name__ == "__main__":
    unittest.main()
