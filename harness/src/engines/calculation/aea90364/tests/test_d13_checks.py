"""MIG-36d (decision D13): which checks decide and which only report.

Pinned here:
  - c_min has one source (aea_tables.json, read through short_circuit); no module of the engine keeps its own c_min literal.
  - Zs and the minimum Icc are reported (finding / verdict) and never change the section or the device.
  - I2 <= 1.45*Iz and the breaking capacity decide.
"""
import ast
import math
import os
import engine_sources
import re
import unittest
from unittest import mock

from epc_aea90364 import aea_earthing as EA
from epc_aea90364 import aea_pipeline as P
from epc_aea90364 import aea_tables as T
from epc_aea90364 import short_circuit as SC

SRC = os.path.dirname(os.path.abspath(T.__file__))
CMIN_NAME = re.compile(r"c_?min|c_tension_min", re.I)
ALLOWED = {}     # {(module, name): reason}; empty: the scan found no own c_min literal


def _is_num(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)


def _name(node):
    return node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else ""


def own_cmin_literals(source):
    """(line, name) of every c_min-looking name that gets a number: assignment, keyword/default, or comparison."""
    out = []
    tree = ast.parse(source)
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and _is_num(n.value):
            out += [(n.lineno, _name(t)) for t in n.targets if CMIN_NAME.search(_name(t))]
        elif isinstance(n, ast.arguments):
            pos = n.posonlyargs + n.args
            pairs = list(zip(pos[len(pos) - len(n.defaults):], n.defaults)) + list(zip(n.kwonlyargs, n.kw_defaults))
            out += [(d.lineno, a.arg) for a, d in pairs if d is not None and _is_num(d) and CMIN_NAME.search(a.arg)]
        elif isinstance(n, ast.keyword) and n.arg and CMIN_NAME.search(n.arg) and _is_num(n.value):
            out.append((n.value.lineno, n.arg))
    return out


class OneSourceForCmin(unittest.TestCase):
    def test_no_module_keeps_its_own_c_min(self):
        found = []
        for f in engine_sources.listdir():
            if f.endswith(".py") and f != "__init__.py":
                with open(engine_sources.join(f), encoding="utf-8") as fh:
                    found += [(f, line, name) for line, name in own_cmin_literals(fh.read()) if (f, name) not in ALLOWED]
        self.assertEqual(found, [], "c_min must be read from aea_tables.json (short_circuit.C_MIN_BT / aea_earthing.zs_maxima)")

    def test_scanner_detects_literals(self):
        self.assertEqual(own_cmin_literals("C_MIN_BT = 0.95"), [(1, "C_MIN_BT")])
        self.assertEqual(own_cmin_literals("def f(c_min=0.95): pass"), [(1, "c_min")])
        self.assertEqual(own_cmin_literals("g(c_min=0.9)"), [(1, "c_min")])
        self.assertEqual(own_cmin_literals("C_MIN_BT = SC.C_MIN_BT\ndef f(c_min=None): pass"), [])

    def test_zs_and_minimum_icc_share_the_table_value(self):
        c = T.constante("impedancias_estandar")["c_tension_min"]
        self.assertEqual(SC.C_MIN_BT, c)
        self.assertEqual(P.C_MIN_BT, c)
        self.assertEqual(EA.zs_maxima(230, 100), c * 230 / 100)
        ref = c * 380 / (2.0 * math.hypot(P.C_MAX_BT * 220.0 / 10e3 + 0.01, 0.02))      # D16: U0 of the 220/380 V system, not 380/sqrt(3)
        self.assertAlmostEqual(P.current_sc_min(380, 10, 0.01, 0.02, 3), ref)

    def test_pipeline_reads_c_min_live(self):
        with mock.patch.object(SC, "_g", lambda name: 0.9 if name == "C_MIN_BT" else SC.T.derived(name, SC._BUILD[name])):
            low = P.current_sc_min(380, 10, 0.01, 0.02, 3)
        self.assertAlmostEqual(low / P.current_sc_min(380, 10, 0.01, 0.02, 3), 0.9 / 0.95)


BOARD = {"TENSION_V": 380, "ICC_KA": 10, "FP_DEFAULT": 0.85}


def feeder(length, kind=None, load=40):
    c = {"TAG": "C-01", "DESCRIPCION": "X", "CARGA": load, "UNIDAD_CARGA": "A", "TOPOLOGY": "single", "FASE": "3F", "LONGITUD_m": length}
    if kind:
        c["KIND"] = kind
    return [c]


class ReportedNotDeciding(unittest.TestCase):
    def test_minimum_icc_reports_and_leaves_section_and_device(self):
        det_lo, det_hi = {}, {}
        with mock.patch.object(P, "current_sc_min", lambda *a, **k: 1.0):
            lo, avisos_lo = P.calculate(BOARD, feeder(40), detalle=det_lo)
        with mock.patch.object(P, "current_sc_min", lambda *a, **k: 1e9):
            hi, avisos_hi = P.calculate(BOARD, feeder(40), detalle=det_hi)
        self.assertTrue(any("Icc mín" in a for a in avisos_lo))                 # reported as a finding...
        self.assertFalse(any("Icc mín" in a for a in avisos_hi))
        self.assertEqual(lo, hi)                                                # ...and the section, In and device are the same
        self.assertEqual((det_lo["C-01"]["seccion_min_mm2"], det_lo["C-01"]["in_a"]), (det_hi["C-01"]["seccion_min_mm2"], det_hi["C-01"]["in_a"]))
        self.assertEqual(det_lo["C-01"]["icc_min_a"], 1.0)                      # reported in the detail


class DeciderChecks(unittest.TestCase):
    def test_i2_limit_rejects_a_section_by_device_type(self):
        f = P._iz_insufficient
        self.assertFalse(f({}, 32, 32, 1.0))                 # MCB: I2 = 1.45*In = 1.45*Iz: accepted
        self.assertTrue(f({}, 32, 31.9, 1.0))
        self.assertTrue(f({}, 32, 25, 0.5))                  # margen_iz does not let I2 exceed 1.45*Iz
        self.assertTrue(f({"KIND": "mccb"}, 100, 80, 0.5))   # MCCB k2 = 1.3: 130 A > 1.45*80
        self.assertFalse(f({"KIND": "mccb"}, 100, 90, 0.5))  # 130 A <= 130.5 A
        self.assertTrue(f({}, 80, 60, 0.5))                  # > 63 A without KIND is a MCCB

    def test_i2_decides_when_the_margin_is_relaxed(self):
        det = {}
        P.calculate(BOARD, feeder(10, load=30), margen_iz=0.5, detalle=det)
        d = det["C-01"]
        self.assertGreaterEqual(1.45 * d["iz_a"], 1.45 * d["in_a"])             # I2 <= 1.45*Iz holds in the result
        self.assertGreaterEqual(d["iz_a"], d["in_a"])

    def test_breaking_capacity_decides_the_device(self):
        icu = {}
        for icc in (6, 10, 30):
            datos, _ = P.calculate({"TENSION_V": 380, "ICC_KA": icc, "FP_DEFAULT": 0.85}, feeder(10, load=20))
            icu[icc] = datos["C-01"]["icu"]
        self.assertEqual(icu, {6: 6, 10: 10, 30: 36})        # the breaking capacity is the first of the series >= the board Icc


if __name__ == "__main__":
    unittest.main()
