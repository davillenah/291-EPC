"""Tests of the RFQ engine: pure functions, small synthetic bills of quantities and datasheets."""
import copy
import re
import unittest

import epc_rfq
from epc_rfq import build, build_rfq, inputs, render_rows, rfq_to_text, text


def supplier(name="Alfa", contact=None):
    return {"name": name, "contact": contact} if contact else {"name": name}


def terms(**changes):
    base = {"suppliers": [supplier("Alfa", "alfa@example.test"), supplier("Beta")], "currency": "ARS", "response_deadline": "2026-12-15",
            "delivery_site": "Obra Central", "validity_days": 30}
    base.update(changes)
    return base


def item(item_id, category="cable", **changes):
    base = {"item_id": item_id, "category": category, "description": f"desc {item_id}", "unit": "m", "quantity": 12.5, "source": ["B", "A"], "issues": [],
            "basis": "x", "spec": {}}
    base.update(changes)
    return base


CABLE_SPEC = {"material": "cu", "insulation": "pvc", "phase_conductors": 3, "s_mm2": 10, "neutral_mm2": 10, "pe_mm2": 10, "cores": 5}
DEVICE_SPEC = {"kind": "mccb", "in_a": 100, "poles": 3, "breaking_capacity_ka": 25}


def boq(items=None):
    return {"board": "TG-1", "items": items if items is not None else [
        item("DEV-001", "protective_device", unit="un", quantity=2, spec=DEVICE_SPEC),
        item("CAB-001", spec=CABLE_SPEC),
        item("ENC-001", "enclosure", unit="un", quantity=1, spec={"board": "TG-1"}),
        item("TRM-001", "terminal_block", unit="un", quantity=8, spec={"size_mm2": 2.5})]}


def candidate(manufacturer, pid, family="Fam", **changes):
    base = {"manufacturer": manufacturer, "product_id": pid, "family": family, "source": f"https://example.test/{pid}", "catalog_status": "unverified",
            "category": "breakers", "matched": {}, "unconfirmed": []}
    base.update(changes)
    return base


def datasheets():
    return {"board": "TG-1", "datasheets": [
        {"item_id": "DS-DEV-001", "kind": "protective_device", "requirement": {"device_kind": "mccb", "in_a": 100, "poles": 3, "breaking_capacity_ka": 25, "circuits": ["A"]},
         "candidates": [candidate("zeta", "z1", "Zed"), candidate("abb", "a2", "Tmax"), candidate("abb", "a1", "Tmax")], "issues": []},
        {"item_id": "DS-DEV-002", "kind": "protective_device", "requirement": {"device_kind": "mccb", "in_a": 100, "poles": 3, "breaking_capacity_ka": 25},
         "candidates": [candidate("abb", "a1", "Tmax")], "issues": []},
        {"item_id": "DS-CAB-001", "kind": "cable", "requirement": dict(CABLE_SPEC, circuits=["A"]),
         "candidates": [candidate("prysmian", "c1", None, source=None, catalog_status="verified")], "issues": []}]}


def rfq(items=None, **kw):
    args = terms()
    args.update(kw)
    return build_rfq("TG-1", boq(items), **args)


def line(result, item_id):
    return [ln for ln in result["lines"] if ln["item_id"] == item_id][0]


class RequiredTermsTests(unittest.TestCase):
    def test_all_missing_are_listed(self):
        with self.assertRaises(ValueError) as caught:
            build_rfq("TG-1", boq())
        message = str(caught.exception)
        for name in inputs.REQUIRED_TERMS:
            self.assertIn(name, message)

    def test_only_the_missing_ones(self):
        with self.assertRaises(ValueError) as caught:
            rfq(currency=None, delivery_site="  ", suppliers=[])
        self.assertEqual(str(caught.exception), "missing required commercial field(s): suppliers, currency, delivery_site")

    def test_optional_ones_may_be_absent(self):
        result = rfq()
        self.assertEqual((result["terms"]["payment_terms"], result["terms"]["notes"]), (None, None))

    def test_terms_are_copied_as_given(self):
        result = rfq(payment_terms=" 30 dias ", notes="n")
        self.assertEqual(result["terms"], {"currency": "ARS", "response_deadline": "2026-12-15", "delivery_site": "Obra Central", "validity_days": 30,
                                           "payment_terms": "30 dias", "notes": "n"})

    def test_board_name(self):
        for bad in ("", None, 3):
            with self.assertRaises(ValueError):
                build_rfq(bad, boq(), **terms())


