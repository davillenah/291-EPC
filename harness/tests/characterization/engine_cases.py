"""Characterization of every engine (COD-13): what each one gives today for a fixed set of fictional inputs, written down before any conversion.

Golden file: `golden/engines.json` (what the code gave on 2026-11-23). To record it again after a change the owner wants, run

    python harness/tests/characterization/engine_cases.py --write

Three kinds of case:
* numeric engines: a list of `(engine, "module.function", args, kwargs)` called one by one; the value (or the error text) is stored;
* document engines (boq, datasheets, rfq, terminal blocks, design basis, descriptive report): the whole result for a small fictional board;
* the drawing and document engines that have their own golden files (`epc_drawing`, `epc_documents`, `epc_aea90364`) keep them: see `ALREADY_PINNED`.
Errors are part of the behaviour: a call that raises is stored as `{"error": "<Type>: <text>"}`.
"""
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLDEN = HERE / "golden" / "engines.json"
REPO = HERE.parents[2]

# Engines whose behaviour is already pinned by their own golden files (do not repeat them here).
ALREADY_PINNED = {
    "epc_drawing": "harness/src/engines/cad/drawing/tests/golden",
    "epc_documents": "harness/src/engines/quality/documents/tests/golden",
    "epc_aea90364": "harness/src/engines/calculation/aea90364/tests/golden",
    "epc_cutlist": "harness/src/engines/fabrication/cutlist/tests",   # hand-checked numbers asserted in the engine's own tests
    "epc_walls": "harness/src/engines/bim/walls/tests",
    "epc_expr": "harness/src/engines/geometry/expr/tests",           # hand-checked values asserted in the engine's own tests
    "epc_select": "harness/src/engines/quality/select/tests",           # hand-checked selections asserted in the engine's own tests
    "epc_changes": "harness/src/engines/quality/changes/tests",           # hand-checked change summaries asserted in the engine's own tests
    "epc_arrays": "harness/src/engines/geometry/arrays/tests",       # hand-checked positions asserted in the engine's own tests
    "epc_dims": "harness/src/engines/bim/dims/tests",           # hand-checked dimensions asserted in the engine's own tests               # hand-checked geometry asserted in the engine's own tests
}

