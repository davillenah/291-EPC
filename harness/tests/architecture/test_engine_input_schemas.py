"""Input schemas of the engines (OPT-09): the schema of an engine's entry point and the engine's own check agree.

For each engine in CASES: a valid input passes the schema and the engine; each invalid input fails the schema AND the engine raises its own bilingual error (never a bare crash).
The schema is documentation and contract (`ENGINE_CONTRACTS.md` is written from it); the engine keeps validating in code, with codes in its `messages.py`.
Run: python -m unittest discover -s harness/tests/architecture
"""
import copy
import importlib
import json
import sys
import unittest
from pathlib import Path

import jsonschema

REPO = Path(__file__).resolve().parents[3]
ENGINES = REPO / "harness" / "src" / "engines"
for src in ENGINES.glob("*/*/src"):
    sys.path.insert(0, str(src))

CIRCUIT = {"tag": "C1", "phases": 3, "s_mm2": 4, "in_a": 20, "length_m": 30, "material": "cu", "insulation": "pvc", "device_kind": "mcb", "poles": 3, "breaking_capacity_ka": 6}
VALID = {
    "epc_boq": ("build_boq", {"board_name": "TS-1", "circuits": [CIRCUIT], "allowance_pct": 5}),
    "epc_terminal_blocks": ("build_terminal_list", {"board_name": "TS-1", "circuits": [{"tag": "C1", "phases": 3, "s_mm2": 4, "in_a": 20}]}),
    "epc_datasheets": ("requirements_from_circuits", {"circuits": [CIRCUIT]}),
}
INVALID = {   # name -> function(valid input) that breaks it
    "no_circuits": lambda d: d.update(circuits=[]),
    "phases_two": lambda d: d["circuits"][0].update(phases=2),
    "negative_section": lambda d: d["circuits"][0].update(s_mm2=-1),
    "unknown_key": lambda d: d["circuits"][0].update(bogus=1),
    "duplicate_tags": lambda d: d.update(circuits=[d["circuits"][0], dict(d["circuits"][0])]),
    "empty_tag": lambda d: d["circuits"][0].update(tag=" "),
    "no_allowance": lambda d: d.pop("allowance_pct"),
    "bad_allowance": lambda d: d.update(allowance_pct=-1),
    "bad_strip": lambda d: d.update(start_strip="1X"),
    "bad_voltage": lambda d: d.update(voltage_v=0),
}


def schema_of(package):
    path = next(ENGINES.glob(f"*/*/src/{package}/schema/input.schema.json"))
    return json.loads(path.read_text(encoding="utf-8"))


def call(package, doc):
    module = importlib.import_module(package)
    function, _ = VALID[package]
    return getattr(module, function)(**doc)


RAN = []


class InputSchemas(unittest.TestCase):
    def test_valid_input_passes_both(self):
        for package, (_, doc) in VALID.items():
            with self.subTest(engine=package):
                jsonschema.validate(doc, schema_of(package))
                call(package, copy.deepcopy(doc))

    def test_invalid_input_fails_both_with_the_engine_error(self):
        for package, (_, valid) in VALID.items():
            schema = schema_of(package)
            error_class = getattr(importlib.import_module(package), [n for n in importlib.import_module(package).__all__ if n.endswith("Error")][0])
            for name, breaker in INVALID.items():
                doc = copy.deepcopy(valid)
                try:
                    breaker(doc)
                except (KeyError, IndexError):
                    continue
                if doc == valid:
                    continue
                with self.subTest(engine=package, case=name):
                    needs = {"no_allowance": "allowance_pct", "bad_allowance": "allowance_pct", "bad_strip": "start_strip", "bad_voltage": "voltage_v"}.get(name)
                    if needs and needs not in schema["properties"]:
                        continue                                  # the case is about a field this engine does not have
                    RAN.append((package, name))
                    if name == "duplicate_tags":   # uniqueness is a rule of the engine, written in the schema as a description
                        with self.assertRaises(error_class):
                            call(package, doc)
                        continue
                    self.assertFalse(jsonschema.Draft202012Validator(schema).is_valid(doc), "the schema accepts it")
                    with self.assertRaises(error_class) as caught:
                        call(package, doc)
                    self.assertTrue(caught.exception.en and caught.exception.es)

    def test_the_cases_ran(self):
        self.test_invalid_input_fails_both_with_the_engine_error()
        self.assertGreaterEqual(len(RAN), 20)

    def test_schemas_are_valid_schemas(self):
        for package in VALID:
            jsonschema.Draft202012Validator.check_schema(schema_of(package))


if __name__ == "__main__":
    unittest.main()