class FieldValidationTests(unittest.TestCase):
    def bad(self, **changes):
        with self.assertRaises(ValueError) as caught:
            rfq(**changes)
        return str(caught.exception)

    def test_iso_date(self):
        for value in ("15/12/2026", "2026-1-5", "20261215", "2026-12-15T10:00", "2026-02-30", "2026-13-01"):
            self.assertIn("response_deadline", self.bad(response_deadline=value))
        self.assertIn("response_deadline", self.bad(response_deadline=20261215))
        self.assertEqual(rfq(response_deadline="2028-02-29")["terms"]["response_deadline"], "2028-02-29")

    def test_validity_days(self):
        for value in (0, -3, 2.5, True, "30"):
            self.assertIn("validity_days", self.bad(validity_days=value))

    def test_currency_and_site_are_text(self):
        self.assertIn("currency", self.bad(currency=5))
        self.assertIn("delivery_site", self.bad(delivery_site=["x"]))
        self.assertIn("payment_terms", self.bad(payment_terms=" "))
        self.assertIn("notes", self.bad(notes=3))

    def test_suppliers(self):
        self.assertIn("non-empty list", self.bad(suppliers="Alfa"))
        self.assertIn("must be an object", self.bad(suppliers=["Alfa"]))
        self.assertIn("unknown key", self.bad(suppliers=[{"name": "A", "phone": "1"}]))
        self.assertIn("name", self.bad(suppliers=[{"name": " "}]))
        self.assertIn("contact", self.bad(suppliers=[{"name": "A", "contact": 4}]))
        self.assertIn("duplicate supplier name(s): Alfa", self.bad(suppliers=[supplier("Alfa"), supplier("alfa")]))

    def test_issued_for_keeps_the_caller_order_and_contact(self):
        result = rfq(suppliers=[supplier("Zeta"), supplier("Alfa", "a@x.test")])
        self.assertEqual(result["issued_for"], [{"name": "Zeta", "contact": None}, {"name": "Alfa", "contact": "a@x.test"}])

    def test_boq_shape(self):
        for bad in (None, [], {}, {"items": []}, {"items": "x"}):
            with self.assertRaises(ValueError):
                build_rfq("TG-1", bad, **terms())

    def test_boq_items(self):
        cases = [("must be an object", ["x"]), ("item_id", [item("")]), ("category", [item("A", category=" ")]), ("description", [item("A", description=None)]),
                 ("unit", [item("A", unit=3)]), ("quantity", [item("A", quantity=0)]), ("quantity", [item("A", quantity=True)]),
                 ("quantity", [item("A", quantity=float("inf"))]), ("issues", [item("A", issues="x")]), ("source", [item("A", source=[1])]),
                 ("spec", [item("A", spec=[1])]), ("duplicate BOQ item_id(s): A", [item("A"), item("A")])]
        for fragment, items in cases:
            with self.subTest(fragment=fragment):
                with self.assertRaisesRegex(ValueError, re.escape(fragment)):
                    rfq(items)

    def test_datasheets_shape(self):
        good = datasheets()
        cases = [("dict", []), ("dict", {"datasheets": "x"}), ("must be an object", {"datasheets": ["x"]}), ("item_id", {"datasheets": [{}]}),
                 ("kind", {"datasheets": [dict(good["datasheets"][0], kind="other")]}),
                 ("requirement", {"datasheets": [dict(good["datasheets"][0], candidates="x")]}),
                 ("requirement", {"datasheets": [dict(good["datasheets"][0], requirement=[])]}),
                 ("candidate", {"datasheets": [dict(good["datasheets"][0], candidates=["x"])]}),
                 ("manufacturer", {"datasheets": [dict(good["datasheets"][0], candidates=[{"product_id": "p"}])]}),
                 ("product_id", {"datasheets": [dict(good["datasheets"][0], candidates=[{"manufacturer": "m"}])]})]
        for fragment, ds in cases:
            with self.subTest(fragment=fragment):
                with self.assertRaisesRegex(ValueError, fragment):
                    rfq(datasheets=ds)

    def test_category_filter_shape(self):
        for bad in ([], "cable", [""], [1]):
            with self.assertRaises(ValueError):
                rfq(requestable_categories=bad)