# (engine, "module.function", args, kwargs). Only fictional numbers.
CALLS = [
    ("epc_calc_common", "num", (5, "x"), {}),
    ("epc_calc_common", "num", (-1, "x"), {}),
    ("epc_calc_common", "pos", (0, "x"), {}),
    ("epc_calc_common", "frac", (1.5, "x"), {}),
    ("epc_calc_common", "round_down_2", (3.14159,), {}),
    ("epc_calc_common", "round_up_2", (3.14159,), {}),
    ("epc_feeder_sizing", "pe_section", (35,), {}),
    ("epc_feeder_sizing", "neutral_section", (70,), {}),
    ("epc_feeder_sizing", "iz_admisible", (16,), {}),
    ("epc_feeder_sizing", "resistencia_cu_ohm_km", (16,), {}),
    ("epc_feeder_sizing", "section_min_circuit", ("tomacorrientes",), {}),
    ("epc_feeder_sizing", "k_material", ("cu", "pvc"), {}),
    ("epc_feeder_sizing", "seccion_minima_mm2", (10000, 0.5, 115), {}),
    ("epc_feeder_sizing", "verificar_i2t", (10000, 0.5, 115, 16), {}),
    ("epc_feeder_sizing", "tiempo_maximo_s", (10000, 115, 16), {}),
    ("epc_feeder_sizing", "seccion_comercial_superior", (13.2, [1.5, 2.5, 4, 6, 10, 16, 25]), {}),
    ("epc_feeder_sizing", "thd_pct", ({1: 100, 3: 20, 5: 10},), {}),
    ("epc_feeder_sizing", "factor_harmonics", (22,), {}),
    ("epc_feeder_sizing", "current_neutral_harmonics", (100, 30), {}),
    ("epc_grounding", "ra_maxima", (0.03,), {}),
    ("epc_grounding", "verifica_ra", (20, 0.03), {}),
    ("epc_grounding", "tiempo_desconexion_max_s", ("TN", 230), {}),
    ("epc_grounding", "tiempo_seccional_max_s", ("TN",), {}),
    ("epc_grounding", "resistance_rod", (100, 2.4, 0.016), {}),
    ("epc_grounding", "resistance_parallel", ([10, 20, 30],), {}),
    ("epc_grounding", "seccion_pe_mm2", (35,), {}),
    ("epc_grounding", "zs_maxima", (230, 160), {}),
    ("epc_load_balance", "grade_electrification_771", ("vivienda", 80), {}),
    ("epc_load_balance", "coef_simultaneity_771", ("elevado",), {}),
    ("epc_load_balance", "coef_simultaneity_770", (8,), {}),
    ("epc_load_balance", "msd_lighting_general", (12,), {}),
    ("epc_load_balance", "dpms_total", (8000, 0.8, 2000), {}),
    ("epc_load_balance", "imbalance_phases", ([20, 30, 25],), {}),
    ("epc_load_balance", "corriente_trifasica", (15000, 400, 0.9), {}),
    ("epc_load_balance", "corriente_monofasica", (2300, 230, 0.95), {}),
    ("epc_selectivity", "i2_convencional", (16,), {}),
    ("epc_selectivity", "in_max_por_iz", (40,), {}),
    ("epc_selectivity", "verifica_tn", (0.8, 160), {"u0_v": 230}),
    ("epc_selectivity", "verifica_tt", (20, 0.03), {}),
    ("epc_selectivity", "corriente_falla_tt", (230, 20, 10), {}),
    ("epc_short_circuit", "factor_c", (6,), {}),
    ("epc_short_circuit", "corriente_asignada_trafo", (630000, 400), {}),
    ("epc_short_circuit", "impedancia_red", (400, 1.0), {"sk_va": 250e6}),
    ("epc_short_circuit", "impedancia_transformador", (630000, 400, 6), {}),
    ("epc_short_circuit", "impedance_cable", (0.727, 0.08, 30), {}),
    ("epc_short_circuit", "ik_desde_impedancia", (400, 1.0, 0.001, 0.005), {}),
    ("epc_short_circuit", "factor_kappa", (0.001, 0.005), {}),
    ("epc_short_circuit", "corriente_pico", (20000, 0.001, 0.005), {}),
    ("epc_short_circuit", "ik_aguas_abajo", (400, 20000, 35, 40), {}),
    ("epc_short_circuit", "aporte_motor", (50000, 400, 6, 1.0), {}),
    ("epc_voltage_drop", "drop_unit_table", (16,), {}),
    ("epc_voltage_drop", "limite_caida_pct", ("seccional",), {}),
    ("epc_voltage_drop", "caida_tension", (3, 50, 80, 1.15, 0.09, 0.85, 400), {}),
    ("epc_voltage_drop", "caida_tension", (1, 16, 25, 7.41, 0.1, 0.9, 230), {}),
    ("epc_voltage_drop", "longitud_maxima_m", (3, 12, 50, 1.15, 0.09, 0.85), {}),
    ("epc_voltage_drop", "porcentaje", (8, 400), {}),
    ("epc_transformer_sizing", "rated_current_a", (630, 400), {}),
    ("epc_transformer_sizing", "required_apparent_power_kva", (400, 25), {}),
    ("epc_transformer_sizing", "select_rating", (520,), {}),
    ("epc_transformer_sizing", "loading_pct", (400, 630), {}),
    ("epc_transformer_sizing", "size_transformer", (400, 400, 25), {}),
    ("epc_transformer_sizing", "size_transformer", (400, 400, None), {}),
    ("epc_standards", "norm_words", ("Sección mínima del conductor 2,5 mm²",), {}),
    ("epc_standards", "shingles", (["a", "b", "c", "d", "e", "f"],), {}),
    ("epc_standards", "convert_table", ("t1", "1.1", [{"size": 1.5, "i": 15}, {"size": 2.5, "i": 21}]), {}),
    ("epc_standards", "convert_table", ("t2", "1.2", {"columnas": ["a", "b"], "filas": [[1, 2], [3]], "notas": "n"}), {}),
    ("epc_hvac", "conduction_w", (0.35, 40, 12), {}),
    ("epc_hvac", "solar_w", (6, 0.4, "W"), {}),
    ("epc_hvac", "people_w", (10,), {}),
    ("epc_hvac", "internal_w", (60, 12), {}),
    ("epc_hvac", "infiltration_ls", (150, 0.5), {}),
]


