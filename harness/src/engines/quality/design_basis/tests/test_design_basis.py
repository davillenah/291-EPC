"""Tests of the design-basis engine: pure functions, synthetic profiles. Limits are compared with direct calls to the engines' accessors."""
import ast
import copy
import importlib
import unittest
from pathlib import Path
from unittest import mock

import epc_design_basis
from epc_design_basis import build, build_design_basis_document, design_basis_to_text, limits, text
from epc_grounding import aea_earthing as GR
from epc_load_balance import system_voltage as SV
from epc_short_circuit import short_circuit as SC
from epc_voltage_drop import aea_voltage_drop as VD


def profile(**supply):
    base = {"project_code": "P-1", "client": {"name": "Cliente SA", "contact": None}, "site": {"address": "Calle 1", "country": "AR", "installation_type": "dwelling"},
            "supply": {"source": "utility", "voltage": {"value": 400, "unit": "V"}, "earthing_system": "TN",
                       "short_circuit_level": {"value": 10, "unit": "kA", "origin": "utility letter"}},
            "normative_profile": {"jurisdiction": "AR", "revisions": {"90364-7-771": "2006", "parts_4_and_5": None}},
            "criteria": {"set": "default", "exceptions": ["E1"]}, "language": "es"}
    base["supply"].update(supply)
    return base


def items(doc, section):
    return {i["key"]: i for s in doc["sections"] if s["id"] == section for i in s["items"]}


class BuildTests(unittest.TestCase):
    def test_sections_and_copied_data(self):
        doc = build_design_basis_document(profile(), criteria={"exceptions": ["E2"]}, assumptions=[{"text": "t", "reason": "r"}],
                                          requirements={"items": [{"id": "R-001", "text": "x", "source": "client", "status": "open"}, {"id": "R-002", "text": "y", "source": "c", "status": "confirmed"}]})
        self.assertEqual([s["id"] for s in doc["sections"]], ["identification", "supply", "normative_profile", "design_criteria", "assumptions", "requirements", "values_note"])
        self.assertEqual(doc["status"], "draft")
        ident = items(doc, "identification")
        self.assertEqual((ident["project_code"]["value"], ident["client_name"]["value"], ident["site_address"]["value"], ident["language"]["value"]), ("P-1", "Cliente SA", "Calle 1", "es"))
        supply = items(doc, "supply")
        self.assertEqual((supply["earthing_system"]["value"], supply["short_circuit_level"]["value"], supply["short_circuit_level"]["unit"], supply["short_circuit_origin"]["value"]),
                         ("TN", 10, "kA", "utility letter"))
        self.assertEqual(supply["supply_voltage"]["unit"], "V")
        norms = items(doc, "normative_profile")
        self.assertEqual((norms["jurisdiction"]["value"], norms["revision.90364-7-771"]["value"], norms["revision.parts_4_and_5"]["value"]), ("AR", "2006", None))
        crit = items(doc, "design_criteria")
        self.assertEqual((crit["criteria_set"]["value"], crit["criteria_exceptions"]["value"]), ("default", ["E1", "E2"]))
        self.assertEqual(doc["assumptions"], [{"id": "A-01", "text": "t", "reason": "r"}])
        self.assertEqual(items(doc, "assumptions")["A-01"]["source"], "r")
        self.assertEqual(doc["open_items"], ["R-001"])
        reqs = items(doc, "requirements")
        self.assertEqual((reqs["R-001"]["value"], reqs["R-001"]["status"], reqs["R-002"]["source"]), ("x", "open", "c"))
        self.assertIn("draft", items(doc, "values_note")["what_the_values_mean"]["value"])
        self.assertEqual(doc["issues"], [])

    def test_deterministic_and_inputs_not_modified(self):
        p = profile()
        before = copy.deepcopy(p)
        a, b = build_design_basis_document(p), build_design_basis_document(p)
        self.assertEqual(a, b)
        self.assertEqual(p, before)
        a["sections"][0]["items"][0]["value"] = "changed"
        self.assertEqual(p, before)

    def test_missing_d24_data_lists_the_fields(self):
        p = profile(earthing_system=None, short_circuit_level={})
        with self.assertRaises(ValueError) as ctx:
            build_design_basis_document(p)
        self.assertIn("supply.earthing_system", str(ctx.exception))
        self.assertIn("supply.short_circuit_level", str(ctx.exception))
        with self.assertRaises(ValueError) as one:
            build_design_basis_document(profile(earthing_system=""))
        self.assertNotIn("short_circuit_level", str(one.exception))
        with self.assertRaises(ValueError):
            build_design_basis_document("x")
        with self.assertRaises(ValueError):
            build_design_basis_document({})

    def test_missing_optional_data_is_none_and_origin_is_an_issue(self):
        doc = build_design_basis_document({"supply": {"earthing_system": "TT", "short_circuit_level": {"value": 5, "unit": "kA"}}})
        self.assertIsNone(items(doc, "identification")["project_code"]["value"])
        self.assertIn("supply.short_circuit_level.origin is missing in the profile", doc["issues"])
        self.assertTrue(any(i.startswith("system_voltage_to_earth:") for i in doc["issues"]))

    def test_assumption_without_reason_is_refused(self):
        for bad in ({"text": "t"}, {"reason": "r"}):
            with self.assertRaises(ValueError):
                build_design_basis_document(profile(), assumptions=[bad])

    def test_criteria_from_the_argument_override_the_set(self):
        doc = build_design_basis_document(profile(), criteria={"set": "other"})
        self.assertEqual(items(doc, "design_criteria")["criteria_set"]["value"], "other")

    def test_insulation_rules(self):
        doc = build_design_basis_document(profile(), insulation_rules={"motor": "xlpe", "feeder": "pvc"}, norm_status={})
        crit = items(doc, "design_criteria")
        self.assertEqual((crit["insulation_by_role.motor"]["value"], crit["insulation_by_role.feeder"]["review_status"]), ("xlpe", "pending review"))
        self.assertEqual(crit["insulation_by_role.motor"]["source"], "caller (insulation_rules)")
        for bad in ("x", {"a": 1}, {1: "a"}):
            with self.assertRaises(ValueError):
                build_design_basis_document(profile(), insulation_rules=bad)