class LinesTests(unittest.TestCase):
    def test_lines_are_ordered_by_item_id_and_numbered(self):
        result = rfq()
        self.assertEqual([(ln["line_no"], ln["item_id"]) for ln in result["lines"]], [(1, "CAB-001"), (2, "DEV-001"), (3, "ENC-001"), (4, "TRM-001")])
        self.assertEqual(result["totals"], {"lines": 4, "incomplete_lines": 0})

    def test_the_boq_order_does_not_matter(self):
        items = boq()["items"]
        self.assertEqual(rfq(items), rfq(list(reversed(items))))

    def test_line_fields_are_copied_and_the_response_is_empty(self):
        ln = line(rfq(), "CAB-001")
        self.assertEqual((ln["category"], ln["description"], ln["unit"], ln["quantity"], ln["source"], ln["spec"]), ("cable", "desc CAB-001", "m", 12.5, ["A", "B"], CABLE_SPEC))
        self.assertEqual(ln["response"], {"unit_price": None, "delivery_days": None, "brand_offered": None, "remarks": None})
        self.assertFalse(ln["incomplete"])

    def test_no_price_or_commercial_value_appears_anywhere(self):
        result = rfq()
        for ln in result["lines"]:
            self.assertEqual(set(ln["response"].values()), {None})
        self.assertNotIn("unit_price", {k for ln in result["lines"] for k in ln if k != "response"})

    def test_a_line_without_quantity_is_carried_incomplete(self):
        result = rfq([item("CAB-001", quantity=None, spec=CABLE_SPEC), item("ENC-001", "enclosure", unit="un", quantity=1)])
        ln = line(result, "CAB-001")
        self.assertEqual((ln["quantity"], ln["incomplete"]), (None, True))
        self.assertEqual(result["totals"], {"lines": 2, "incomplete_lines": 1})
        self.assertIn("CAB-001: no quantity (line carried, incomplete)", result["issues"])

    def test_issue_text_is_carried(self):
        result = rfq([item("CAB-001", issues=["A: missing material"], spec=CABLE_SPEC)])
        ln = result["lines"][0]
        self.assertEqual((ln["incomplete"], ln["issues"]), (True, ["A: missing material"]))
        self.assertIn("CAB-001: A: missing material", result["issues"])

    def test_a_cable_with_unspecified_material_is_incomplete_even_without_issue_text(self):
        for key in ("material", "insulation"):
            result = rfq([item("CAB-001", spec=dict(CABLE_SPEC, **{key: None}))])
            self.assertTrue(result["lines"][0]["incomplete"], key)

    def test_a_device_with_missing_spec_values_is_complete_unless_issues(self):
        result = rfq([item("DEV-001", "protective_device", unit="un", quantity=1, spec=dict(DEVICE_SPEC, poles=None))])
        self.assertFalse(result["lines"][0]["incomplete"])

    def test_missing_optional_boq_keys_are_accepted(self):
        result = rfq([{"item_id": "X-1", "category": "other", "description": "d", "unit": "un", "quantity": 1}])
        self.assertEqual((result["lines"][0]["source"], result["lines"][0]["issues"], result["lines"][0]["spec"]), ([], [], {}))


class CategoryFilterTests(unittest.TestCase):
    def test_default_is_all_categories(self):
        self.assertEqual(rfq()["requestable_categories"], ["cable", "enclosure", "protective_device", "terminal_block"])

    def test_filter(self):
        result = rfq(requestable_categories=["protective_device", "cable", "cable"])
        self.assertEqual([ln["item_id"] for ln in result["lines"]], ["CAB-001", "DEV-001"])
        self.assertEqual(result["requestable_categories"], ["cable", "protective_device"])
        self.assertEqual(result["comparison_template"]["suppliers"], ["Alfa", "Beta"])
        self.assertEqual([r["item_id"] for r in result["comparison_template"]["rows"]], ["CAB-001", "DEV-001"])

    def test_unknown_category_is_reported_and_nothing_left_is_an_error(self):
        result = rfq(requestable_categories=["cable", "busbar"])
        self.assertIn("requestable category busbar is not in the bill of quantities", result["issues"])
        with self.assertRaisesRegex(ValueError, "no bill-of-quantities line is requestable"):
            rfq(requestable_categories=["busbar"])


