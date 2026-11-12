"""Tests of the descriptive-report engine: pure functions, synthetic inputs."""
import ast
import copy
import importlib
import unittest
from pathlib import Path

import epc_descriptive_report
from epc_descriptive_report import build, build_descriptive_report, descriptive_report_to_text, text


def entry(key, value, unit=None, review=None, label=None):
    return {"key": key, "label": label or key, "value": value, "unit": unit, "source": "x", "review_status": review}


def design_basis():
    return {"sections": [
        {"id": "identification", "title": "t", "items": [entry("project_code", "P-1"), entry("client_name", "Cliente SA"), entry("site_address", "Calle 1"),
                                                         entry("site_country", "AR"), entry("site_installation_type", "dwelling"), entry("language", "es")]},
        {"id": "supply", "title": "t", "items": [entry("supply_source", "utility"), entry("supply_voltage", 400, "V"), entry("earthing_system", "TN"),
                                                 entry("short_circuit_level", 10, "kA"), entry("short_circuit_origin", "utility letter")]},
        {"id": "normative_profile", "title": "t", "items": [entry("jurisdiction", "AR"), entry("revision.90364-7-771", "2006", label="Revision of 90364-7-771"),
                                                              entry("revision.parts", "2022", label="Revision of parts")]},
        {"id": "design_criteria", "title": "t", "items": [entry("criteria_set", "default"), entry("disconnection_time.sectional.TN", 5, "s", "pending review", "Max time TN"),
                                                          entry("c_min", 0.95)]}],
        "open_items": ["R-1", "R-2"]}


def circuits():
    return [{"tag": "C1", "kind": "lighting", "phases": 1, "device_kind": "MCB", "s_mm2": 1.5, "material": "Cu", "insulation": "PVC", "length_m": 10},
            {"tag": "C2", "kind": "lighting", "phases": 1, "device_kind": "MCB", "s_mm2": 1.5, "material": "Cu", "insulation": "PVC"},
            {"tag": "C3", "kind": "motor", "phases": 3, "device_kind": "MCCB", "s_mm2": 10, "material": "Cu", "insulation": "XLPE"},
            {"tag": "F1", "phases": 3, "s_mm2": 25}]


def full():
    return build_descriptive_report(design_basis(), circuits(), terminals={"totals": {"terminals": 12}}, boq={"totals": {"lines": 7, "devices": 4, "cable_m": 55.5}},
                                    pending_documents=[{"name": "specification", "status": "planned"}, {"name": "BOQ", "status": "planned", "reason": "no_allowance_pct"}],
                                    unreviewed_norm_records=9)


def items(doc, section):
    return {i["key"]: i for s in doc["sections"] if s["id"] == section for i in s["items"]}


