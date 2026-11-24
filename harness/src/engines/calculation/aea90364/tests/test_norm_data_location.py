"""MIG-37a: the norm data of AEA 90364 lives in `harness/config/normative/AR/electrical/aea90364/` and is read through ONE loader (`norm_data`)."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_aea90364 import aea_rules, aea_tables, norm_data, solutions, system_voltage   # noqa: E402

import epc_aea90364   # noqa: E402

PKG = Path(epc_aea90364.__file__).resolve().parent                   # norm_data itself is in epc_calc_common since MIG-37b; the rest of the package data stays here
MOVED_FILES = ("aea_tables.json", "design-criteria.json", "standard-solutions.json", "system_voltages.json")
STAYING = ("formulas_aea.json", "example_calculo.json", "example_conductor_table.json", "data/installation_types.json", "data/insulation_by_role.json",
           "data/review.json", "data/review_log.jsonl")


def _root_with_copy(tmp):
    """A temporary `normative` root with a copy of the real folder; returns the root."""
    dest = Path(tmp) / "normative" / "AR" / "electrical" / "aea90364"
    shutil.copytree(norm_data.normative_dir(), dest)
    return Path(tmp) / "normative"


class TestLocation(unittest.TestCase):
    def test_every_moved_file_is_in_the_normative_folder_and_nothing_remains_in_the_package(self):
        folder = norm_data.normative_dir()
        self.assertEqual(folder.parts[-6:], ("harness", "config", "normative", "AR", "electrical", "aea90364")[-6:])
        for name in MOVED_FILES:
            self.assertTrue((folder / name).is_file(), name)
            self.assertFalse((PKG / name).exists(), name)
            self.assertFalse((PKG / "data" / name).exists(), name)
        rules = sorted(p.name for p in (folder / "rules").glob("*.json"))
        self.assertEqual(len(rules), 18)
        self.assertIn("_indice.json", rules)
        self.assertFalse((PKG / "rules").exists())

    def test_what_is_not_norm_data_stays_in_the_package(self):
        for name in STAYING:
            self.assertTrue((PKG / name).is_file(), name)

    def test_the_loader_returns_what_the_file_bytes_parse_to(self):
        folder = norm_data.normative_dir()
        for name in MOVED_FILES + tuple("rules/" + p.name for p in (folder / "rules").glob("*.json")):
            expected = json.loads((folder / name).read_bytes().decode("utf-8-sig"))
            self.assertEqual(norm_data.load_json(name), expected, name)
        self.assertEqual(aea_tables.cargar(), json.loads((folder / "aea_tables.json").read_bytes()))
        self.assertEqual(aea_rules.indice(), json.loads((folder / "rules" / "_indice.json").read_bytes()))
        self.assertEqual(solutions.defaults(), json.loads((folder / "standard-solutions.json").read_bytes()))
        self.assertEqual(system_voltage.systems(), {400.0: 230.0, 380.0: 220.0})


class TestLoader(unittest.TestCase):
    def setUp(self):
        for module, name in ((aea_tables, "RUTA_JSON"), (aea_rules, "CARPETA")):
            module.__dict__.pop(name, None)           # another test may have left the path it saved and restored: the default is computed lazily

    def tearDown(self):
        norm_data.clear_cache()
        aea_tables.limpiar_cache_tablas()
        aea_rules.limpiar_cache_reglas()

    def test_the_environment_variable_points_the_loader_at_another_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _root_with_copy(tmp)
            marker = root / "AR" / "electrical" / "aea90364" / "system_voltages.json"
            marker.write_text(json.dumps({"systems": []}), encoding="utf-8")
            with mock.patch.dict(os.environ, {norm_data.ENV_VAR: str(root)}):
                self.assertEqual(norm_data.normative_dir(), root / "AR" / "electrical" / "aea90364")
                self.assertEqual(norm_data.load_json("system_voltages.json"), {"systems": []})
                self.assertEqual(norm_data.criteria_file("electrical"), root / "AR" / "electrical" / "aea90364" / "design-criteria.json")
        self.assertEqual(norm_data.load_json("system_voltages.json")["systems"][0]["un_v"], 400.0)

    def test_a_missing_folder_gives_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {norm_data.ENV_VAR: tmp}):
            with self.assertRaises(FileNotFoundError) as cm:
                norm_data.normative_dir()
            self.assertIn(tmp, str(cm.exception))
            self.assertIn("aea90364", str(cm.exception))
            with self.assertRaises(FileNotFoundError):
                norm_data.load_json("aea_tables.json")

    def test_a_discipline_without_catalog_gets_none_even_without_folder(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {norm_data.ENV_VAR: tmp}):
            self.assertIsNone(norm_data.criteria_file("hvac"))

    def test_the_cache_serves_the_same_object_until_it_is_cleared(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _root_with_copy(tmp)
            f = root / "AR" / "electrical" / "aea90364" / "system_voltages.json"
            with mock.patch.dict(os.environ, {norm_data.ENV_VAR: str(root)}):
                first = norm_data.load_json("system_voltages.json")
                self.assertIs(norm_data.load_json("system_voltages.json"), first)
                f.write_text(json.dumps({"systems": [1]}), encoding="utf-8")
                self.assertIs(norm_data.load_json("system_voltages.json"), first)           # still the cached one
                norm_data.clear_cache()
                self.assertEqual(norm_data.load_json("system_voltages.json"), {"systems": [1]})

    def test_the_old_cache_clearing_functions_still_reread_the_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _root_with_copy(tmp)
            f = root / "AR" / "electrical" / "aea90364" / "aea_tables.json"
            data = json.loads(f.read_bytes())
            with mock.patch.dict(os.environ, {norm_data.ENV_VAR: str(root)}):
                aea_tables.limpiar_cache_tablas()
                self.assertEqual(aea_tables.cargar(), data)
                data["marker_mig37a"] = 1
                f.write_text(json.dumps(data), encoding="utf-8")
                self.assertNotIn("marker_mig37a", aea_tables.cargar())
                aea_tables.limpiar_cache_tablas()
                self.assertEqual(aea_tables.cargar()["marker_mig37a"], 1)
            aea_tables.limpiar_cache_tablas()
            aea_rules.limpiar_cache_reglas()
            self.assertGreater(len(aea_rules.reglas()), 100)

    def test_the_path_attributes_the_backend_reads_still_exist(self):
        self.assertTrue(Path(aea_tables.RUTA_JSON).is_file())
        self.assertTrue(Path(aea_rules.CARPETA).is_dir())
        self.assertTrue(Path(solutions.DEFAULT_FILE).is_file())
        with self.assertRaises(AttributeError):
            aea_tables.NO_SUCH_NAME
        with self.assertRaises(AttributeError):
            aea_rules.NO_SUCH_NAME


if __name__ == "__main__":
    unittest.main()
