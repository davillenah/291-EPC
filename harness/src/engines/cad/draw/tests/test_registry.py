"""SYM-01: the one API over the symbol libraries (resolve, aliases, terminals, DXF block, insert) and the catalogue schema."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from epc_draw.symbols import KINDS, library_dir, registry as R  # noqa: E402


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


class TestEdges(unittest.TestCase):
    def test_an_id_that_exists_in_two_views_asks_for_the_view(self):
        import dataclasses
        from unittest import mock
        sld = R.resolve("lv_mccb_basic", "sld")
        mld = dataclasses.replace(sld, view="mld")
        with mock.patch.object(R, "_index", return_value=((sld, mld), {"twin": (sld, mld)})):
            with self.assertRaises(R.AmbiguousSymbol) as caught:
                R.resolve("twin")
            self.assertIn("give the view", str(caught.exception))
            self.assertIn("indique la vista", str(caught.exception))
            self.assertEqual(R.resolve("twin", "mld").view, "mld")

    def test_a_symbol_without_a_dxf_block_says_so_in_both_languages(self):
        import dataclasses
        from unittest import mock
        bare = dataclasses.replace(R.resolve("lv_mccb_basic", "sld"), dxf=None)
        with mock.patch.object(R, "resolve", return_value=bare):
            with self.assertRaises(R.UnknownSymbol) as caught:
                R.dxf_block("lv_mccb_basic", "sld")
        self.assertIn("has no DXF block", str(caught.exception))
        self.assertIn("no tiene bloque DXF", str(caught.exception))
        self.assertIsNone(bare.block)


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