def resolve(engine, name):
    """The function `name` defined in `engine` (the package itself, or the first of its modules, in name order, that defines it)."""
    import pkgutil
    pkg = importlib.import_module(engine)
    if getattr(getattr(pkg, name, None), "__module__", "").startswith(engine):
        return getattr(pkg, name)
    for info in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda i: i.name):
        if info.name.startswith("__"):
            continue
        mod = importlib.import_module(f"{engine}.{info.name}")
        fn = getattr(mod, name, None)
        if callable(fn) and getattr(fn, "__module__", None) == mod.__name__:
            return fn
    raise LookupError(f"{engine}.{name} not found")


def plain(value):
    """A JSON-safe copy: tuples as lists, sets sorted, floats rounded to 9 places, anything else as its text."""
    if isinstance(value, bool) or value is None or isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        return round(value, 9)
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(plain(v) for v in value)
    if hasattr(value, "__dataclass_fields__"):
        return plain({k: getattr(value, k) for k in value.__dataclass_fields__})
    if hasattr(value, "as_dict"):
        return plain(value.as_dict())
    return repr(value)


def attempt(fn, *args, **kwargs):
    try:
        return plain(fn(*args, **kwargs))
    except Exception as e:      # noqa: BLE001 - a characterization stores every outcome, an error included
        return {"error": f"{type(e).__name__}: {e}"}


def numeric():
    out = {}
    for engine, name, args, kwargs in CALLS:
        key = f"{name}({', '.join(map(repr, args))}{''.join(f', {k}={v!r}' for k, v in kwargs.items())})"
        out.setdefault(engine, {})[key] = attempt(resolve(engine, name), *args, **kwargs)
    return out


# ---- the document engines: the whole result for a small fictional board -------------------------------------------------------------------------------

def _circuit(tag, **changes):
    base = {"tag": tag, "phases": 1, "s_mm2": 2.5, "neutral_mm2": 2.5, "pe_mm2": 2.5, "length_m": 10.0, "material": "cu", "insulation": "pvc",
            "device_kind": "mcb", "in_a": 16, "poles": 2, "breaking_capacity_ka": 6}
    base.update(changes)
    return base


BOARD = [_circuit("C1"), _circuit("C2", length_m=22.5), _circuit("C3", phases=3, s_mm2=10, neutral_mm2=10, pe_mm2=10, device_kind="mccb", in_a=100, poles=3, breaking_capacity_ka=25),
         _circuit("C4", s_mm2=1.5, neutral_mm2=1.5, pe_mm2=1.5, in_a=10)]
CATALOG = [{"manufacturer": "m1", "category": "breakers", "products": [
    {"id": "p1", "family": "Fam p1", "type": "mccb", "status": "unverified", "source": "https://example.test/p1", "rated_current_a": {"min": 16, "max": 160},
     "standards": ["IEC 60947-2"], "breaking_capacity": [{"class": "N", "voltage_v": 400, "icu_ka": 25}, {"class": "H", "voltage_v": 400, "icu_ka": 36}]}]}]
PROFILE = {"project_code": "P-1", "client": {"name": "Cliente SA", "contact": None}, "site": {"address": "Calle 1", "country": "AR", "installation_type": "dwelling"},
           "supply": {"source": "utility", "voltage": {"value": 400, "unit": "V"}, "earthing_system": "TN", "short_circuit_level": {"value": 10, "unit": "kA", "origin": "utility letter"}},
           "normative_profile": {"jurisdiction": "AR", "revisions": {"90364-7-771": "2006", "parts_4_and_5": None}}, "criteria": {"set": "default", "exceptions": ["E1"]}, "language": "es"}
TERMS = {"suppliers": [{"name": "Alfa", "contact": "alfa@example.test"}, {"name": "Beta"}], "currency": "ARS", "response_deadline": "2026-12-15", "delivery_site": "Obra Central", "validity_days": 30}