class ReferencesTests(unittest.TestCase):
    def test_without_datasheets_there_are_no_references_and_no_issue(self):
        result = rfq()
        self.assertTrue(all(ln["references"] == [] for ln in result["lines"]))
        self.assertFalse([i for i in result["issues"] if "reference" in i])

    def test_references_are_verbatim_unique_and_sorted(self):
        ln = line(rfq(datasheets=datasheets()), "DEV-001")
        self.assertEqual([(r["manufacturer"], r["family"], r["product_id"]) for r in ln["references"]], [("abb", "Tmax", "a1"), ("abb", "Tmax", "a2"), ("zeta", "Zed", "z1")])
        first = ln["references"][0]
        self.assertEqual((first["source"], first["catalog_status"], first["datasheet_item_id"]), ("https://example.test/a1", "unverified", "DS-DEV-001"))

    def test_catalog_status_and_missing_values_are_kept_as_given(self):
        ref = line(rfq(datasheets=datasheets()), "CAB-001")["references"][0]
        self.assertEqual((ref["family"], ref["source"], ref["catalog_status"]), (None, None, "verified"))

    def test_other_categories_have_no_references_and_no_issue(self):
        result = rfq(datasheets=datasheets())
        self.assertEqual(line(result, "ENC-001")["references"], [])
        self.assertEqual(result["issues"], [])

    def test_a_requestable_line_without_a_matching_datasheet_is_reported(self):
        other = [item("DEV-001", "protective_device", unit="un", quantity=1, spec=dict(DEVICE_SPEC, in_a=63)), item("CAB-001", spec=CABLE_SPEC)]
        result = rfq(other, datasheets=datasheets())
        self.assertEqual(result["issues"], ["DEV-001: no acceptable reference in the datasheets"])

    def test_an_empty_datasheet_list_is_accepted(self):
        result = rfq(datasheets={"datasheets": []})
        self.assertIn("CAB-001: no acceptable reference in the datasheets", result["issues"])

    def test_inputs_are_not_modified(self):
        b, d = boq(), datasheets()
        before = copy.deepcopy((b, d))
        build_rfq("TG-1", b, datasheets=d, **terms())
        self.assertEqual((b, d), before)


class IdentifierAndStructureTests(unittest.TestCase):
    def test_rfq_id_is_deterministic_and_depends_on_board_and_suppliers_only(self):
        a = rfq()
        self.assertEqual(a["rfq_id"], rfq(currency="USD", validity_days=5)["rfq_id"])
        self.assertRegex(a["rfq_id"], r"^RFQ-[0-9A-F]{12}$")
        self.assertNotEqual(a["rfq_id"], rfq(suppliers=[supplier("Alfa")])["rfq_id"])
        self.assertNotEqual(a["rfq_id"], build_rfq("TG-2", boq(), **terms())["rfq_id"])

    def test_whole_result_is_deterministic(self):
        self.assertEqual(rfq(datasheets=datasheets()), rfq(datasheets=datasheets()))

    def test_keys_and_register(self):
        result = rfq()
        self.assertEqual(sorted(result), ["assumptions", "board", "comparison_template", "issued_for", "issues", "lines", "norm_records", "requestable_categories",
                                          "rfq_id", "terms", "totals"])
        self.assertEqual(result["norm_records"], [])
        self.assertTrue(result["assumptions"])

    def test_comparison_template_shape(self):
        template = rfq()["comparison_template"]
        self.assertEqual(template["suppliers"], ["Alfa", "Beta"])
        self.assertEqual(template["response_fields"], ["unit_price", "delivery_days", "brand_offered", "remarks"])
        self.assertEqual(template["columns"][:5], ["line_no", "item_id", "description", "unit", "quantity"])
        self.assertEqual(len(template["columns"]), 5 + 2 * 4)
        self.assertIn("Beta: delivery_days", template["columns"])
        self.assertEqual(len(template["rows"]), 4)
        self.assertEqual(template["rows"][0]["quotes"]["Alfa"], {"unit_price": None, "delivery_days": None, "brand_offered": None, "remarks": None})
        self.assertEqual(sorted(template["rows"][0]["quotes"]), ["Alfa", "Beta"])

    def test_package_exports(self):
        self.assertEqual(sorted(epc_rfq.__all__), ["RfqError", "build_rfq", "render_rows", "rfq_to_text"])
        self.assertEqual(epc_rfq.__version__, "0.1.0")

    def test_public_door(self):
        """COD-02: `epc_rfq.api` offers exactly what the package exports."""
        import importlib
        api = importlib.import_module("epc_rfq.api")
        self.assertEqual(sorted(api.__all__), sorted(epc_rfq.__all__))
        for name in api.__all__:
            self.assertIs(getattr(api, name), getattr(epc_rfq, name))