class BuildTests(unittest.TestCase):
    def test_sections_and_shape(self):
        doc = full()
        self.assertEqual([s["id"] for s in doc["sections"]], list(build.ORDER))
        self.assertEqual((doc["status"], doc["norm_records"], doc["issues"]), ("draft", [], []))
        self.assertTrue(doc["assumptions"])
        self.assertTrue(all(set(i) >= {"key", "label", "value", "unit", "source", "review_status"} for s in doc["sections"] for i in s["items"]))

    def test_copied_values(self):
        doc = full()
        ident, supply, norms = items(doc, "object_scope"), items(doc, "supply_earthing"), items(doc, "standards")
        self.assertEqual((ident["project_code"]["value"], ident["site_address"]["value"], ident["project_code"]["source"]), ("P-1", "Calle 1", "design_basis.identification.project_code"))
        self.assertEqual((supply["supply_voltage"]["value"], supply["supply_voltage"]["unit"], supply["earthing_system"]["value"]), (400, "V", "TN"))
        self.assertEqual((norms["jurisdiction"]["value"], norms["revision.parts"]["value"], norms["criteria_set"]["value"]), ("AR", "2022", "default"))

    def test_counts_by_type_phases_and_total(self):
        org = items(full(), "board_organisation")
        self.assertEqual(org["circuits_total"]["value"], 4)
        self.assertEqual((org["circuits_by_type.lighting"]["value"], org["circuits_by_type.motor"]["value"], org["circuits_by_type.not specified"]["value"]), (2, 1, 1))
        self.assertEqual((org["circuits_by_phases.1"]["value"], org["circuits_by_phases.3"]["value"]), (2, 2))
        self.assertEqual(org["circuits_total"]["source"], build.COUNT_SOURCE)
        self.assertIn("Counting is the only arithmetic", " ".join(full()["assumptions"]))

    def test_phases_not_specified(self):
        doc = build_descriptive_report(design_basis(), [{"tag": "A"}])
        org = items(doc, "board_organisation")
        self.assertEqual((org["circuits_by_phases.not specified"]["value"], org["circuits_by_type.not specified"]["value"]), (1, 1))

    def test_cable_specifications_listed_with_counts(self):
        cab = items(full(), "cables_installation")
        self.assertEqual(cab["cable_specs_distinct"]["value"], 4 - 1)
        self.assertEqual(cab["cable_spec.Cu|PVC|1.5"]["value"], 2)
        self.assertEqual(cab["cable_spec.Cu|XLPE|10"]["spec"], {"material": "Cu", "insulation": "XLPE", "section": "10", "section_unit": "mm2"})
        self.assertEqual(cab["cable_spec.Cu|PVC|1.5"]["label"], "Cu / PVC / 1.5")
        other = cab["cable_spec.not specified|not specified|25"]
        self.assertEqual((other["value"], other["spec"]["material"]), (1, "not specified"))
        none = items(build_descriptive_report(design_basis(), [{"tag": "A"}]), "cables_installation")["cable_spec.not specified|not specified|"]
        self.assertEqual((none["label"], none["spec"]["section"], none["spec"]["section_unit"]), ("not specified / not specified / not specified", None, None))

    def test_terminals_and_boq_counts(self):
        cab = items(full(), "cables_installation")
        self.assertEqual((cab["terminals_total"]["value"], cab["boq_lines"]["value"], cab["boq_devices"]["value"], cab["boq_cable_m"]["value"], cab["boq_cable_m"]["unit"]),
                         (12, 7, 4, 55.5, "m"))
        whole = build_descriptive_report(design_basis(), circuits(), terminals={"terminals": 3}, boq={})
        self.assertEqual(items(whole, "cables_installation")["terminals_total"]["value"], 3)
        self.assertIsNone(items(whole, "cables_installation")["boq_lines"]["value"])

    def test_protection_section(self):
        prot = items(full(), "protection_earthing")
        self.assertEqual((prot["protective_device.MCB"]["value"], prot["protective_device.MCCB"]["value"], prot["protective_device.not specified"]["value"]), (2, 1, 1))
        self.assertEqual((prot["earthing_system"]["value"], prot["disconnection_time.sectional.TN"]["review_status"]), ("TN", "pending review"))

    def test_status_section(self):
        st = items(full(), "status_limitations")
        self.assertIn("D21", st["draft_notice"]["value"])
        self.assertEqual((st["pending_documents_total"]["value"], st["pending.specification"]["value"], st["pending.BOQ"]["value"]), (2, "planned", "no_allowance_pct"))
        self.assertEqual((st["unreviewed_norm_records"]["value"], st["open_requirements"]["value"]), (9, 2))
        self.assertNotIn("open_requirements", items(build_descriptive_report({"sections": []}, circuits()), "status_limitations"))

    def test_missing_optionals_are_issues_and_omitted(self):
        doc = build_descriptive_report(design_basis(), circuits())
        self.assertEqual([i for i in doc["issues"] if i.startswith("not provided")],
                         ["not provided: terminals", "not provided: boq", "not provided: pending_documents", "not provided: unreviewed_norm_records"])
        keys = {i["key"] for s in doc["sections"] for i in s["items"]}
        self.assertFalse(keys & {"terminals_total", "boq_lines", "pending_documents_total", "unreviewed_norm_records"})

    def test_missing_design_basis_parts_are_issues(self):
        doc = build_descriptive_report({"sections": [{"id": "supply", "items": [entry("earthing_system", "TT")]}, "junk", {"id": "x", "items": "no"}]}, circuits())
        self.assertIn("design basis: section identification not found", doc["issues"])
        self.assertIn("design basis: item supply.supply_source not found", doc["issues"])
        self.assertIn("design basis: section normative_profile not found", doc["issues"])
        self.assertEqual(items(doc, "supply_earthing")["earthing_system"]["value"], "TT")

    def test_required_inputs(self):
        for bad in (None, {}, {"sections": "x"}, "x"):
            with self.assertRaises(ValueError):
                build_descriptive_report(bad, circuits())
        for bad in (None, [], "x", [{"tag": ""}], ["x"], [{"tag": "A"}, {"tag": "A"}], [{"tag": "A", "s_mm2": 0}], [{"tag": "A", "s_mm2": "1"}], [{"tag": "A", "s_mm2": True}]):
            with self.assertRaises(ValueError):
                build_descriptive_report(design_basis(), bad)

    def test_optional_inputs_validated(self):
        for kwargs in ({"terminals": []}, {"boq": "x"}, {"pending_documents": {}}, {"pending_documents": [{"status": "x"}]}, {"pending_documents": ["x"]},
                       {"unreviewed_norm_records": -1}, {"unreviewed_norm_records": 1.5}, {"unreviewed_norm_records": True}):
            with self.assertRaises(ValueError, msg=str(kwargs)):
                build_descriptive_report(design_basis(), circuits(), **kwargs)

    def test_deterministic_and_inputs_untouched(self):
        db, rows = design_basis(), circuits()
        before = copy.deepcopy((db, rows))
        a, b = build_descriptive_report(db, rows), build_descriptive_report(db, rows)
        self.assertEqual(a, b)
        self.assertEqual((db, rows), before)
        a["sections"][0]["items"][0]["value"] = "changed"
        self.assertEqual(db, before[0])