def documents():
    from epc_boq import build_boq, render_rows as boq_rows
    from epc_datasheets import build_datasheets, render_rows as ds_rows, requirements_from_circuits
    from epc_descriptive_report import build_descriptive_report, descriptive_report_to_text
    from epc_design_basis import build_design_basis_document, design_basis_to_text
    from epc_rfq import build_rfq, render_rows as rfq_rows, rfq_to_text
    from epc_terminal_blocks import build_terminal_list, render_rows as tb_rows
    out = {}
    boq = attempt(build_boq, "TG-1", BOARD, allowance_pct=10)
    out["epc_boq"] = {"build_boq": boq, "render_rows": attempt(lambda: boq_rows(build_boq("TG-1", BOARD, allowance_pct=10))),
                      "no_allowance": attempt(build_boq, "TG-1", BOARD)}
    requirements = attempt(requirements_from_circuits, BOARD, 400)
    sheets = attempt(build_datasheets, "TG-1", requirements, CATALOG) if isinstance(requirements, list) else requirements
    out["epc_datasheets"] = {"requirements_from_circuits": requirements, "build_datasheets": sheets,
                             "render_rows": attempt(lambda: ds_rows(build_datasheets("TG-1", requirements_from_circuits(BOARD, 400), CATALOG)))}
    real_boq = build_boq("TG-1", BOARD, allowance_pct=10)
    out["epc_rfq"] = {"build_rfq": attempt(build_rfq, "TG-1", real_boq, **TERMS), "text": attempt(lambda: rfq_to_text(build_rfq("TG-1", real_boq, **TERMS))),
                      "render_rows": attempt(lambda: rfq_rows(build_rfq("TG-1", real_boq, **TERMS))), "no_terms": attempt(build_rfq, "TG-1", real_boq)}
    TB = [{k: c[k] for k in ("tag", "phases", "s_mm2", "pe_mm2", "neutral_mm2")} for c in BOARD]
    terminals = attempt(build_terminal_list, "TS", TB)
    out["epc_terminal_blocks"] = {"build_terminal_list": terminals, "render_rows": attempt(lambda: tb_rows(build_terminal_list("TS", TB)))}
    basis = attempt(build_design_basis_document, PROFILE, criteria={"exceptions": ["E2"]}, assumptions=[{"text": "t", "reason": "r"}],
                    requirements={"items": [{"id": "R-001", "text": "x", "source": "client", "status": "open"}]})
    out["epc_design_basis"] = {"build_design_basis_document": basis,
                               "text": attempt(lambda: design_basis_to_text(build_design_basis_document(PROFILE, criteria={"exceptions": ["E2"]})))}
    if isinstance(basis, dict) and "error" not in basis:
        report = attempt(build_descriptive_report, basis, BOARD, terminals={"totals": {"terminals": 12}}, boq={"totals": {"lines": 7, "devices": 4, "cable_m": 55.5}},
                         pending_documents=[{"name": "specification", "status": "planned"}], unreviewed_norm_records=9)
        out["epc_descriptive_report"] = {"build_descriptive_report": report,
                                         "text": attempt(lambda: descriptive_report_to_text(build_descriptive_report(basis, BOARD)))}
    return out


# ---- the engines that take a whole document and give a result -------------------------------------------------------------------------------------

def _pv_weather(days=3):
    import math
    ghi, dni, dhi = [], [], []
    for h in range(24 * days):
        x = math.sin(math.pi * (h % 24 - 6) / 12.0) if 6 <= h % 24 <= 18 else 0.0
        ghi.append(round(900 * x, 1)), dni.append(round(700 * x, 1)), dhi.append(round(150 * x, 1))
    return {"start": "2023-01-01T00:00", "utc_offset_h": -3, "step_minutes": 60, "ghi": ghi, "dni": dni, "dhi": dhi, "temp_air_c": [20.0] * 24 * days, "wind_ms": [2.0] * 24 * days}