class LimitTests(unittest.TestCase):
    def setUp(self):
        self.doc = build_design_basis_document(profile())
        self.crit = items(self.doc, "design_criteria")

    def test_limits_equal_direct_calls_to_the_engines(self):
        for kind in ("iluminacion", "tomacorrientes", "seccional", "motor_regimen", "motor_arranque"):
            entry = self.crit[f"voltage_drop_limit.{kind}"]
            self.assertEqual((entry["value"], entry["unit"], entry["source"]), (VD.limite_caida_pct(kind), "%", "epc_voltage_drop.aea_voltage_drop.limite_caida_pct"))
        self.assertEqual(self.crit["disconnection_time.sectional.TT"]["value"], GR.tiempo_seccional_max_s("TT"))
        self.assertEqual(self.crit["disconnection_time.sectional.TN"]["value"], GR.tiempo_seccional_max_s("TN"))
        self.assertEqual(self.crit["disconnection_time.sectional.TN_selectivity"]["value"], GR.tiempo_seccional_max_s("TN", selectividad=True))
        self.assertEqual(self.crit["c_min"]["value"], SC.C_MIN_BT)
        self.assertEqual(self.crit["c_min"]["source"], "epc_short_circuit.short_circuit.C_MIN_BT")
        self.assertEqual(self.crit["system_voltage_to_earth"]["value"], SV.system_u0(400))
        self.assertEqual(self.crit["disconnection_time.table.TN"]["value"], GR.tiempo_desconexion_max_s("TN", SV.system_u0(400)))
        self.assertNotIn("disconnection_time.table.TT", self.crit)

    def test_tt_scheme_reads_the_tt_table(self):
        crit = items(build_design_basis_document(profile(earthing_system="TT")), "design_criteria")
        self.assertEqual(crit["disconnection_time.table.TT"]["value"], GR.tiempo_desconexion_max_s("TT", SV.system_u0(400)))

    def test_every_limit_is_pending_review_by_default_and_records_are_listed(self):
        limit_items = [i for k, i in self.crit.items() if k.startswith(("voltage_drop", "disconnection", "c_min", "system_voltage_to_earth"))]
        self.assertTrue(limit_items)
        self.assertEqual({i["review_status"] for i in limit_items}, {"pending review"})
        self.assertIn("aea90364.constant.771-19-limites-caida-pct", self.doc["norm_records"])
        self.assertEqual(len(self.doc["norm_records"]), len(set(self.doc["norm_records"])))

    def test_undefined_voltage_is_an_issue_not_a_guess(self):
        doc = build_design_basis_document(profile(voltage={"value": 415, "unit": "V"}))
        crit = items(doc, "design_criteria")
        self.assertNotIn("system_voltage_to_earth", crit)
        self.assertNotIn("disconnection_time.table.TN", crit)
        self.assertTrue(any(i.startswith("system_voltage_to_earth: cannot be read from epc_load_balance.system_voltage.system_u0") for i in doc["issues"]))
        self.assertIn("disconnection_time.table.TN: needs U0, which could not be read", doc["issues"])
        self.assertNotIn("aea90364.code.system_voltage.u0_380", doc["norm_records"])

    def test_voltage_missing_or_not_in_volts(self):
        for voltage in (None, {"value": None, "unit": "V"}, {"value": 400, "unit": "kV"}):
            doc = build_design_basis_document(profile(voltage=voltage))
            self.assertTrue(any("supply.voltage" in i for i in doc["issues"]))

    def test_it_scheme_has_no_table_time(self):
        doc = build_design_basis_document(profile(earthing_system="IT"))
        self.assertTrue(any("earthing system 'IT'" in i for i in doc["issues"]))

    def test_an_unreadable_accessor_becomes_an_issue(self):
        with mock.patch.object(VD, "limite_caida_pct", new=None):
            doc = build_design_basis_document(profile())
        self.assertFalse([k for k in items(doc, "design_criteria") if k.startswith("voltage_drop")])
        self.assertEqual(len([i for i in doc["issues"] if i.startswith("voltage_drop_limit.")]), 5)
        self.assertNotIn("aea90364.constant.771-19-limites-caida-pct", doc["norm_records"])

    def test_a_missing_attribute_and_a_missing_module(self):
        spec = limits.Spec("k", "l", None, "epc_voltage_drop.aea_voltage_drop", "no_such_function", None, {}, ())
        self.assertIn("no_such_function", limits.read(spec)[1])
        gone = spec._replace(module="epc_no_such_engine")
        self.assertIn("cannot be read", limits.read(gone)[1])
        self.assertEqual(limits.read(spec._replace(name="limite_caida_pct", args=("seccional",))), (VD.limite_caida_pct("seccional"), None))

    def test_norm_status_passthrough_and_combination(self):
        ids = {"aea90364.constant.771-19-limites-caida-pct": "verified", "aea90364.code.system_voltage.u0_380": "verified", "aea90364.code.board_memo.u0_v": "rejected",
               "aea90364.code.aea_pipeline.c_min_bt": "rejected"}
        crit = items(build_design_basis_document(profile(), norm_status=ids), "design_criteria")
        self.assertEqual(crit["voltage_drop_limit.seccional"]["review_status"], "verified")
        self.assertEqual(crit["system_voltage_to_earth"]["review_status"], "rejected")
        self.assertEqual(crit["c_min"]["review_status"], "rejected")
        self.assertEqual(crit["disconnection_time.sectional.TT"]["review_status"], "pending review")
        half = {"aea90364.code.system_voltage.u0_380": "verified"}
        self.assertEqual(items(build_design_basis_document(profile(), norm_status=half), "design_criteria")["system_voltage_to_earth"]["review_status"], "pending review")
        self.assertEqual(limits.review_status((), {}), "pending review")

    def test_all_records_verified_gives_verified(self):
        self.assertEqual(limits.review_status(("a", "b"), {"a": "verified", "b": "verified"}), "verified")

    def test_invalid_norm_status_is_refused(self):
        for bad in ({"a": "approved"}, ["x"]):
            with self.assertRaises(ValueError):
                build_design_basis_document(profile(), norm_status=bad)