class TextTests(unittest.TestCase):
    def test_full_text(self):
        out = descriptive_report_to_text(full())
        for fragment in ("MEMORIA DESCRIPTIVA (borrador)", "1. Objeto y alcance", "proyecto P-1, del cliente Cliente SA, ubicada en Calle 1 (AR).", "Tipo de instalacion: dwelling.",
                         "se alimenta desde utility.", "La tension de alimentacion es 400 V.", "El esquema de puesta a tierra es TN.",
                         "El nivel de cortocircuito disponible es 10 kA, segun utility letter.", "compuesto por 4 circuitos.", "lighting: 2", "sin especificar: 1",
                         "Cu, PVC, seccion 1.5 mm2: 2 circuitos", "Cu, PVC, seccion 1.5 mm2: 2 circuitos; Cu, XLPE", "not specified, not specified, seccion 25 mm2: 1 circuitos",
                         "La lista de bornes contiene 12 bornes.", "7 lineas, 4 dispositivos de proteccion y 55.5 m.", "MCB: 2", "Max time TN: 5 s",
                         "Revision of 90364-7-771: 2006", "Conjunto de criterios de diseno: default", "(D21)", "specification: planned; BOQ: no_allowance_pct",
                         "sin revisar: 9.", "abiertos de la base de diseno: 2."):
            self.assertIn(fragment, out)
        self.assertNotIn("Observaciones", out)

    def test_missing_optionals_omit_sentences_and_list_issues(self):
        out = descriptive_report_to_text(build_descriptive_report(design_basis(), [{"tag": "A"}]))
        self.assertNotIn("lista de bornes", out)
        self.assertNotIn("computo", out)
        self.assertNotIn("Documentos pendientes", out)
        self.assertNotIn("sin revisar:", out)
        self.assertIn("seccion sin especificar: 1 circuitos", out)
        self.assertIn("Observaciones\n- not provided: terminals", out)

    def test_nothing_is_invented_without_data(self):
        out = descriptive_report_to_text(build_descriptive_report({"sections": []}, [{"tag": "A"}]))
        self.assertNotIn("Esta memoria describe", out)
        self.assertNotIn("se alimenta", out)
        self.assertNotIn("jurisdiccion", out)

    def test_partial_object_and_supply(self):
        doc = {"sections": [{"id": "object_scope", "title": "t", "items": [entry("project_code", "P"), entry("site_address", None)]},
                            {"id": "supply_earthing", "title": "t", "items": [entry("short_circuit_level", 5, "kA"), entry("short_circuit_origin", None)]},
                            {"id": "unknown", "title": "t", "items": []},
                            {"id": "board_organisation", "title": "t", "items": []}], "issues": []}
        out = descriptive_report_to_text(doc)
        self.assertIn("proyecto P.", out)
        self.assertIn("El nivel de cortocircuito disponible es 5 kA.", out)
        self.assertNotIn("ubicada", out)
        self.assertIn("4. Organizacion del tablero\n\n", out)

    def test_unknown_section_id_has_no_body(self):
        out = descriptive_report_to_text({"sections": [{"id": "zzz", "title": "Own title", "items": []}]})
        self.assertIn("1. Own title\n\n", out)

    def test_status_without_notice_source(self):
        doc = {"sections": [{"id": "status_limitations", "title": "t", "items": [{"key": "draft_notice", "value": "x", "source": None},
                                                                                  {"key": "pending.A", "value": None}]}]}
        out = descriptive_report_to_text(doc)
        self.assertNotIn("borrador y no puede", out)
        self.assertNotIn("Documentos pendientes", out)

    def test_invalid_document(self):
        for bad in (None, {}, "x", {"sections": "x"}):
            with self.assertRaises(ValueError):
                descriptive_report_to_text(bad)

    def test_deterministic(self):
        self.assertEqual(descriptive_report_to_text(full()), descriptive_report_to_text(full()))

    def test_templates_contain_no_digit(self):
        tree = ast.parse(Path(text.__file__).read_text(encoding="utf-8"))
        strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertTrue(strings)
        self.assertEqual([s for s in strings if any(c.isdigit() for c in s)], [])


class PackageTests(unittest.TestCase):
    def test_public_api(self):
        self.assertEqual(sorted(epc_descriptive_report.__all__), ["build_descriptive_report", "descriptive_report_to_text"])
        self.assertEqual(epc_descriptive_report.__version__, "0.1.0")
        self.assertIs(importlib.import_module("epc_descriptive_report.build"), build)

    def test_no_forbidden_imports(self):
        for path in Path(build.__file__).parent.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            for name in ("import disciplines", "from disciplines", "import platform", "epc_aea90364", "open("):
                self.assertNotIn(name, source, path.name)


if __name__ == "__main__":
    unittest.main()