PV_DOC = {"site": {"latitude_deg": -34.6, "longitude_deg": -58.4, "albedo": 0.2, "design_t_min_c": -5}, "weather": _pv_weather(),
          "arrays": [{"id": "A1", "tilt_deg": 30, "azimuth_deg": 0, "n_modules": 1000, "dc_ac_ratio": 1.2,
                      "module": {"pmax_w": 550.0, "voc_v": 49.9, "vmp_v": 41.8, "isc_a": 13.9, "imp_a": 13.16, "beta_voc_pct_c": -0.27, "gamma_pmax_pct_c": -0.34},
                      "inverter": {"pac0_w": 100000.0, "mppt_v_min": 200.0, "mppt_v_max": 1000.0, "vdc_max_v": 1100.0, "n_mppt": 10, "i_max_input_a": 30.0, "isc_max_input_a": 45.0}}]}
HVAC_DOC = {"design": {"t_out_c": 35, "t_in_c": 24, "w_out_kg_kg": 0.018, "w_in_kg_kg": 0.0093, "supply_delta_t_k": 10},
            "spaces": [{"id": "S1", "name": "Office", "area_m2": 50, "height_m": 3, "use": "office", "occupants": 10, "lighting_w_m2": 10, "equipment_w_m2": 15,
                        "envelope": [{"kind": "wall", "area_m2": 30, "u_w_m2k": 0.5}, {"kind": "window", "area_m2": 6, "u_w_m2k": 2.8, "shgc": 0.4, "orientation": "W"}]}]}


def run_engines():
    import epc_hvac, epc_pv, epc_receptacles, epc_lighting
    out = {"epc_hvac": {"run": attempt(epc_hvac.run, HVAC_DOC), "run_bad": attempt(epc_hvac.run, {"spaces": []})},
           "epc_pv": {"run": attempt(epc_pv.run, PV_DOC), "run_bad": attempt(epc_pv.run, {"site": {}})}}
    for name, mod, folder in (("epc_receptacles", epc_receptacles, "receptacles"), ("epc_lighting", epc_lighting, "lighting")):
        example = next((REPO / "harness" / "src" / "engines" / "calculation" / folder / "examples").glob("*.json"))
        out[name] = {"run": attempt(mod.run, json.loads(example.read_text(encoding="utf-8"))), "run_bad": attempt(mod.run, {"schema_version": "1.0"})}
    return out


def more_engines():
    """The rules engine over two small fictional standards, the plan engine over its sample, and the pipeline of the synthetic project for the rest."""
    from epc_rules import RuleSet, compare, match_when
    std_a = {"schema_version": "1.1", "standard": {"id": "TEST-1", "country": "ZZ", "body": "T", "edition": "1", "domain": "electrical"}, "source_status": "verified",
             "validated_by": "t", "validated_on": "2026-01-01",
             "tables": [{"id": "t1", "clause": "1.1", "columns": ["size", "ampacity"], "rows": [[1.5, 15], [2.5, 21]]}],
             "rules": [{"id": "tray.reserve", "clause": "1.2", "topic": "trays", "type": "mandatory", "summary": {"es": "Reserva minima"},
                        "applies_to": {"installation_types": ["dwellings"]}, "params": {"reserve_min_pct": 20}, "check": {"field": "reserve_pct", "op": ">=", "value": 20}},
                       {"id": "no.diag", "clause": "1.4", "topic": "conduits", "type": "prohibited", "summary": {"es": "Sin diagonal"},
                        "check": {"field": "diagonal", "op": "==", "value": True}}]}
    out = {"epc_rules": {"compare": [attempt(compare, 25, ">=", 20), attempt(compare, "a", "<", 3), attempt(compare, 1, "??", 1)],
                         "match_when": [attempt(match_when, {"a": 1, "c": {"lt": 5}}, {"a": 1, "c": 4}), attempt(match_when, {"a": 1}, {})]}}
    rs = attempt(lambda: RuleSet([std_a], env="dev"))
    if not isinstance(rs, dict):
        rs = RuleSet([std_a], env="dev")
        out["epc_rules"].update({"query": attempt(lambda: [r["id"] for r in rs.query(topic="trays")]), "param": attempt(rs.param, "tray.reserve", "reserve_min_pct"),
                                 "lookup": attempt(rs.lookup, "t1", size=2.5),
                                 "check": attempt(rs.check, {"reserve_pct": 10, "diagonal": True}, installation_type="dwellings")})
    plan_dir = REPO / "harness" / "src" / "engines" / "cad" / "plan" / "tests" / "fixtures" / "plan"
    from epc_plan import core
    arch_tests = REPO / "harness" / "src" / "engines" / "cad" / "arch" / "tests"
    sys.path.insert(0, str(arch_tests))
    import helpers
    from epc_arch import recognize
    out["epc_arch"] = {"flat": attempt(lambda: recognize(helpers.room_dxf(), "flat.dxf").as_dict()),
                       "flat_in_millimetres": attempt(lambda: recognize(helpers.room_dxf(unit=1000.0, insunits=4), "flat.dxf").as_dict()),
                       "not_a_plan": attempt(recognize, b"not a drawing", "x.dxf")}
    out["epc_plan"] = {"process": attempt(core.process, json.loads((plan_dir / "input.json").read_text(encoding="utf-8"))),
                       "process_bad": attempt(core.process, {"schema_version": "1.0"})}
    return out