class TextTests(unittest.TestCase):
    def setUp(self):
        self.doc = build_design_basis_document(profile(voltage={"value": 415, "unit": "V"}), assumptions=[{"text": "algo", "reason": "porque"}],
                                               requirements={"items": [{"id": "R-001", "text": "pedido", "source": "cliente", "status": "open"}]},
                                               insulation_rules={"motor": "xlpe"}, norm_status={"aea90364.constant.771-19-limites-caida-pct": "verified"})

    def test_text_has_values_and_spanish_words(self):
        out = design_basis_to_text(self.doc)
        for needle in ("BASE DE DISENO", "P-1", "Cliente SA", "TN", "pendiente de revision", "verificado", "Supuesto A-01", "algo", "porque", "Requisito R-001", "pedido",
                       "Puntos abiertos", "Observaciones", "Aislacion segun el rol: motor", "xlpe", "sin dato", "utility letter"):
            self.assertIn(needle, out)
        self.assertIn(f"{VD.limite_caida_pct('seccional')} %", out)
        self.assertEqual(out, design_basis_to_text(copy.deepcopy(self.doc)))

    def test_sections_are_numbered_by_position(self):
        lines = design_basis_to_text(self.doc).splitlines()
        self.assertIn("1. Identificacion del proyecto", lines)
        self.assertIn("7. Que significan los valores", lines)

    def test_fallbacks(self):
        doc = {"sections": [{"id": "x", "title": "Own title", "items": [{"key": "k", "label": "Own label", "value": ["a", "b"], "unit": None, "source": None, "review_status": "weird"},
                                                                        {"key": "e", "label": "E", "value": [], "unit": None, "source": None, "review_status": None}]}]}
        out = design_basis_to_text(doc)
        self.assertIn("Own title", out)
        self.assertIn("- Own label: a, b (estado: weird)", out)
        self.assertIn("- E: sin dato", out)
        self.assertNotIn("Observaciones", out)

    def test_invalid_document(self):
        for bad in (None, {}, "x"):
            with self.assertRaises(ValueError):
                design_basis_to_text(bad)

    def test_templates_contain_no_digit(self):
        tree = ast.parse(Path(text.__file__).read_text(encoding="utf-8"))
        strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertTrue(strings)
        self.assertEqual([s for s in strings if any(c.isdigit() for c in s)], [])


class PackageTests(unittest.TestCase):
    def test_public_api(self):
        self.assertEqual(sorted(epc_design_basis.__all__), ["build_design_basis_document", "design_basis_to_text"])
        self.assertEqual(epc_design_basis.__version__, "0.1.0")
        self.assertIs(importlib.import_module("epc_design_basis.build"), build)

    def test_no_import_of_the_orchestrator(self):
        for path in Path(build.__file__).parent.glob("*.py"):
            self.assertNotIn("import epc_aea90364", path.read_text(encoding="utf-8"))
            self.assertNotIn("from epc_aea90364", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
