"""Tests of the datasheets engine: pure functions, small synthetic catalogs; one read-only test over the real repository catalog."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import epc_datasheets
from epc_datasheets import build_datasheets, catalog as catalog_mod, inputs, load_catalog_dir, match, render_rows, requirements_from_circuits

REAL_CATALOG = Path(__file__).resolve().parents[5] / "catalogs" / "manufacturers"


def product(pid, **changes):
    base = {"id": pid, "family": f"Fam {pid}", "type": "mccb", "status": "unverified", "source": f"https://example.test/{pid}", "rated_current_a": {"min": 16, "max": 160},
            "standards": ["IEC 60947-2"], "breaking_capacity": [{"class": "N", "voltage_v": 400, "icu_ka": 25}, {"class": "H", "voltage_v": 400, "icu_ka": 36}]}
    base.update(changes)
    return base


def document(manufacturer="m1", category="breakers", products=None, **extra):
    doc = {"manufacturer": manufacturer, "category": category, "products": products if products is not None else [product("p1")]}
    doc.update(extra)
    return doc


def device_req(item_id="DS-DEV-001", **changes):
    base = {"item_id": item_id, "kind": "protective_device", "device_kind": "mccb", "in_a": 100, "poles": 3, "breaking_capacity_ka": 25, "voltage_v": 400, "circuits": ["B", "A"]}
    base.update(changes)
    return base


def cable_req(item_id="DS-CAB-001", **changes):
    base = {"item_id": item_id, "kind": "cable", "material": "cu", "insulation": "pvc", "phase_conductors": 3, "s_mm2": 10, "neutral_mm2": 10, "pe_mm2": 10, "cores": 5, "circuits": ["A"]}
    base.update(changes)
    return base


def circuit(tag, **changes):
    base = {"tag": tag, "phases": 1, "s_mm2": 2.5, "neutral_mm2": 2.5, "pe_mm2": 2.5, "length_m": 10.0, "material": "cu", "insulation": "pvc",
            "device_kind": "mcb", "in_a": 16, "poles": 2, "breaking_capacity_ka": 6}
    base.update(changes)
    return base


def sheets(requirements, catalog=None):
    return build_datasheets("TG-1", requirements, catalog if catalog is not None else [document()])["datasheets"]


class DeviceSatisfactionTests(unittest.TestCase):
    def ids(self, req, products):
        sheet = sheets([req], [document(products=products)])[0]
        return [c["product_id"] for c in sheet["candidates"]]

    def test_rated_current_boundaries(self):
        p = [product("p1", rated_current_a={"min": 16, "max": 160})]
        for in_a, expected in ((16, ["p1"]), (160, ["p1"]), (15.9, []), (160.1, []), (100, ["p1"])):
            self.assertEqual(self.ids(device_req(in_a=in_a), p), expected, in_a)

    def test_max_only_and_list_shapes(self):
        self.assertEqual(self.ids(device_req(in_a=1), [product("p1", rated_current_a={"max": 160})]), ["p1"])
        self.assertEqual(self.ids(device_req(in_a=63), [product("p1", rated_current_a=[16, 63])]), ["p1"])
        self.assertEqual(self.ids(device_req(in_a=64), [product("p1", rated_current_a=[16, 63])]), [])

    def test_no_rated_current_data_is_not_satisfied(self):
        p = product("p1")
        del p["rated_current_a"]
        self.assertEqual(self.ids(device_req(), [p]), [])
        self.assertEqual(self.ids(device_req(), [product("p2", rated_current_a={"min": 10})]), [])

    def test_breaking_capacity_equal_greater_lower(self):
        p = [product("p1", breaking_capacity=[{"voltage_v": 400, "icu_ka": 25}])]
        for ka, expected in ((25, ["p1"]), (24.9, ["p1"]), (25.1, [])):
            self.assertEqual(self.ids(device_req(breaking_capacity_ka=ka), p), expected, ka)

    def test_voltage_condition(self):
        p = [product("p1", breaking_capacity=[{"voltage_v": 230, "icu_ka": 50}, {"voltage_v": 400, "icu_ka": 20}])]
        self.assertEqual(self.ids(device_req(voltage_v=230, breaking_capacity_ka=40), p), ["p1"])
        self.assertEqual(self.ids(device_req(voltage_v=400, breaking_capacity_ka=40), p), [])
        self.assertEqual(self.ids(device_req(voltage_v=400, breaking_capacity_ka=20), p), ["p1"])
        self.assertEqual(self.ids(device_req(voltage_v=415, breaking_capacity_ka=1), p), [])
        self.assertEqual(self.ids(device_req(voltage_v=None, breaking_capacity_ka=40), p), ["p1"])

    def test_missing_catalog_capacity_is_not_satisfied(self):
        p = product("p1")
        del p["breaking_capacity"]
        self.assertEqual(self.ids(device_req(), [p]), [])

    def test_matched_entries_are_the_satisfying_ones(self):
        sheet = sheets([device_req(voltage_v=400, breaking_capacity_ka=30)])[0]
        self.assertEqual(sheet["candidates"][0]["matched"], {"in_a": 100, "breaking_capacity": [{"class": "H", "voltage_v": 400, "icu_ka": 36}]})

    def test_kind_mismatch_and_category(self):
        self.assertEqual(self.ids(device_req(device_kind="mcb"), [product("p1")]), [])
        wrong = document(category="cables", products=[product("c1")])
        self.assertEqual(sheets([device_req()], [wrong])[0]["candidates"], [])

    def test_poles(self):
        self.assertEqual(self.ids(device_req(poles=3), [product("p1", poles=[3, 4])]), ["p1"])
        self.assertEqual(self.ids(device_req(poles=2), [product("p1", poles=[3, 4])]), [])
        sheet = sheets([device_req(poles=3)])[0]
        self.assertEqual(sheet["candidates"][0]["unconfirmed"], ["poles"])
        self.assertEqual(sheets([device_req(poles=None)])[0]["candidates"][0]["unconfirmed"], [])

    def test_breaking_capacity_not_required(self):
        sheet = sheets([device_req(breaking_capacity_ka=None)])[0]
        self.assertEqual(len(sheet["candidates"]), 1)
        self.assertIn("DS-DEV-001: breaking capacity not specified (not compared)", sheet["issues"])
        self.assertNotIn("breaking_capacity", sheet["candidates"][0]["matched"])

    def test_missing_voltage_is_reported(self):
        sheet = sheets([device_req(voltage_v=None)])[0]
        self.assertIn("DS-DEV-001: voltage not specified (breaking capacity compared at any catalog voltage)", sheet["issues"])

    def test_incomplete_requirement_has_no_candidate(self):
        for field in ("device_kind", "in_a"):
            sheet = sheets([device_req(**{field: None})])[0]
            self.assertEqual(sheet["candidates"], [])
            self.assertIn(f"DS-DEV-001: missing {field} (nothing to compare)", sheet["issues"])


class CableSatisfactionTests(unittest.TestCase):
    CABLES = [document("m2", "cables", [product("c1", type="cable_power", construction="VV-K, PVC"), product("c2", type="cable_power", construction="RZ1-R XLPE"),
                                         product("c3", type="cable_power", construction="PVCX")])]

    def test_insulation_word_match(self):
        sheet = sheets([cable_req()], self.CABLES)[0]
        self.assertEqual([c["product_id"] for c in sheet["candidates"]], ["c1"])
        self.assertEqual(sheet["candidates"][0]["matched"], {"insulation": "pvc"})
        self.assertEqual(sheet["candidates"][0]["unconfirmed"], ["material", "section", "conductors"])

    def test_family_text_counts(self):
        cables = [document("m2", "cables", [product("c1", family="Cable XLPE 1 kV")])]
        self.assertEqual(len(sheets([cable_req(insulation="xlpe")], cables)[0]["candidates"]), 1)

    def test_no_insulation_requirement_matches_every_cable(self):
        sheet = sheets([cable_req(insulation=None)], self.CABLES)[0]
        self.assertEqual(len(sheet["candidates"]), 3)
        self.assertIn("DS-CAB-001: insulation not specified (not compared)", sheet["issues"])

    def test_breaker_document_is_not_a_cable_candidate(self):
        self.assertEqual(sheets([cable_req(insulation=None)])[0]["candidates"], [])


class BuildTests(unittest.TestCase):
    def test_shape_and_verbatim_copy(self):
        p = product("p1", notes="n", voltage="up to 440 V")
        result = build_datasheets("TG-1", [device_req()], [document(products=[p], manufacturer_name="M One")])
        self.assertEqual(set(result), {"board", "datasheets", "totals", "assumptions", "norm_records", "issues"})
        sheet = result["datasheets"][0]
        self.assertEqual((sheet["item_id"], sheet["kind"], sheet["review_status"]), ("DS-DEV-001", "protective_device", "pending review"))
        self.assertEqual(sheet["review_reason"], "catalog values are unverified manufacturer data")
        self.assertEqual(sheet["requirement"]["circuits"], ["A", "B"])
        c = sheet["candidates"][0]
        for key in ("family", "type", "source", "rated_current_a", "breaking_capacity", "standards", "notes", "voltage"):
            self.assertEqual(c[key], p[key])
        self.assertEqual((c["manufacturer"], c["catalog_status"], c["product_id"]), ("m1", "unverified", "p1"))
        self.assertNotIn("status", c)
        self.assertEqual(result["totals"], {"items": 1, "items_without_candidate": 0})
        self.assertEqual(result["norm_records"], [{"manufacturer": "m1", "category": "breakers", "catalog_status": "unverified", "review_status": "pending review",
                                                   "reason": "catalog values are unverified manufacturer data"}])

    def test_catalog_is_not_modified(self):
        catalog = [document()]
        before = copy.deepcopy(catalog)
        build_datasheets("TG-1", [device_req()], catalog)
        self.assertEqual(catalog, before)

    def test_verified_status_is_copied_verbatim(self):
        sheet = sheets([device_req()], [document(products=[product("p1", status="verified")])])[0]
        self.assertEqual(sheet["candidates"][0]["catalog_status"], "verified")
        self.assertEqual(sheet["review_status"], "pending review")

    def test_no_candidate_is_an_issue(self):
        result = build_datasheets("TG-1", [device_req(in_a=999)], [document()])
        self.assertEqual(result["datasheets"][0]["candidates"], [])
        self.assertIn("DS-DEV-001: no catalog product satisfies the requirement", result["issues"])
        self.assertEqual((result["totals"], result["norm_records"]), ({"items": 1, "items_without_candidate": 1}, []))

    def test_empty_requirements_and_empty_catalog(self):
        result = build_datasheets("TG-1", [], [])
        self.assertEqual((result["datasheets"], result["totals"], result["issues"]), ([], {"items": 0, "items_without_candidate": 0}, []))
        self.assertEqual(sheets([device_req()], [])[0]["candidates"], [])

    def test_deterministic_order(self):
        catalog = [document("zz", products=[product("z1")]), document("aa", products=[product("b2", family="B"), product("a1", family="B"), product("c3", family="A")])]
        reqs = [device_req("DS-DEV-002"), device_req("DS-DEV-001")]
        a = build_datasheets("TG-1", reqs, catalog)
        b = build_datasheets("TG-1", list(reversed(reqs)), list(reversed(catalog)))
        self.assertEqual(a, b)
        self.assertEqual([s["item_id"] for s in a["datasheets"]], ["DS-DEV-001", "DS-DEV-002"])
        self.assertEqual([c["product_id"] for c in a["datasheets"][0]["candidates"]], ["c3", "a1", "b2", "z1"])

    def test_invalid_inputs(self):
        for board in ("", None, 3):
            with self.assertRaisesRegex(ValueError, "board_name"):
                build_datasheets(board, [], [])
        with self.assertRaisesRegex(ValueError, "catalog must be a list"):
            build_datasheets("TG-1", [], {})


class RenderRowsTests(unittest.TestCase):
    def test_rows(self):
        result = build_datasheets("TG-1", [device_req("DS-DEV-001"), device_req("DS-DEV-002", in_a=999), cable_req(insulation=None, material=None)],
                                  [document(), document("m2", "cables", [product("c1")])])
        rows = render_rows(result)
        self.assertEqual([r["item_id"] for r in rows], ["DS-CAB-001", "DS-DEV-001", "DS-DEV-002"])
        self.assertEqual(rows[0]["requirement"], "material unspecified INSULATION UNSPECIFIED cable 3x10 mm2 (5 cores)")
        self.assertEqual((rows[1]["manufacturer"], rows[1]["catalog_status"], rows[1]["circuits"]), ("m1", "unverified", "A, B"))
        self.assertEqual(rows[1]["requirement"], "MCCB, 100 A, 3 poles, 25 kA, at 400 V")
        self.assertEqual((rows[2]["manufacturer"], rows[2]["issue"]), ("", "DS-DEV-002: no catalog product satisfies the requirement"))

    def test_unspecified_device_text(self):
        req = device_req(device_kind=None, in_a=None, poles=None, breaking_capacity_ka=None, voltage_v=None)
        row = render_rows(build_datasheets("TG-1", [req], []))[0]
        self.assertEqual(row["requirement"], "unspecified-kind, rated current unspecified, poles unspecified, breaking capacity unspecified")


class RequirementsFromCircuitsTests(unittest.TestCase):
    def test_deduplication_and_ids(self):
        circuits = [circuit("B"), circuit("A"), circuit("C", in_a=32, s_mm2=4), circuit("D", phases=3, s_mm2=10, neutral_mm2=None, device_kind="mccb", in_a=100, poles=3)]
        reqs = requirements_from_circuits(circuits, voltage_v=400)
        devices = [r for r in reqs if r["kind"] == "protective_device"]
        cables = [r for r in reqs if r["kind"] == "cable"]
        self.assertEqual([r["item_id"] for r in devices], ["DS-DEV-001", "DS-DEV-002", "DS-DEV-003"])
        self.assertEqual([(r["device_kind"], r["in_a"], r["circuits"]) for r in devices], [("mcb", 16, ["A", "B"]), ("mcb", 32, ["C"]), ("mccb", 100, ["D"])])
        self.assertTrue(all(r["voltage_v"] == 400 for r in devices))
        self.assertEqual([r["item_id"] for r in cables], ["DS-CAB-001", "DS-CAB-002", "DS-CAB-003"])
        self.assertEqual([(r["s_mm2"], r["cores"], r["circuits"]) for r in cables], [(2.5, 3, ["A", "B"]), (4, 3, ["C"]), (10, 4, ["D"])])
        self.assertEqual(cables[2]["phase_conductors"], 3)

    def test_output_feeds_build_datasheets(self):
        result = build_datasheets("TG-1", requirements_from_circuits([circuit("A", device_kind="mccb", in_a=100, poles=3, breaking_capacity_ka=25)], voltage_v=400), [document()])
        self.assertEqual(result["totals"]["items"], 2)
        self.assertEqual([len(d["candidates"]) for d in result["datasheets"]], [0, 1])

    def test_order_independent_and_no_voltage(self):
        circuits = [circuit("A"), circuit("B", in_a=6), circuit("C", material=None, device_kind=None)]
        self.assertEqual(requirements_from_circuits(circuits), requirements_from_circuits(list(reversed(circuits))))
        self.assertIsNone(requirements_from_circuits(circuits)[0]["voltage_v"])

    def test_circuit_without_device_data(self):
        reqs = requirements_from_circuits([circuit("A", device_kind=None, in_a=None, poles=None, breaking_capacity_ka=None)])
        self.assertEqual([r["kind"] for r in reqs], ["cable"])

    def test_invalid_circuits(self):
        for bad, message in (([], "non-empty list"), ([1], "must be an object"), ([circuit("A", zz=1)], "unknown key"), ([circuit("A", phases=2)], "phases must be"),
                             ([circuit("A", s_mm2=0)], "s_mm2 must be"), ([circuit("A", poles=5)], "poles must be"), ([circuit("A", material="")], "material must be"),
                             ([circuit("A"), circuit("A")], "duplicate circuit tag"), ([circuit("")], "tag must be")):
            with self.assertRaisesRegex(ValueError, message):
                requirements_from_circuits(bad)
        with self.assertRaisesRegex(ValueError, "voltage_v"):
            requirements_from_circuits([circuit("A")], voltage_v=-1)
        self.assertIsNone(inputs.poles(None, "x"))


class RequirementValidationTests(unittest.TestCase):
    def test_invalid_requirements(self):
        bad = [("x", "must be a list"), ([1], "must be an object"), ([{"kind": "other", "item_id": "x"}], "kind must be"), ([device_req(zz=1)], "unknown key"),
               ([device_req(item_id="")], "item_id must be"), ([device_req(in_a=0)], "in_a must be"), ([device_req(poles=7)], "poles must be"),
               ([device_req(circuits="A")], "circuits must be a list"), ([device_req(circuits=[1])], "circuits must be a list"), ([cable_req(s_mm2=None)], "s_mm2 must be"),
               ([cable_req(insulation=3)], "insulation must be"), ([device_req(), device_req()], "duplicate requirement")]
        for value, message in bad:
            with self.assertRaisesRegex(ValueError, message):
                build_datasheets("TG-1", value, [])

    def test_optional_fields_default_to_none(self):
        req = build_datasheets("TG-1", [{"item_id": "X", "kind": "protective_device", "circuits": []}], [])["datasheets"][0]["requirement"]
        self.assertEqual((req["device_kind"], req["in_a"], req["poles"], req["voltage_v"]), (None, None, None, None))


class CatalogValidationTests(unittest.TestCase):
    def fails(self, catalog, message):
        with self.assertRaisesRegex(ValueError, message):
            catalog_mod.products(catalog)

    def test_structure(self):
        self.fails("x", "must be a list")
        self.fails([1], "must be an object")
        self.fails([{"category": "breakers", "products": []}], "required key manufacturer")
        self.fails([{"manufacturer": "m", "category": " ", "products": []}], "required key category")
        self.fails([{"manufacturer": "m", "category": "breakers", "products": {}}], "products must be a list")
        self.fails([document(products=[1])], "must be an object")
        self.fails([document(products=[{"id": "p"}])], "missing or empty required key")
        self.fails([document(products=[product("p", status="maybe")])], "status must be")
        self.fails([document(products=[product("p"), product("p")])], "duplicate product id")

    def test_numbers(self):
        self.fails([document(products=[product("p", rated_current_a="x")])], "rated_current_a must be")
        self.fails([document(products=[product("p", rated_current_a={"max": "a"})])], "rated_current_a.max")
        self.fails([document(products=[product("p", rated_current_a={"top": 1})])], "unknown key")
        self.fails([document(products=[product("p", rated_current_a={"min": 5, "max": 1})])], "min is greater")
        self.fails([document(products=[product("p", rated_current_a=[True])])], "rated_current_a entry")
        self.fails([document(products=[product("p", breaking_capacity="x")])], "breaking_capacity must be a list")
        self.fails([document(products=[product("p", breaking_capacity=[{"voltage_v": 400}])])], "needs voltage_v and icu_ka")
        self.fails([document(products=[product("p", breaking_capacity=[1])])], "needs voltage_v and icu_ka")
        self.fails([document(products=[product("p", breaking_capacity=[{"voltage_v": 400, "icu_ka": 0}])])], "icu_ka")
        self.fails([document(products=[product("p", breaking_capacity=[{"voltage_v": float("nan"), "icu_ka": 1}])])], "voltage_v")
        self.fails([document(products=[product("p", poles=[5])])], "poles must be")
        self.fails([document(products=[product("p", poles=3)])], "poles must be")

    def test_products_flatten_and_sort(self):
        flat = catalog_mod.products([document("b", products=[product("p2", family="Z")]), document("a", products=[product("p1", family="Y")], manufacturer_name="A Co")])
        self.assertEqual([(p["manufacturer"], p["id"]) for p in flat], [("a", "p1"), ("b", "p2")])
        self.assertEqual(flat[0]["manufacturer_name"], "A Co")
        self.assertNotIn("manufacturer_name", flat[1])


class LoadCatalogDirTests(unittest.TestCase):
    def write(self, root, manufacturer, files):
        folder = Path(root) / manufacturer
        folder.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (folder / name).write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")

    def good(self, root, name="m1"):
        self.write(root, name, {"manufacturer.json": {"id": name, "name": name.upper(), "categories": ["breakers", "cables"]},
                                "breakers.json": document(name, products=[product(f"{name}-b")]),
                                "cables.json": document(name, "cables", [product(f"{name}-c")])})

    def fails(self, path, message):
        with self.assertRaisesRegex(ValueError, message):
            load_catalog_dir(path)

    def test_reads_a_folder(self):
        with tempfile.TemporaryDirectory() as root:
            self.good(root, "m2")
            self.good(root, "m1")
            (Path(root) / "README.txt").write_text("not a manufacturer", encoding="utf-8")
            catalog = load_catalog_dir(root)
            self.assertEqual([(d["manufacturer"], d["category"], d["manufacturer_name"]) for d in catalog],
                             [("m1", "breakers", "M1"), ("m1", "cables", "M1"), ("m2", "breakers", "M2"), ("m2", "cables", "M2")])
            self.assertEqual(len(build_datasheets("TG-1", [device_req()], catalog)["datasheets"][0]["candidates"]), 2)
            self.assertEqual(len(load_catalog_dir(str(root))), 4)

    def test_folder_errors(self):
        self.fails("no-such-folder-xyz", "catalog folder not found")
        with tempfile.TemporaryDirectory() as root:
            self.fails(root, "no manufacturer folder")

    def test_manufacturer_file_errors(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root, "m1", {"breakers.json": document("m1")})
            self.fails(root, "manufacturer.json not found")
        for bad, message in (({"id": "m1", "categories": ["breakers"]}, "required key name"), ({"id": "m1", "name": "M", "categories": []}, "categories must be"),
                             ([1], "required key id")):
            with tempfile.TemporaryDirectory() as root:
                self.write(root, "m1", {"manufacturer.json": bad, "breakers.json": document("m1")})
                self.fails(root, message)

    def test_product_file_errors(self):
        info = {"id": "m1", "name": "M", "categories": ["breakers"]}
        cases = (({"manufacturer.json": info}, "no product file"), ({"manufacturer.json": info, "breakers.json": document("other")}, "manufacturer must be"),
                 ({"manufacturer.json": info, "breakers.json": [1]}, "manufacturer must be"), ({"manufacturer.json": info, "breakers.json": "{not json"}, "not valid JSON"),
                 ({"manufacturer.json": info, "breakers.json": document("m1", products=[{"id": "x"}])}, "missing or empty required key"))
        for files, message in cases:
            with tempfile.TemporaryDirectory() as root:
                self.write(root, "m1", files)
                self.fails(root, message)

    def test_unreadable_file(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root, "m1", {"manufacturer.json": {"id": "m1", "name": "M", "categories": ["breakers"]}})
            (Path(root) / "m1" / "breakers.json").mkdir()          # a folder where a file is expected is not a file: skipped
            self.fails(root, "no product file")
            with self.assertRaisesRegex(ValueError, "cannot read"):
                catalog_mod._read_json(Path(root) / "m1" / "breakers.json")

    def test_real_catalog_read_only(self):
        self.assertTrue(REAL_CATALOG.is_dir(), REAL_CATALOG)
        catalog = load_catalog_dir(REAL_CATALOG)
        self.assertEqual(sorted({d["manufacturer"] for d in catalog}), ["abb", "prysmian", "schneider-electric", "siemens"])
        flat = catalog_mod.products(catalog)
        self.assertTrue(all(p["status"] == "unverified" for p in flat))
        result = build_datasheets("TG-1", [device_req(device_kind="mccb", in_a=100, poles=None, breaking_capacity_ka=25, voltage_v=380),
                                           device_req("DS-DEV-002", device_kind="mccb", in_a=100, breaking_capacity_ka=500),
                                           cable_req(insulation="pvc")], catalog)
        first = result["datasheets"][1]
        self.assertEqual([c["product_id"] for c in first["candidates"]], ["abb-tmax-xt1"])
        self.assertEqual(first["candidates"][0]["catalog_status"], "unverified")
        self.assertEqual(result["datasheets"][2]["candidates"], [])
        self.assertEqual([c["product_id"] for c in result["datasheets"][0]["candidates"]], ["prysmian-sintenax-valio"])
        self.assertEqual(result["datasheets"][0]["kind"], "cable")


class MatchTests(unittest.TestCase):
    def test_helpers(self):
        self.assertTrue(match.rated_current_contains([6, 10], 10))
        self.assertFalse(match.rated_current_contains(None, 10))
        self.assertTrue(match.mentions("RZ1-R, XLPE.", "xlpe"))
        self.assertFalse(match.mentions("PVCX", "pvc"))

    def test_public_surface(self):
        self.assertEqual(sorted(epc_datasheets.__all__), ["build_datasheets", "load_catalog_dir", "render_rows", "requirements_from_circuits"])


if __name__ == "__main__":
    unittest.main()
