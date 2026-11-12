"""MIG-36b (decision D25): one source of truth for the disconnection times.

The times live in `aea_tables.json` and are read through `aea_earthing` (`tiempo_seccional_max_s`, `tiempo_desconexion_max_s`).
These tests fail if a module of the engine package grows its own literal time (a table, a time constant, a time parameter
default), compares a time against a literal instead of calling the accessor, reads the time keys of the JSON itself,
or if the numbers quoted by the rule texts drift from the table.
"""
import ast
import json
import os
import engine_sources
import re
import unittest

from epc_aea90364 import aea_earthing as EA
from epc_aea90364 import aea_tables as T
from epc_aea90364 import norm_data as NORM

SRC = os.path.dirname(os.path.abspath(T.__file__))
TIME_NAME = re.compile(r"tiempo|desconex|disconnect|seccional|sectional|^t_s$|^t_\w*_s$|^t_(max|min|desc)\w*$", re.I)

# Allowlist {(module, name): reason}: names that look like a time but are not a disconnection time. Empty today: the scan found nothing.
ALLOWED = {}

JSON_TIME_KEYS = ("771.18.III_tiempos_desconexion_s", "771.18_t_seccional_s", "771.18_t_seccional_selectividad_tn_s")


def _name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _name(node.func)
    if isinstance(node, ast.Subscript):
        return _name(node.value)
    return ""


def _is_num(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)


def _leaves(node):
    """Leaves of a literal container, or None when the node is not a plain literal structure."""
    if isinstance(node, ast.Constant):
        return [node]
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        parts = [_leaves(e) for e in node.elts]
    elif isinstance(node, ast.Dict):
        parts = [_leaves(v) for v in node.values]
    else:
        return None
    return None if any(p is None for p in parts) else [x for p in parts for x in p]


def _num_struct(node):
    leaves = _leaves(node)
    return bool(leaves) and any(_is_num(x) for x in leaves) and all(_is_num(x) or x.value is None for x in leaves)


def _assignments(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and _num_struct(n.value):
            for t in n.targets:
                if TIME_NAME.search(_name(t)):
                    yield n.lineno, f"literal assigned to {_name(t)}", _name(t)


def _compares(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare):
            ops = [n.left] + n.comparators
            hit = [_name(o) for o in ops if TIME_NAME.search(_name(o))]
            if hit and any(_is_num(o) for o in ops):
                yield n.lineno, f"time compared with a literal: {ast.unparse(n)}", hit[0]


def _defaults(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.arguments):
            pos = n.posonlyargs + n.args
            pairs = list(zip(pos[len(pos) - len(n.defaults):], n.defaults)) + [(a, d) for a, d in zip(n.kwonlyargs, n.kw_defaults) if d is not None]
            for a, d in pairs:
                if _is_num(d) and TIME_NAME.search(a.arg):
                    yield d.lineno, f"literal default for parameter {a.arg}", a.arg


def find_time_literals(source):
    """[(line, what, name)] of every own literal time in the Python source."""
    tree = ast.parse(source)
    return sorted([*_assignments(tree), *_compares(tree), *_defaults(tree)])


def _read(fname):
    with open(engine_sources.join(fname), encoding="utf-8") as f:
        return f.read()


def _py_modules():
    return engine_sources.listdir()


class ScannerSelfTest(unittest.TestCase):
    """The scan must catch the copies it exists to catch."""

    def test_detects_table_constants(self):
        self.assertTrue(find_time_literals('T_SECCIONAL = {"TN": 2.0, "TT": 1.0}\n'))
        self.assertTrue(find_time_literals("TIEMPOS_DESCONEXION = {'TN': ((120, 0.4, None),)}\n"))
        self.assertTrue(find_time_literals("t_seccional_s = 5\n"))

    def test_detects_a_comparison_and_a_default(self):
        self.assertTrue(find_time_literals("def f(t_s):\n    return t_s <= 5\n"))
        self.assertTrue(find_time_literals("def f(t_max_s=2.0):\n    return t_max_s\n"))

    def test_ignores_calls_to_the_accessor(self):
        self.assertEqual(find_time_literals("def f(e):\n    return EA.tiempo_seccional_max_s(e)\n"), [])
        self.assertEqual(find_time_literals("def f(e, t):\n    return t <= EA.tiempo_seccional_max_s(e)\n"), [])


class NoOwnTimesInTheEngine(unittest.TestCase):
    def test_no_module_holds_its_own_time(self):
        found = []
        for fname in _py_modules():
            for line, what, name in find_time_literals(_read(fname)):
                if (fname, name) not in ALLOWED:
                    found.append(f"{fname}:{line}: {what}")
        self.assertEqual(found, [], "own disconnection time outside aea_tables.json / aea_earthing")

    def test_allowlist_entries_are_still_needed(self):
        hits = {(f, name) for f in _py_modules() for _, _, name in find_time_literals(_read(f))}
        self.assertEqual(set(ALLOWED) - hits, set(), "stale allowlist entry")

    def test_only_aea_earthing_reads_the_time_keys_of_the_json(self):
        for fname in _py_modules():
            if fname == "aea_earthing.py":
                continue
            text = _read(fname)
            for key in JSON_TIME_KEYS:
                with self.subTest(module=fname, key=key):
                    self.assertNotIn(key, text)

    def test_accessor_is_the_table(self):
        raw = json.load(open(T.RUTA_JSON, encoding="utf-8"))["constantes"]
        self.assertEqual(EA.tiempo_seccional_max_s("TT"), raw["771.18_t_seccional_s"]["TT"])
        self.assertEqual(EA.tiempo_seccional_max_s("TN"), raw["771.18_t_seccional_s"]["TN"])
        self.assertEqual(EA.tiempo_seccional_max_s("TN", selectividad=True), raw["771.18_t_seccional_selectividad_tn_s"]["valor"])


class TextsAgreeWithTheTable(unittest.TestCase):
    """The rule file repeats three numbers (parameters and sentence); they must equal the table."""

    @staticmethod
    def _rule(rid):
        data = NORM.read_json(NORM.path("rules", "proteccion_choques.json"))

        def walk(x):
            if isinstance(x, dict):
                if x.get("id") == rid:
                    return x
                x = list(x.values())
            if isinstance(x, list):
                for v in x:
                    r = walk(v)
                    if r:
                        return r
            return None
        return walk(data)

    @staticmethod
    def _fmt(v):
        return str(int(v)) if v == int(v) else str(v).replace(".", ",")

    def test_tn_rule_matches_the_accessor(self):
        rule = self._rule("proteccion_choques.tn_s_tiempo_2s")
        p, f = rule["parametros"], self._fmt
        self.assertEqual(p["t_max_s"], EA.tiempo_seccional_max_s("TN"))
        self.assertEqual(p["t_max_selectividad_s"], EA.tiempo_seccional_max_s("TN", selectividad=True))
        self.assertIn(f"hasta {f(p['t_max_s'])} s", rule["regla"])
        self.assertIn(f"hasta {f(p['t_max_selectividad_s'])} s", rule["regla"])

    def test_tt_rule_matches_the_accessor(self):
        rule = self._rule("proteccion_choques.tt_tiempo_1s")
        self.assertEqual(rule["parametros"]["t_max_s"], EA.tiempo_seccional_max_s("TT"))
        self.assertIn(f"hasta {self._fmt(rule['parametros']['t_max_s'])} s", rule["regla"])


if __name__ == "__main__":
    unittest.main()
