"""MIG-30c: the stages wired to the engines. Zero difference against the engines' own calls (the board calculation chain of `epc_drawing.board_design`).

Parity with the web backend (`epc.modules.sld.repository.run_design`) retired with the web (paused): MIG-38b removed that comparison and the backend import;
the comparison against the engine's own direct call (`BD.design`) stays.

Needs the engine packages on PYTHONPATH (the gate's `harness-tests` environment has them). Small synthetic project built in code;
the circuit rows are the engine's own characterization rows (`aea90364/tests/characterization.py`).
"""
import contextlib
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from epc_aea90364 import aea_pipeline as P
import epc_design_basis
from epc_drawing import board_design as BD

from disciplines.electrical_lv import pipeline
from disciplines.electrical_lv.pipeline import STAGES, PipelineContext, run
from disciplines.electrical_lv.stages import engine_calls as EC
from disciplines.electrical_lv.stages.base import StageResult
from disciplines.electrical_lv.stages.table import WIRED_STAGES

ROOT = Path(__file__).resolve().parents[3]
CHARACTERIZATION = ROOT / "harness" / "src" / "engines" / "calculation" / "aea90364" / "tests" / "characterization.py"
CALC_STAGES = (4, 5, 7, 8, 9, 10, 11, 12)
CHAIN_STAGES = (4, 5, 7, 8, 9, 10, 11, 12, 14, 15)
NOT_WIRED = ()
NO_INPUT = (6,)            # stage 6 is wired (MIG-39a) but returns not_available without the `transformer` inputs
NO_STORE = (6, 16)         # stage 16 is wired (MIG-32) but returns not_available when the context has no ProjectStore