# Which engines the stages of the synthetic project exercise (stage slug -> engines); the project is the fictional `synthetic_lv_small` with the drawing date pinned.
STAGES = {"intake": ["epc_calc_common"], "requirements_inputs": ["epc_design_basis"], "loads_demand": ["epc_load_balance", "epc_calc_common"],
          "supply_transformer": ["epc_transformer_sizing", "epc_short_circuit"], "board_structure": ["epc_load_balance"],
          "cable_sizing": ["epc_feeder_sizing", "epc_voltage_drop", "epc_aea90364"], "selectivity": ["epc_selectivity"], "earthing": ["epc_grounding"],
          "calc_check": ["epc_calc_check", "epc_rules"], "drawings": ["epc_sld", "epc_mld", "epc_dxf", "epc_symbols", "epc_titleblock", "epc_drawing"],
          "documents": ["epc_documents", "epc_boq", "epc_datasheets", "epc_rfq", "epc_terminal_blocks", "epc_descriptive_report", "epc_design_basis"],
          "package_issue": ["epc_documents"]}


def pipeline():
    """The whole synthetic project, pinned: the statuses and a SHA-256 of every file of the `.epc/ssot` folder and of every delivered file (names, not paths of the machine)."""
    import hashlib
    import os
    before = os.environ.get("EPC_RUN_MODE")
    os.environ["EPC_RUN_MODE"] = "edit"                  # the same mode whoever calls (the test suite pins production)
    sys.path.insert(0, str(REPO / "harness" / "tests" / "integration"))
    import synthetic_lv as S
    run = S.SyntheticRun(drawing_date="2026-03-04")
    try:
        run.init()
        code, answer = run.run()
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()    # noqa: E731
        ssot = {p.name: digest(p) for p in run.stage_files()}
        delivered = {str(p.relative_to(run.project)): digest(p) for p in sorted((run.project / "deliverables").rglob("*")) if p.is_file()}
        return {"exit_code": code, "stage_files": ssot, "delivered": delivered, "engines_by_stage": STAGES}
    finally:
        run.cleanup()
        os.environ.pop("EPC_RUN_MODE") if before is None else os.environ.__setitem__("EPC_RUN_MODE", before)


def everything():
    out = numeric()
    out.update(documents())
    out.update(more_engines())
    out["pipeline"] = pipeline()
    for k, v in run_engines().items():
        out.setdefault(k, {}).update(v)
    return out


def paths():
    """Put the repository's engines on sys.path the way the gate does."""
    sys.path.insert(0, str(REPO / "harness" / "tools" / "ci"))
    import run_gate
    sys.path[:0] = [p for p in run_gate.HARNESS_ENV["PYTHONPATH"].split(__import__("os").pathsep) if p]


if __name__ == "__main__":
    paths()
    result = everything()
    if "--write" in sys.argv:
        GOLDEN.write_text(json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(f"written {GOLDEN} ({sum(len(v) for v in result.values())} cases)")
    else:
        print(json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False))