class RenderRowsTests(unittest.TestCase):
    def test_one_row_per_line_with_blank_supplier_columns(self):
        result = rfq(datasheets=datasheets())
        rows = render_rows(result)
        self.assertEqual([r["item_id"] for r in rows], [ln["item_id"] for ln in result["lines"]])
        row = rows[1]
        self.assertEqual((row["rfq_id"], row["board"], row["line_no"], row["quantity"], row["incomplete"], row["issue"]), (result["rfq_id"], "TG-1", 2, 2, False, ""))
        for column in result["comparison_template"]["columns"][5:]:
            self.assertEqual(row[column], "")
        self.assertEqual(row["references"], "abb Tmax (a1) [unverified; https://example.test/a1]; abb Tmax (a2) [unverified; https://example.test/a2]; "
                                            "zeta Zed (z1) [unverified; https://example.test/z1]")

    def test_reference_without_status_or_source_and_incomplete_row(self):
        ds = {"datasheets": [{"item_id": "DS-CAB-001", "kind": "cable", "requirement": dict(CABLE_SPEC), "candidates": [{"manufacturer": "m", "product_id": "p"}]}]}
        result = rfq([item("CAB-001", quantity=None, issues=["A: missing material"], spec=CABLE_SPEC)], datasheets=ds)
        row = render_rows(result)[0]
        self.assertEqual((row["references"], row["quantity"], row["incomplete"], row["issue"]), ("m (p)", None, True, "A: missing material"))


class TextTests(unittest.TestCase):
    def test_templates_contain_no_digit(self):
        for name in dir(text):
            value = getattr(text, name)
            if name.isupper() and isinstance(value, str):
                self.assertFalse(re.search(r"\d", value), name)

    def test_the_letter(self):
        result = rfq(datasheets=datasheets(), payment_terms="Contado", notes="Urgente")
        letter = rfq_to_text(result)
        self.assertTrue(letter.startswith(f"PEDIDO DE COTIZACIÓN {result['rfq_id']}\nTablero: TG-1\nDirigido a: Alfa, Beta\n"))
        for fragment in ("- Moneda de la oferta: ARS", "- Fecha límite de respuesta: 2026-12-15", "- Lugar de entrega: Obra Central", "- Validez de la oferta: 30 días",
                         "- Condiciones de pago: Contado", "- Observaciones: Urgente", "1. desc CAB-001 - cantidad: 12.5 m", "2. desc DEV-001 - cantidad: 2 un",
                         "   Referencia aceptable: abb Tmax (a1) [unverified; https://example.test/a1]"):
            self.assertIn(fragment, letter)
        self.assertTrue(letter.endswith("Borrador sujeto a revisión del ingeniero responsable.\n"))

    def test_optional_terms_are_omitted(self):
        letter = rfq_to_text(rfq())
        self.assertNotIn("Condiciones de pago", letter)
        self.assertNotIn("Observaciones", letter)

    def test_incomplete_lines(self):
        result = rfq([item("CAB-001", quantity=None, issues=["A: missing material"], spec=CABLE_SPEC), item("CAB-002", spec=dict(CABLE_SPEC, material=None))])
        letter = rfq_to_text(result)
        self.assertIn("1. desc CAB-001 - cantidad: sin definir\n   Ítem incompleto: A: missing material", letter)
        self.assertIn("2. desc CAB-002 - cantidad: 12.5 m\n   Ítem incompleto: falta información", letter)

    def test_numbers_come_from_the_values(self):
        letter = rfq_to_text(rfq(validity_days=45, response_deadline="2031-07-08"))
        self.assertIn("45 días", letter)
        self.assertIn("2031-07-08", letter)

    def test_build_helpers(self):
        self.assertIsNone(build._line_key(item("X", "enclosure")))


if __name__ == "__main__":
    unittest.main()