def characterization():
    spec = importlib.util.spec_from_file_location("aea_characterization", CHARACTERIZATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CH = characterization()
# (engine tag = load id, engine row, load kind, per-load overrides in board-form keys)
PROJECT = (
    ("L-01", "lighting", "lighting", {"fp": 0.9, "kind": "mcb"}),
    ("T-01", "sockets", "receptacles", {"fp": 0.9, "kind": "mcb"}),
    ("M-01", "motor_dol", "motor", {"topology": "dol", "fp": 0.85, "efficiency": 0.9}),
    ("E-01", "ups", "special", {"fp": 0.9, "notes": "UPS"}),
)
FEEDER = {"tag": "SUB", "description": "ALIMENTADOR TS", "load": 120, "unit": "A", "phase": "3F", "length_m": 60, "topology": "single", "kind": "mccb"}


def load_of(tag, row_name, kind):
    row = CH.KINDS[row_name]
    unit = row["UNIDAD_CARGA"]
    load = {"id": tag, "description": row["DESCRIPCION"], "area": "A1", "kind": kind, "power": {"value": row["CARGA"], "unit": unit},
            "phases": 1 if row["FASE"] == "1F" else 3}
    load["length"] = {"value": row["LONGITUD_m"], "unit": "m"}
    return load


def loads_doc():
    return {"schema_version": "1.0", "areas": [{"id": "A1", "name": "One"}], "loads": [load_of(t, r, k) for t, r, k, _ in PROJECT]}


def profile_doc():
    return {"project_code": "TEST-001", "normative_profile": {}, "criteria": {}, "language": "en",
            "supply": {"voltage": {"value": CH.BOARD["TENSION_V"], "unit": "V"}, "earthing_system": "TN",
                       "short_circuit_level": {"value": CH.BOARD["ICC_KA"], "unit": "kA", "origin": "declared by test"}}}


def inputs_doc():
    return {"board": {"fp_default": CH.BOARD["FP_DEFAULT"]}, "circuits": {t: dict(o) for t, _, _, o in PROJECT}, "extra_circuits": [dict(FEEDER)]}


def context(work_dir=None, **changes):
    ctx = PipelineContext(profile=profile_doc(), loads=loads_doc(), inputs_manifest={"files": [], "manifest_sha256": "0" * 64},
                          engine_inputs=inputs_doc(), work_dir=work_dir)
    for key, value in changes.items():
        setattr(ctx, key, value)
    return ctx


def direct_rows():
    """The same circuits as the engine's own Excel-key rows (what `P.calculate` reads), without going through the adapter."""
    rows = [CH.circuit(tag, CH.KINDS[name], **({"NOTAS": "UPS"} if tag == "E-01" else {}),
                       **({"KIND": o["kind"]} if "kind" in o else {}), **({"FP": o["fp"]} if "fp" in o else {}),
                       **({"TOPOLOGY": o["topology"]} if "topology" in o else {}), **({"RENDIMIENTO": o["efficiency"]} if "efficiency" in o else {}))
            for tag, name, _, o in PROJECT]
    rows.append(CH.circuit("SUB", {"DESCRIPCION": "ALIMENTADOR TS", "CARGA": 120, "UNIDAD_CARGA": "A", "TOPOLOGY": "single", "FASE": "3F", "LONGITUD_m": 60, "KIND": "mccb"}))
    return rows


def direct_form():
    """The board form of the backend (`board_design` keys), written by hand from the engine rows."""
    circuits = [{key: row[col] for col, key in BD.CIRCUIT_COLS if row.get(col) is not None} for row in direct_rows()]
    board = {"name": "TEST-001", "voltage_v": CH.BOARD["TENSION_V"], "system": "TN", "icc_ka": CH.BOARD["ICC_KA"], "fp_default": CH.BOARD["FP_DEFAULT"], "project": "TEST-001"}
    return {"board": board, "circuits": circuits, "validated": False}


def direct_call():
    detail = {}
    data, warnings = P.calculate(dict(CH.BOARD), direct_rows(), criterios=None, detalle=detail)
    return data, detail, warnings


def by_circuit(result):
    return {row["circuit"]: row for row in result.outputs["circuits"]}


def run_to_12():
    ctx = context()
    res = run(ctx, stop_after=12, run_id="r1", clock=lambda: "2026-01-01T00:00:00Z")
    return ctx, res


class ZeroDifferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx, cls.res = run_to_12()
        cls.datos, cls.detail, cls.warnings = direct_call()
        cls.stage = {r.stage: r for r in cls.res.results}

    def test_stages_1_to_12_ran(self):
        self.assertEqual([r.status for r in self.res.results], ["ok"] * 5 + ["not_available"] + ["ok"] * 6)
        self.assertEqual(self.stage[6].outputs, {})

    def test_the_raw_engine_result_equals_a_direct_call(self):
        calc = self.ctx.engine_cache["chain"]["calc"]
        self.assertEqual(calc["datos"], self.datos)
        self.assertEqual(calc["avisos"], self.warnings)
        self.assertEqual({t: {k: v for k, v in d.items() if k != "descripcion"} for t, d in calc["detalle"].items()}, self.detail)

    def test_every_calculation_stage_row_equals_the_direct_values(self):
        for number in (4, 7, 8, 9, 10):
            rows = by_circuit(self.stage[number])
            self.assertEqual(list(rows), list(self.datos))
        for tag, d in self.datos.items():
            det = self.detail[tag]
            self.assertEqual(by_circuit(self.stage[4])[tag]["ib_a"], det["ib_a"])
            self.assertEqual(by_circuit(self.stage[4])[tag]["p_kw"], det["p_kw"])
            sizing = by_circuit(self.stage[8])[tag]
            self.assertEqual((sizing["in_a"], sizing["ib_a"], sizing["s_mm2"], sizing["iz_a"]), (d["In"], d["Ib"], d["S"], det["iz_a"]))
            self.assertEqual(sizing["s_internal_mm2"], det["s_termica_mm2"])
            drop = by_circuit(self.stage[9])[tag]
            self.assertEqual((drop["du_pct"], drop["own_pct"], drop["accumulated_pct"], drop["limit_pct"]), (d["dU"], det["du_propia_pct"], det["du_acum_pct"], det["limite_pct"]))
            short = by_circuit(self.stage[10])[tag]
            self.assertEqual((short["icu_ka"], short["icc_min_a"]), (d["icu"], det["icc_min_a"]))
            structure = by_circuit(self.stage[7])[tag]
            self.assertEqual((structure["device"], structure["chain"], structure["parent"]), (d["disp"], det["cadena"], det["padre"]))

    def test_limits_and_demand_factors_come_from_the_engine(self):
        from epc_aea90364 import aea_demand
        limits = P.resolver_criterios(None)[0]
        self.assertEqual(self.stage[9].outputs["limits_pct"], {"seccional": limits["seccional"], "terminal": limits["iluminacion"], "motor": limits["motor"]})
        for row in by_circuit(self.stage[5]).values():
            self.assertEqual(row["demand_factor"], aea_demand.factor_demanda_sistema(row["system"]))

    def test_the_chain_ran_once(self):
        with mock.patch.object(P, "calculate", wraps=P.calculate) as spy:
            run(context(), stop_after=12, run_id="r2")
        self.assertEqual(spy.call_count, 1)

    def test_engine_calls_name_the_function_and_version(self):
        for number in CALC_STAGES:
            calls = self.stage[number].engine_calls
            self.assertTrue(calls, number)
            for call in calls:
                self.assertEqual(sorted(call), ["engine", "function", "version"])
                self.assertTrue(call["version"])
        self.assertIn("epc_aea90364.aea_pipeline.calculate", [c["function"] for c in self.stage[8].engine_calls])

    def test_pending_items_are_names_not_values(self):
        for number in (4, 5, 11, 12):
            for item in self.stage[number].outputs["pending"]:
                self.assertEqual(sorted(item), ["item", "reason"])

    def test_a_false_engine_verdict_becomes_a_finding(self):
        findings = self.stage[12].findings
        # the engine treats a circuit that is neither lighting nor a motor nor a feeder as a socket circuit: it asks for a differential
        self.assertEqual([f["field"] for f in findings], ["T-01/differential_ok", "E-01/differential_ok"])
        self.assertTrue(findings[0]["clause"].startswith("engine result"))
        self.assertEqual(findings[0]["verifier"], "calc-check")


class BackendParityTests(unittest.TestCase):
    """The pipeline equals the board calculation chain the engine runs itself (`epc_drawing.board_design.design`). Parity with the web backend retired with the web (paused)."""

    @classmethod
    def setUpClass(cls):
        cls.ctx, cls.res = run_to_12()
        cls.chain = cls.ctx.engine_cache["chain"]

    def assert_files_equal_chain(self, out):
        read = lambda name: json.loads((out / f"TEST-001_{name}.json").read_text(encoding="utf-8"))  # noqa: E731
        self.assertEqual(read("dimensionado"), self.chain["calc"]["datos"])
        self.assertEqual(read("dimensionado_detalle"), json.loads(json.dumps(self.chain["calc"]["detalle"])))
        self.assertEqual(read("memoria"), json.loads(json.dumps(self.chain["memo"])))

    def test_board_design_files_equal_the_pipeline_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = BD.design(direct_form(), Path(tmp), "TEST-001", None, None, diagrams=("none",))
            self.assertTrue(summary["ok"])
            self.assert_files_equal_chain(Path(tmp) / "out")

    def test_stage_rows_equal_the_backend_detail_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            BD.design(direct_form(), Path(tmp), "TEST-001", None, None, diagrams=("none",))
            detail = json.loads((Path(tmp) / "out" / "TEST-001_dimensionado_detalle.json").read_text(encoding="utf-8"))
        stage = {r.stage: r for r in self.res.results}
        for tag, det in detail.items():
            self.assertEqual(by_circuit(stage[8])[tag]["pe_mm2"], det["pe_mm2"])
            self.assertEqual(by_circuit(stage[8])[tag]["route"], det["ruta"])
            self.assertEqual(by_circuit(stage[4])[tag]["fp"], det["fp"])
            self.assertEqual(by_circuit(stage[9])[tag]["accumulated_pct"], det["du_acum_pct"])


class MissingDataTests(unittest.TestCase):
    def ready(self, **changes):
        ctx = context(**changes)
        ctx.design_basis = {"supply": {}}
        ctx.results = {3: StageResult(3, "ok")}
        return ctx

    def assert_blocked_without_values(self, ctx, expected_text, stages=CHAIN_STAGES):
        for number in stages:
            res = STAGES[number - 1].run(ctx)
            with self.subTest(stage=number):
                self.assertEqual(res.status, "blocked")
                self.assertEqual((res.outputs, res.engine_calls), ({}, []))
                self.assertIn(expected_text, res.message)
                self.assertTrue(res.findings)

    def test_missing_length_blocks_every_chain_stage(self):
        ctx = self.ready()
        del ctx.loads["loads"][0]["length"]
        self.assert_blocked_without_values(ctx, "L-01: run length")
        self.assertEqual(ctx.engine_cache, {})

    def test_missing_voltage_blocks(self):
        ctx = self.ready()
        del ctx.profile["supply"]["voltage"]
        self.assert_blocked_without_values(ctx, "supply.voltage")

    def test_missing_power_factor_blocks(self):
        ctx = self.ready()
        ctx.engine_inputs["board"] = {}
        del ctx.engine_inputs["circuits"]["L-01"]["fp"]       # a load in kW without its own fp and no board default
        self.assert_blocked_without_values(ctx, "board.fp_default")

    def test_a_motor_without_starter_topology_blocks(self):
        ctx = self.ready()
        del ctx.engine_inputs["circuits"]["M-01"]["topology"]
        self.assert_blocked_without_values(ctx, "M-01: starter topology")

    def test_unknown_override_blocks(self):
        ctx = self.ready()
        ctx.engine_inputs["circuits"]["M-01"]["colour"] = "red"
        self.assert_blocked_without_values(ctx, "colour")

    def test_a_refusal_of_the_engine_blocks(self):
        ctx = self.ready()
        ctx.engine_inputs["extra_circuits"][0]["tag"] = "L-01"      # duplicate tag: the engine raises ValueError
        self.assert_blocked_without_values(ctx, "TAG duplicados", stages=(4, 8, 12))

    def test_missing_loads_block_through_the_preconditions(self):
        res = STAGES[3].run(PipelineContext())
        self.assertEqual((res.status, res.reason, res.outputs), ("blocked", "precondition", {}))

    def test_d24_data_missing_blocks_at_stage_1_before_any_engine_call(self):
        ctx = PipelineContext(answers={"project_code": "TEST-001", "client": {"name": "C"}, "site": {"address": "A", "installation_type": "t"},
                                       "supply": {}, "language": "en"})
        res = run(ctx, run_id="r")
        self.assertEqual([r.status for r in res.results], ["blocked"])
        self.assertEqual([c for r in res.results for c in r.engine_calls], [])
        self.assertEqual(ctx.engine_cache, {})


class NotWiredTests(unittest.TestCase):
    def test_the_table_and_the_stage_flags_agree(self):
        self.assertEqual(WIRED_STAGES, tuple(s.number for s in STAGES if s.wired))
        self.assertEqual(sorted(set(WIRED_STAGES) | set(NOT_WIRED)), list(range(1, 17)))

    def test_stages_without_inputs_still_return_not_available_with_nothing(self):
        ctx = context()
        run(ctx, stop_after=3, run_id="r")
        for number in NO_INPUT:
            res = STAGES[number - 1].run(ctx)
            with self.subTest(stage=number):
                self.assertEqual(res.status, "not_available")
                self.assertEqual((res.outputs, res.engine_calls, res.findings), ({}, [], []))


def without_dxf_stamp(result):
    """The run as a dict without the size and hash of the DXF files: the drawing engine writes the current time into them."""
    out = json.loads(json.dumps(result))
    for res in out["results"]:
        for f in res["outputs"].get("files", []):
            if f["path"].endswith(".dxf"):
                f["bytes"] = f["sha256"] = None
    return out


class DeterminismTests(unittest.TestCase):
    def test_two_runs_with_the_same_run_id_and_clock_give_the_same_result(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = run(context(a), run_id="fixed", clock=lambda: "2026-01-01T00:00:00Z").to_dict()
            second = run(context(b), run_id="fixed", clock=lambda: "2026-01-01T00:00:00Z").to_dict()
        self.assertEqual(without_dxf_stamp(first), without_dxf_stamp(second))
        self.assertEqual(json.loads(json.dumps(first)), first)
        self.assertEqual(first["summary"]["not_available"], list(NO_STORE))

    def test_only_the_dxf_files_differ_between_runs_because_the_engine_stamps_the_time(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = {f["path"]: f for f in run(context(a), stop_after=14, run_id="x").results[13].outputs["files"]}
            second = {f["path"]: f for f in run(context(b), stop_after=14, run_id="x").results[13].outputs["files"]}
        self.assertEqual(sorted(first), sorted(second))
        self.assertEqual([p for p in first if first[p] != second[p]], [p for p in first if p.endswith(".dxf") and first[p] != second[p]])

    def test_a_second_run_in_the_same_context_recomputes_the_chain(self):
        ctx = context()
        first = run(ctx, stop_after=12, run_id="x").to_dict()
        ctx.engine_inputs["circuits"]["L-01"]["fp"] = 0.8
        second = run(ctx, stop_after=12, run_id="x").to_dict()
        self.assertNotEqual(first["results"][3], second["results"][3])


class OutputStagesTests(unittest.TestCase):
    def test_drawings_are_written_only_under_the_work_dir(self):
        with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as cwd, contextlib.ExitStack() as stack:
            work = Path(base) / "work"
            work.mkdir()
            old = os.getcwd()
            os.chdir(cwd)
            stack.callback(os.chdir, old)
            res = run(context(str(work)), stop_after=14, run_id="r")
            drawing = res.results[13]
            self.assertEqual(drawing.status, "ok", drawing.message)
            self.assertEqual(os.listdir(base), ["work"])
            self.assertEqual(os.listdir(cwd), [])
            out = work / "drawings" / "TEST-001" / "out"
            files = {f["path"]: f for f in drawing.outputs["files"]}
            self.assertEqual(sorted(files), sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()))
            self.assertTrue(any(name.startswith("SLD_TEST-001") for name in files))
            self.assertEqual(drawing.engine_calls[0]["function"], "epc_drawing.board_design.design")
            self.assertTrue(drawing.outputs["summary"]["ok"])

    def test_drawings_without_a_work_dir_are_blocked(self):
        ctx = context()
        run(ctx, stop_after=12, run_id="r")
        res = STAGES[13].run(ctx)
        self.assertEqual((res.status, res.outputs, res.engine_calls), ("blocked", {}, []))
        self.assertIn("work_dir", res.message)

    def test_a_board_name_that_is_not_a_file_name_is_blocked(self):
        ctx = context("unused")
        ctx.engine_inputs["board"]["name"] = "../x"
        ctx.results = {3: StageResult(3, "ok")}
        res = STAGES[13].run(ctx)
        self.assertEqual(res.status, "blocked")
        self.assertIn("board name", res.message)

    def test_documents_are_the_engine_memo_and_the_rest_is_pending(self):
        ctx = context()
        res = run(ctx, stop_after=15, run_id="r", stages=[s for s in STAGES if s.number != 14])
        docs = res.results[-1]
        self.assertEqual(docs.status, "ok")
        memo = ctx.engine_cache["chain"]["memo"]
        self.assertEqual(docs.outputs["memo_summary"], memo["resumen"])
        self.assertEqual([d["name"] for d in docs.outputs["documents"]], ["calculation_memo", "project_summary", "terminal_block_list", "design_basis", "descriptive_report"])
        self.assertTrue(all(d["document"]["blocks"] for d in docs.outputs["documents"][:2]))
        terminals = docs.outputs["documents"][2]["document"]
        self.assertEqual(terminals["board"], ctx.engine_cache["chain"]["form"]["board"]["name"])
        self.assertEqual([r["circuit"] for r in terminals["strips"][0]["rows"]], list(ctx.engine_cache["chain"]["calc"]["datos"]))
        self.assertEqual(docs.outputs["documents"][2]["sha256"], hashlib.sha256(json.dumps(terminals, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest())
        self.assertIn("epc_terminal_blocks.build_terminal_list", [c["function"] for c in docs.engine_calls])
        self.assertTrue(all(p["status"] == "planned" for p in docs.outputs["pending_documents"]))
        self.assertTrue(all(set(p) == ({"name", "status", "reason"} if p["name"] in ("BOQ", "datasheets", "RFQ") else {"name", "status"}) for p in docs.outputs["pending_documents"]))
        self.assertIn(("BOQ", "no_allowance_pct"), [(p["name"], p.get("reason")) for p in docs.outputs["pending_documents"]])
        self.assertNotIn("epc_boq.build_boq", [c["function"] for c in docs.engine_calls])
        self.assertIn(("datasheets", "no_catalog_dir"), [(p["name"], p.get("reason")) for p in docs.outputs["pending_documents"]])
        self.assertNotIn("epc_datasheets.build_datasheets", [c["function"] for c in docs.engine_calls])
        self.assertIn(("RFQ", "no_boq"), [(p["name"], p.get("reason")) for p in docs.outputs["pending_documents"]])
        self.assertNotIn("epc_rfq.build_rfq", [c["function"] for c in docs.engine_calls])
        self.assertNotIn("terminal-block list", [p["name"] for p in docs.outputs["pending_documents"]])


def synthetic_catalog(root):
    """A small synthetic catalog folder (never the repository catalog): one breaker maker and one cable maker."""
    makers = {"mk1": ("breakers", {"id": "mk1-a", "family": "Fam A", "type": "mccb", "status": "unverified", "source": "https://example.test/a", "rated_current_a": {"max": 6300},
                                   "breaking_capacity": [{"voltage_v": 1000, "icu_ka": 1000}]}),
              "mk2": ("cables", {"id": "mk2-c", "family": "Fam C XLPE PVC", "type": "cable_power", "status": "unverified", "source": "https://example.test/c"})}
    for name, (category, item) in makers.items():
        folder = Path(root) / name
        folder.mkdir(parents=True)
        (folder / "manufacturer.json").write_text(json.dumps({"id": name, "name": name.upper(), "categories": [category]}), encoding="utf-8")
        (folder / f"{category}.json").write_text(json.dumps({"manufacturer": name, "category": category, "products": [item]}), encoding="utf-8")


class DatasheetsStageTests(unittest.TestCase):
    """MIG-39d: stage 15 builds the datasheets only when `engine_inputs["datasheets"]["catalog_dir"]` is given (explicit; the stage never searches the repository)."""

    def documents(self, given):
        ctx = context()
        if given is not None:
            ctx.engine_inputs["datasheets"] = given
        res = run(ctx, stop_after=15, run_id="r", stages=[s for s in STAGES if s.number != 14])
        return ctx, res.results[-1]

    def test_produced_from_a_synthetic_catalog(self):
        with tempfile.TemporaryDirectory() as root:
            synthetic_catalog(root)
            ctx, docs = self.documents({"catalog_dir": root})
        self.assertEqual(docs.status, "ok", docs.message)
        self.assertEqual([d["name"] for d in docs.outputs["documents"]], ["calculation_memo", "project_summary", "terminal_block_list", "datasheets", "design_basis", "descriptive_report"])
        entry = docs.outputs["documents"][3]
        sheets = entry["document"]
        self.assertEqual(entry["sha256"], hashlib.sha256(json.dumps(sheets, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest())
        self.assertEqual(sheets["board"], ctx.engine_cache["chain"]["form"]["board"]["name"])
        self.assertTrue(sheets["datasheets"])
        self.assertTrue(all(s["review_status"] == "pending review" for s in sheets["datasheets"]))
        self.assertTrue(all(c["catalog_status"] == "unverified" for s in sheets["datasheets"] for c in s["candidates"]))
        self.assertEqual([c["engine"] for c in docs.engine_calls if c["function"] == "epc_datasheets.build_datasheets"], ["procurement/datasheets"])
        self.assertNotIn("datasheets", [p["name"] for p in docs.outputs["pending_documents"]])
        self.assertIn("RFQ", [p["name"] for p in docs.outputs["pending_documents"]])
        self.assertIn(("BOQ", "no_allowance_pct"), [(p["name"], p.get("reason")) for p in docs.outputs["pending_documents"]])

    def test_voltage_is_passed_when_given(self):
        with tempfile.TemporaryDirectory() as root:
            synthetic_catalog(root)
            _, docs = self.documents({"catalog_dir": root, "voltage_v": 400})
        reqs = [s["requirement"] for s in docs.outputs["documents"][3]["document"]["datasheets"] if s["kind"] == "protective_device"]
        self.assertTrue(reqs and all(r["voltage_v"] == 400 for r in reqs))

    def test_pending_without_a_catalog_dir(self):
        for given in (None, {}, {"other": 1}, {"catalog_dir": ""}, "x"):
            _, docs = self.documents(given)
            self.assertEqual([d["name"] for d in docs.outputs["documents"]], ["calculation_memo", "project_summary", "terminal_block_list", "design_basis", "descriptive_report"])
            self.assertIn({"name": "datasheets", "status": "planned", "reason": "no_catalog_dir"}, docs.outputs["pending_documents"])

    def test_an_unreadable_or_invalid_catalog_blocks_the_stage(self):
        with tempfile.TemporaryDirectory() as root:
            _, docs = self.documents({"catalog_dir": str(Path(root) / "missing")})
            self.assertEqual(docs.status, "blocked")
            self.assertIn("catalog folder not found", docs.message)
            (Path(root) / "mk").mkdir()
            (Path(root) / "mk" / "manufacturer.json").write_text("{not json", encoding="utf-8")
            _, docs = self.documents({"catalog_dir": root})
            self.assertEqual(docs.status, "blocked")
            self.assertIn("datasheets:", docs.message)

    def test_an_invalid_voltage_blocks_the_stage(self):
        with tempfile.TemporaryDirectory() as root:
            synthetic_catalog(root)
            _, docs = self.documents({"catalog_dir": root, "voltage_v": -1})
        self.assertEqual((docs.status, "voltage_v" in docs.message), ("blocked", True))

    def test_the_real_catalog_folder_is_read_only_through_the_engine(self):
        _, docs = self.documents({"catalog_dir": str(ROOT / "harness" / "catalogs" / "manufacturers")})
        self.assertEqual(docs.status, "ok", docs.message)
        sheets = docs.outputs["documents"][3]["document"]["datasheets"]
        self.assertTrue(all(c["catalog_status"] == "unverified" for s in sheets for c in s["candidates"]))


class BillOfQuantitiesStageTests(unittest.TestCase):
    """MIG-39c: stage 15 builds the bill of quantities only when the engineer gives `engine_inputs["boq"]["allowance_pct"]`."""

    def documents(self, boq):
        ctx = context()
        if boq is not None:
            ctx.engine_inputs["boq"] = boq
        res = run(ctx, stop_after=15, run_id="r", stages=[s for s in STAGES if s.number != 14])
        return ctx, res.results[-1]

    def test_produced_with_an_explicit_allowance(self):
        ctx, docs = self.documents({"allowance_pct": 10})
        self.assertEqual(docs.status, "ok", docs.message)
        self.assertEqual([d["name"] for d in docs.outputs["documents"]], ["calculation_memo", "project_summary", "terminal_block_list", "boq", "design_basis", "descriptive_report"])
        entry = docs.outputs["documents"][3]
        boq = entry["document"]
        self.assertEqual(entry["sha256"], hashlib.sha256(json.dumps(boq, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest())
        self.assertEqual((boq["board"], boq["allowance_pct"]), (ctx.engine_cache["chain"]["form"]["board"]["name"], 10))
        datos = ctx.engine_cache["chain"]["calc"]["datos"]
        self.assertEqual(sum(i["quantity"] for i in boq["items"] if i["category"] == "protective_device"), len(datos))
        terminals = docs.outputs["documents"][2]["document"]["totals"]["by_terminal_size"]
        self.assertEqual({i["spec"]["size_mm2"]: i["quantity"] for i in boq["items"] if i["category"] == "terminal_block"},
                         {float(k): v for k, v in terminals.items() if k != "none"})
        lengths = sum(ctx.engine_cache["chain"]["calc"]["detalle"][t]["largo_m"] for t in datos)
        self.assertAlmostEqual(boq["totals"]["cable_m"], lengths * 1.1, places=3)
        none_count = terminals.get("none", 0)
        self.assertEqual(boq["issues"], [f"{none_count} terminal(s) have no assigned terminal size (not counted)"] if none_count else [])
        self.assertEqual([c["engine"] for c in docs.engine_calls if c["function"] == "epc_boq.build_boq"], ["procurement/boq"])
        self.assertNotIn("BOQ", [p["name"] for p in docs.outputs["pending_documents"]])
        self.assertIn("RFQ", [p["name"] for p in docs.outputs["pending_documents"]])

    def test_zero_allowance_is_accepted(self):
        _, docs = self.documents({"allowance_pct": 0})
        self.assertEqual(docs.outputs["documents"][3]["document"]["allowance_pct"], 0)

    def test_not_produced_without_an_allowance(self):
        for boq in ({}, {"other": 1}, "x"):
            _, docs = self.documents(boq)
            self.assertEqual([d["name"] for d in docs.outputs["documents"]], ["calculation_memo", "project_summary", "terminal_block_list", "design_basis", "descriptive_report"])
            self.assertIn({"name": "BOQ", "status": "planned", "reason": "no_allowance_pct"}, docs.outputs["pending_documents"])

    def test_an_invalid_allowance_blocks_the_stage(self):
        _, docs = self.documents({"allowance_pct": -5})
        self.assertEqual(docs.status, "blocked")
        self.assertIn("bill of quantities", docs.message)
        self.assertIn("allowance_pct", docs.message)


RFQ_TERMS = {"suppliers": [{"name": "Alfa", "contact": "alfa@example.test"}, {"name": "Beta"}], "currency": "ARS", "response_deadline": "2026-12-15",
             "delivery_site": "Obra Central", "validity_days": 30}


class RfqStageTests(unittest.TestCase):
    """MIG-39e: stage 15 builds the RFQ only when the BOQ was produced in the same run AND the commercial terms are given."""

    def documents(self, rfq=None, boq=None, catalog=None):
        ctx = context()
        for key, given in (("rfq", rfq), ("boq", boq), ("datasheets", catalog)):
            if given is not None:
                ctx.engine_inputs[key] = given
        res = run(ctx, stop_after=15, run_id="r", stages=[s for s in STAGES if s.number != 14])
        return ctx, res.results[-1]

    def reasons(self, docs):
        return {p["name"]: p.get("reason") for p in docs.outputs["pending_documents"]}

    def test_produced_with_the_boq_and_the_terms(self):
        ctx, docs = self.documents(RFQ_TERMS, {"allowance_pct": 10})
        self.assertEqual(docs.status, "ok", docs.message)
        self.assertEqual([d["name"] for d in docs.outputs["documents"]], ["calculation_memo", "project_summary", "terminal_block_list", "boq", "rfq", "design_basis", "descriptive_report"])
        entry = docs.outputs["documents"][4]
        rfq = entry["document"]
        self.assertEqual(entry["sha256"], hashlib.sha256(json.dumps(rfq, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest())
        self.assertEqual(rfq["board"], ctx.engine_cache["chain"]["form"]["board"]["name"])
        self.assertEqual(rfq["terms"]["currency"], "ARS")
        self.assertEqual([ln["item_id"] for ln in rfq["lines"]], sorted(i["item_id"] for i in docs.outputs["documents"][3]["document"]["items"]))
        self.assertTrue(all(set(ln["response"].values()) == {None} for ln in rfq["lines"]))
        self.assertEqual([c["engine"] for c in docs.engine_calls if c["function"] == "epc_rfq.build_rfq"], ["procurement/rfq"])
        self.assertNotIn("RFQ", [p["name"] for p in docs.outputs["pending_documents"]])

    def test_the_datasheets_are_passed_when_produced(self):
        with tempfile.TemporaryDirectory() as root:
            synthetic_catalog(root)
            _, docs = self.documents(RFQ_TERMS, {"allowance_pct": 10}, {"catalog_dir": root})
        self.assertEqual([d["name"] for d in docs.outputs["documents"]][-5:-2], ["boq", "datasheets", "rfq"])
        rfq = docs.outputs["documents"][5]["document"]
        self.assertTrue(any(ln["references"] for ln in rfq["lines"]))
        self.assertTrue(all(r["catalog_status"] == "unverified" for ln in rfq["lines"] for r in ln["references"]))

    def test_pending_without_a_boq(self):
        for terms in (None, RFQ_TERMS):
            _, docs = self.documents(terms)
            self.assertEqual([d["name"] for d in docs.outputs["documents"]], ["calculation_memo", "project_summary", "terminal_block_list", "design_basis", "descriptive_report"])
            self.assertIn({"name": "RFQ", "status": "planned", "reason": "no_boq"}, docs.outputs["pending_documents"])

    def test_pending_without_the_terms(self):
        for terms in (None, {}, "x", []):
            _, docs = self.documents(terms, {"allowance_pct": 10})
            self.assertEqual([d["name"] for d in docs.outputs["documents"]][-3], "boq")
            self.assertEqual(self.reasons(docs)["RFQ"], "no_rfq_terms")
            self.assertNotIn("epc_rfq.build_rfq", [c["function"] for c in docs.engine_calls])

    def test_invalid_terms_block_the_stage(self):
        cases = [(dict(RFQ_TERMS, response_deadline="15/12/2026"), "response_deadline"), (dict(RFQ_TERMS, validity_days=0), "validity_days"),
                 ({"currency": "ARS"}, "missing required commercial field(s): suppliers, response_deadline, delivery_site, validity_days"),
                 (dict(RFQ_TERMS, price=5), "unknown input(s) price"), (dict(RFQ_TERMS, requestable_categories=["busbar"]), "no bill-of-quantities line")]
        for terms, fragment in cases:
            _, docs = self.documents(terms, {"allowance_pct": 10})
            self.assertEqual(docs.status, "blocked", fragment)
            self.assertIn("rfq: ", docs.message)
            self.assertIn(fragment, docs.message)

    def test_a_category_filter_is_passed(self):
        _, docs = self.documents(dict(RFQ_TERMS, requestable_categories=["cable"]), {"allowance_pct": 10})
        self.assertEqual({ln["category"] for ln in docs.outputs["documents"][4]["document"]["lines"]}, {"cable"})


class DesignBasisStageTests(unittest.TestCase):
    """MIG-39f: stage 15 adds the draft design-basis document whenever the context has the profile and the design basis of stage 2; no extra input is needed."""

    def documents(self, **changes):
        ctx = context()
        for key, value in changes.items():
            setattr(ctx, key, value)
        res = run(ctx, stop_after=15, run_id="r", stages=[s for s in STAGES if s.number != 14])
        return ctx, res.results[-1]

    def test_produced_without_any_extra_input(self):
        ctx, docs = self.documents()
        self.assertEqual(docs.status, "ok", docs.message)
        entry = docs.outputs["documents"][-2]
        self.assertEqual(entry["name"], "design_basis")
        doc = entry["document"]
        self.assertEqual(entry["sha256"], hashlib.sha256(json.dumps(doc, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest())
        self.assertEqual(doc["status"], "draft")
        self.assertEqual(doc, epc_design_basis.build_design_basis_document(ctx.profile, criteria=ctx.criteria, assumptions=ctx.assumptions, requirements=ctx.requirements))
        self.assertEqual([c["engine"] for c in docs.engine_calls if c["function"] == "epc_design_basis.build_design_basis_document"], ["quality/design_basis"])
        self.assertNotIn("design basis", [p["name"] for p in docs.outputs["pending_documents"]])

    def test_pending_with_a_reason_when_stage_2_gave_nothing(self):
        ctx = context()
        run(ctx, stop_after=15, run_id="r", stages=[s for s in STAGES if s.number != 14])
        ctx.design_basis = None
        docs = STAGES[14].run(ctx)
        self.assertEqual(docs.status, "ok", docs.message)
        self.assertNotIn("design_basis", [d["name"] for d in docs.outputs["documents"]])
        self.assertIn({"name": "design basis", "status": "planned", "reason": "no_design_basis"}, docs.outputs["pending_documents"])
        self.assertNotIn("epc_design_basis.build_design_basis_document", [c["function"] for c in docs.engine_calls])

    def test_an_invalid_profile_blocks_with_the_engine_message(self):
        ctx = context()
        run(ctx, stop_after=15, run_id="r", stages=[s for s in STAGES if s.number != 14])
        ctx.profile = dict(ctx.profile, supply=dict(ctx.profile["supply"], earthing_system=None))
        docs = STAGES[14].run(ctx)
        self.assertEqual(docs.status, "blocked")
        self.assertIn("design basis: D24 data missing in the profile: supply.earthing_system", docs.message)


class DescriptiveReportStageTests(unittest.TestCase):
    """MIG-39g: stage 15 adds the draft descriptive report right after the design basis, whenever the design basis is produced; no extra input is needed."""

    def documents(self, **changes):
        ctx = context()
        for key, value in changes.items():
            setattr(ctx, key, value)
        res = run(ctx, stop_after=15, run_id="r", stages=[s for s in STAGES if s.number != 14])
        return ctx, res.results[-1]

    def test_produced_last_after_the_design_basis(self):
        ctx, docs = self.documents()
        self.assertEqual(docs.status, "ok", docs.message)
        names = [d["name"] for d in docs.outputs["documents"]]
        self.assertEqual(names[-2:], ["design_basis", "descriptive_report"])
        entry = docs.outputs["documents"][-1]
        doc = entry["document"]
        self.assertEqual(entry["sha256"], hashlib.sha256(json.dumps(doc, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest())
        self.assertEqual(doc["status"], "draft")
        self.assertEqual(doc["norm_records"], [])
        self.assertEqual(sorted(s["id"] for s in doc["sections"]), sorted(["object_scope", "supply_earthing", "board_organisation", "cables_installation",
                                                                            "protection_earthing", "standards", "status_limitations"]))
        calls = [c["engine"] for c in docs.engine_calls if c["function"] == "epc_descriptive_report.build_descriptive_report"]
        self.assertEqual(calls, ["quality/descriptive_report"])
        self.assertNotIn("descriptive report", [p["name"] for p in docs.outputs["pending_documents"]])

    def test_counts_come_from_the_run(self):
        ctx, docs = self.documents()
        doc = docs.outputs["documents"][-1]["document"]
        items = {i["key"]: i for s in doc["sections"] for i in s["items"]}
        circuits = ctx.engine_cache["chain"]["calc"]["datos"]
        self.assertEqual(items["circuits_total"]["value"], len(circuits))
        terminals = docs.outputs["documents"][2]["document"]
        self.assertEqual(items["terminals_total"]["value"], terminals["totals"]["terminals"])
        self.assertIn("not provided: boq", doc["issues"])
        pending = [p["name"] for p in docs.outputs["pending_documents"]]
        self.assertEqual(items["pending_documents_total"]["value"], len(pending))
        self.assertIsInstance(items["unreviewed_norm_records"]["value"], int)
        self.assertGreater(items["unreviewed_norm_records"]["value"], 0)

    def test_boq_totals_are_passed_when_produced(self):
        ctx = context()
        ctx.engine_inputs["boq"] = {"allowance_pct": 10}
        res = run(ctx, stop_after=15, run_id="r", stages=[s for s in STAGES if s.number != 14])
        docs = res.results[-1]
        boq = next(d for d in docs.outputs["documents"] if d["name"] == "boq")["document"]
        items = {i["key"]: i for s in docs.outputs["documents"][-1]["document"]["sections"] for i in s["items"]}
        self.assertEqual((items["boq_lines"]["value"], items["boq_devices"]["value"]), (boq["totals"]["lines"], boq["totals"]["devices"]))
        self.assertNotIn("not provided: boq", docs.outputs["documents"][-1]["document"]["issues"])

    def test_pending_with_a_reason_without_the_design_basis(self):
        ctx = context()
        run(ctx, stop_after=15, run_id="r", stages=[s for s in STAGES if s.number != 14])
        ctx.design_basis = None
        docs = STAGES[14].run(ctx)
        self.assertEqual(docs.status, "ok", docs.message)
        self.assertNotIn("descriptive_report", [d["name"] for d in docs.outputs["documents"]])
        self.assertIn({"name": "descriptive report", "status": "planned", "reason": "no_design_basis"}, docs.outputs["pending_documents"])
        self.assertNotIn("epc_descriptive_report.build_descriptive_report", [c["function"] for c in docs.engine_calls])

    def test_an_engine_error_blocks_with_its_message(self):
        ctx = context()
        run(ctx, stop_after=15, run_id="r", stages=[s for s in STAGES if s.number != 14])
        with mock.patch("epc_descriptive_report.build_descriptive_report", side_effect=ValueError("boom")):
            docs = STAGES[14].run(ctx)
        self.assertEqual(docs.status, "blocked")
        self.assertIn("descriptive report: boom", docs.message)


class ModuleTests(unittest.TestCase):
    def test_exports(self):
        self.assertIs(pipeline.STAGES, STAGES)
        self.assertEqual(EC.engine_tag({"id": "01", "kind": "lighting"}), "L-01")
        self.assertEqual(EC.engine_tag({"id": "L-01", "kind": "lighting"}), "L-01")


if __name__ == "__main__":
    unittest.main()
