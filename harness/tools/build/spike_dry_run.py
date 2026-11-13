#!/usr/bin/env python3
"""Spike dry run (MIG-44p): the ten criteria of PRD section 21 evaluated on the SYNTHETIC project, not on the 309 kVA project.

  python harness/tools/build/spike_dry_run.py            run the synthetic project and write harness/docs/validation/SPIKE_DRY_RUN.md
  python harness/tools/build/spike_dry_run.py --check    exit 1 when the file on disk differs from what a fresh dry run generates

The dry run is HONEST: every criterion function EXECUTES something (a pipeline run through the real `epc` CLI, a second run, mutated copies of the
result, a permission matrix, the guard hook, a correction with a rerun) and reports one status:

  pass                 all of the criterion is demonstrated by the synthetic run and an automated check
  partial              demonstrated except an identified gap
  needs_owner_values   cannot be evaluated without the owner's 309 kVA reference values and tolerances (criteria 2 and 4); only the plumbing is checked
  fail                 a requirement is not met
  not_instrumented     nothing measures it

Nothing here changes pipeline behaviour or makes a criterion pass: the script only measures. Everything runs in temporary folders. The report is for the
owner and is written in Spanish; every number in it is COMPUTED from the run (`facts` of each result) and never typed. Timings are printed to the
console, never written to the report, so the file is reproducible. The 309 kVA reference values and tolerances are the owner's (MIG-42) and are never
read, invented or written here; criteria 2 and 4 are compared in MIG-44 once they exist.

Needs the engine packages: the script puts `harness/src` and every engine `src` on `sys.path` itself and imports the integration helper
`harness/tests/integration/synthetic_lv.py` the way the tests do (a full run takes about half a minute).
"""
import argparse
import contextlib
import copy
import importlib
import importlib.util
import io
import json
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REPORT = REPO / "harness" / "docs" / "validation" / "SPIKE_DRY_RUN.md"
STATUSES = ("pass", "partial", "needs_owner_values", "fail", "not_instrumented")
STATUS_ES = {"pass": "cumple", "partial": "parcial", "needs_owner_values": "requiere valores del dueño", "fail": "falla",
             "not_instrumented": "sin medición"}
# Names that contain digits but are identifiers, not numbers: the report may carry them typed (the test removes them before it looks for digits).
IDENTIFIER_PATTERN = (r"309 kVA|PRD §\d+|§\d+|MIG-[0-9A-Za-z]+|IM-01|CC-[A-Z]\d+|CC-R\d+|[Dd]21|D\d+|\bC\d{1,2}\b|\bR[01]\b|SYNTH-001|SHA-256|IEC \d+|"
                      r"sha256|ezdxf|\bxlsx\b|\bDXF\b|\b[A-Z]{1,2}-\d+\b|[Ee]tapas? \d+")
M = SimpleNamespace()

DOC_ENGINE = {"calculation_memo": "board_memo", "project_summary": "board_memo", "terminal_block_list": "epc_terminal_blocks", "boq": "epc_boq",
              "datasheets": "epc_datasheets", "rfq": "epc_rfq", "design_basis": "epc_design_basis", "descriptive_report": "epc_descriptive_report"}
TITLES = {
    1: "El pipeline corre de project_profile.json hasta deliverables/ sin edición manual",
    2: "Los resultados de cálculo están dentro de las tolerancias del dueño frente a valores de referencia independientes",
    3: "Cada número de cada entregable es trazable a una llamada a motor y a sus registros de norma",
    4: "Las cantidades de listas y BOQ están dentro de las tolerancias del dueño frente a la referencia",
    5: "Dos corridas con las mismas entradas dan los mismos hashes de salida",
    6: "Todo error sembrado en una copia de las entradas lo detecta calc_check o una compuerta",
    7: "Los valores de norma sin revisar se listan y bloquean approved_for_construction",
    8: "Los agentes no pueden escribir ssot/, deliverables/ ni inputs/ directamente",
    9: "El costo y el tiempo por corrida se registran por agente y quedan dentro de las metas del dueño",
    10: "Una corrección re-ejecuta solo las etapas afectadas y marca como reemplazadas las firmas previas",
}


# ------------------------------------------------------------------ setup
def setup_path():
    """Put the harness sources, every engine and the test helpers on sys.path (what the gate's PYTHONPATH does)."""
    sys.path.insert(0, str(REPO / "harness" / "tools"))
    import epc_paths as P
    extra = [REPO / "harness" / "src", REPO / "harness" / "src" / "platform", REPO / "harness" / "src" / "platform" / "mcp" / "src",
             *[P.engine_src(a) for a in P.engine_names()], REPO / "harness" / "tests" / "integration", REPO / "harness" / "tests" / "unit"]
    for path in reversed(extra):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def load_modules():
    """Import the platform, the discipline and the integration helper once (names on the namespace `M`)."""
    if hasattr(M, "S"):
        return
    setup_path()
    M.S = importlib.import_module("synthetic_lv")
    M.store = importlib.import_module("disciplines.electrical_lv.store")
    M.manifest = importlib.import_module("disciplines.electrical_lv.manifest")
    M.pipeline = importlib.import_module("disciplines.electrical_lv.pipeline")
    M.stages = importlib.import_module("disciplines.electrical_lv.stages")
    M.calc_stage = importlib.import_module("disciplines.electrical_lv.stages.calc_check_stage")
    M.calc_check = importlib.import_module("epc_calc_check")
    M.perm = importlib.import_module("epc_platform.permissions")
    M.rules = importlib.import_module("epc_platform.permissions.rules")
    M.events = importlib.import_module("epc_platform.events")
    M.workflow = importlib.import_module("epc_platform.workflow")
    M.seeded = importlib.import_module("test_calc_check_seeded")


# ------------------------------------------------------------------ small helpers
def result(number, status, evidence, gaps=(), facts=None):
    """One criterion result: {criterion, title, status, evidence, gaps, facts}. `facts` holds the computed numbers the texts quote."""
    assert status in STATUSES, status
    return {"criterion": number, "title": TITLES[number], "status": status, "evidence": list(evidence), "gaps": list(gaps), "facts": dict(facts or {})}


def numeric_leaves(value, path=""):
    """(path, number) of every numeric leaf (bool excluded) of a JSON value."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield from numeric_leaves(item, f"{path}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from numeric_leaves(item, f"{path}/{index}")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield path, value


def strings_of(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from strings_of(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings_of(item)
    elif isinstance(value, str):
        yield value


TOKEN = re.compile(r"(?<![\w.,-])\d+(?:[.,]\d+)?(?![\w-])")


def text_numbers(document):
    """Number tokens typed in the text of a document (tables and paragraphs), not counting identifiers such as `90364-7-771`."""
    return sum(len(TOKEN.findall(text)) for text in strings_of(document))


def key_names(value, out=None):
    """Every dict key found anywhere in a JSON value."""
    out = set() if out is None else out
    if isinstance(value, dict):
        for key, item in value.items():
            out.add(str(key))
            key_names(item, out)
    elif isinstance(value, list):
        for item in value:
            key_names(item, out)
    return out


def all_calls(run_dict):
    return [call for r in run_dict["results"] for call in r["engine_calls"]]


def files_of(project):
    return {p.relative_to(project).as_posix(): p for p in sorted(project.rglob("*")) if p.is_file()}


def stage_of(run_dict, number):
    return next(r for r in run_dict["results"] if r["stage"] == number)


def dxf_bytes(proj):
    out14 = proj.ssot("stage_14_drawings.json")["outputs"]
    base = proj.project / ".epc" / "runs" / proj.run_id / out14["directory"]
    return {f"{out14['directory']}/{f['path']}": (base / f["path"]).read_bytes() for f in out14["files"] if f["path"].endswith(".dxf")}


# ------------------------------------------------------------------ the runs the criteria share
class DryRun:
    """The temporary synthetic projects of the dry run. Each is created on first use and cleaned up by `close()`."""

    def __init__(self):
        load_modules()
        self.stack = contextlib.ExitStack()
        self.cache = {}

    def close(self):
        self.stack.close()

    def started(self, key, run_id=None, drawing_date=None):
        """A fresh synthetic project run through the real CLI (init + run), cached by `key`; with `drawing_date` the run pins the dates and GUIDs of the drawings (MIG-3Z)."""
        if key not in self.cache:
            proj = M.S.SyntheticRun(run_id, drawing_date=drawing_date) if run_id else M.S.SyntheticRun(drawing_date=drawing_date)
            self.stack.callback(proj.cleanup)
            self.cache[key] = proj.start()
        return self.cache[key]

    @property
    def primary(self):
        return self.started("primary")

    @property
    def run_dict(self):
        return self.primary.run_result[1]["data"]["run"]

    @property
    def check_project(self):
        """The engine inputs `calc_check` recomputes from, taken from an in-process run of stages 1-13 of the same inputs."""
        if "check_project" not in self.cache:
            aux = M.S.SyntheticRun()
            self.stack.callback(aux.cleanup)
            aux.init()
            store = M.store.ProjectStore(aux.project)
            ctx = M.stages.PipelineContext(answers=store.read_answers(), loads=M.S.read_json(M.S.GOLDEN / "loads.json"), engine_inputs=aux.engine_inputs,
                                           store=store, revision="R0")
            M.pipeline.run(ctx, stop_after=13, run_id=M.S.RUN_ID, clock=M.S.clock)
            self.cache["check_project"] = M.calc_stage.engine_inputs_for_check(ctx)
        return self.cache["check_project"]

    @property
    def correction(self):
        if "correction" not in self.cache:
            self.cache["correction"] = run_correction(self)
        return self.cache["correction"]


# ------------------------------------------------------------------ C1
def inputs_state(proj):
    """(frozen inputs unchanged after the run, loads copy equal to the file given to the run, engine inputs copy equal to the file given)."""
    store = M.store.ProjectStore(proj.project)
    loads = (proj.project / "inputs" / "loads" / "loads.json").read_bytes() == (M.S.GOLDEN / "loads.json").read_bytes()
    engine = (proj.project / "inputs" / "engine_inputs.json").read_bytes() == proj.engine_inputs_file.read_bytes()
    return store.verify_inputs_unchanged("dry-run") == [], loads, engine


def c1(run):
    proj, res = run.primary, run.run_dict
    code, env = proj.run_result
    statuses = [r["status"] for r in res["results"]]
    unchanged, loads_same, engine_same = inputs_state(proj)
    profile_same = M.S.read_json(proj.project / ".epc" / "project_profile.json") == stage_of(res, 1)["outputs"]["profile"]
    facts = {"stages": len(statuses), "stages_ok": statuses.count("ok"), "manifests": len(proj.manifests()), "dxf_files": len(dxf_bytes(proj))}
    broken = code != 0 or not env["ok"] or statuses.count("ok") != len(statuses) or not facts["manifests"] or not unchanged or not profile_same
    evidence = [f"La corrida por el CLI real (init y run) terminó con {facts['stages_ok']} de {facts['stages']} etapas en estado ok y produjo {facts['manifests']} manifiestos "
                f"y {facts['dxf_files']} planos DXF bajo deliverables/.",
                "Después de la corrida las entradas congeladas siguen idénticas a su hash y el perfil del proyecto es el que produjo la etapa 1: nadie editó nada a mano.",
                "El perfil se produce en la etapa 1 a partir de las respuestas de intake (no se lee un project_profile.json escrito de antemano)."]
    gaps = []
    if not engine_same:
        gaps.append("Las entradas de motor que usó la corrida (engine_inputs, con la carpeta del catálogo resuelta) no son byte a byte la copia congelada en inputs/: "
                    "la corrida no se ata a lo congelado.")
    if run.correction["unfrozen_loads_accepted"]:
        gaps.append("Las cargas llegan a la corrida como argumento del CLI y no se leen de inputs/: una lista de cargas distinta de la congelada se acepta sin bloqueo IM-01.")
    facts["loads_copy_equal"] = int(loads_same)
    status = "fail" if broken else ("partial" if gaps else "pass")
    return result(1, status, evidence, gaps, facts)


# ------------------------------------------------------------------ C2 and C4 (plumbing only)
def stage_number(label):
    return int(label.split(" - ")[0])


def keys_in_stage(res, number):
    return key_names(stage_of(res, number)["outputs"])


def template_state():
    """The spike input template read back: (sheets present, reference rows, owner cells that hold a value (must be zero))."""
    V = importlib.import_module("validation_templates")
    from openpyxl import load_workbook
    book = load_workbook(V.OUT_DIR / V.SPIKE)
    ref, tol = book["Valores de referencia"], book["Tolerancias"]
    filled = sum(1 for row in ref.iter_rows(min_row=2, min_col=5, max_col=8) for c in row if c.value not in (None, ""))
    filled += sum(1 for row in tol.iter_rows(min_row=2, min_col=2, max_col=2) for c in row if c.value not in (None, ""))
    return V, ref.max_row - 1, filled


def c2(run):
    V, rows, filled = template_state()
    res = run.run_dict
    listed = [(stage_number(s), k) for s, k, *_ in V.REFERENCE_QUANTITIES]
    present = [(n, k) for n, k in listed if k in keys_in_stage(res, n)]
    missing = [f"etapa {n} clave {k}" for n, k in listed if (n, k) not in present]
    facts = {"template_rows": rows, "quantities_listed": len(listed), "quantities_in_outputs": len(present), "owner_cells_filled": filled,
             "circuits": len(stage_of(res, 8)["outputs"]["circuits"])}
    evidence = [f"La plantilla del spike lista {facts['quantities_listed']} magnitudes de cálculo por comparar y la corrida sintética las entrega todas en las salidas de sus etapas: "
                f"{facts['quantities_in_outputs']} de {facts['quantities_listed']} presentes, para {facts['circuits']} circuitos.",
                f"Las celdas del dueño (valor de referencia y tolerancias) están vacías en la plantilla: {facts['owner_cells_filled']} celdas con valor.",
                "La comparación en sí es la tarea MIG-44, cuando existan los valores de referencia y las tolerancias del dueño (MIG-42 y PRD §24)."]
    gaps = [f"Falta en las salidas: {m}." for m in missing]
    status = "needs_owner_values" if not missing else "fail"
    return result(2, status, evidence, gaps, facts)


def boq_plumbing(res):
    """For each quantity list of the template: does stage 15 produce the document with line items? -> (documents present, total documents asked)."""
    docs = {d["name"]: d["document"] for d in stage_of(res, 15)["outputs"]["documents"]}
    return {"boq": "boq" in docs and bool(docs["boq"]), "terminal_block_list": "terminal_block_list" in docs and bool(docs["terminal_block_list"])}


def c4(run):
    V, _rows, filled = template_state()
    res = run.run_dict
    present = boq_plumbing(res)
    asked = len(V.BOQ_QUANTITIES)
    facts = {"boq_quantities_listed": asked, "documents_present": sum(present.values()), "documents_asked": len(present), "owner_cells_filled": filled}
    evidence = [f"La plantilla lista {asked} cantidades de lista o BOQ por comparar; la corrida sintética produce {facts['documents_present']} de {facts['documents_asked']} "
                "documentos de cantidades (BOQ y lista de bornes) en la etapa 15.",
                "La referencia y la tolerancia de cantidades las pone el dueño (celdas vacías en la plantilla); la comparación es la tarea MIG-44."]
    gaps = [f"No se produjo el documento {name}." for name, ok in present.items() if not ok]
    return result(4, "needs_owner_values" if not gaps else "fail", evidence, gaps, facts)


# ------------------------------------------------------------------ C3
def stage_coverage(res):
    """Per stage: (stage number, numeric leaves, engine calls, the distinct key paths of the leaves)."""
    rows = []
    for r in res["results"]:
        leaves = list(numeric_leaves(r["outputs"]))
        top = sorted({"/".join(p.split("/")[1:3]) for p, _ in leaves})
        rows.append((r["stage"], len(leaves), len(r["engine_calls"]), top))
    return rows


def document_state(res):
    """Documents with number tokens whose engine left no call in stage 15: [(name, tokens)]; plus the total of tokens."""
    stage15 = stage_of(res, 15)
    functions = [c["function"] for c in stage15["engine_calls"]]
    docs = stage15["outputs"]["documents"]
    unmatched = [d["name"] for d in docs if text_numbers(d["document"]) and not any(DOC_ENGINE.get(d["name"], "?") in f for f in functions)]
    return unmatched, sum(text_numbers(d["document"]) for d in docs), len(docs)


def norm_link(run, res):
    """Engine packages of the recorded calls that appear in no norm record of the first manifest, and the total of packages."""
    manifest = M.S.read_json(run.primary.manifests()[0])
    ids = [r["id"] for r in manifest["normative_profile"]["norm_records"]]
    packages = sorted(M.manifest.packages_of(all_calls(res)))
    return [p for p in packages if not any(i.split(".")[0] == p.removeprefix("epc_") for i in ids)], len(packages)


def c3(run):
    res = run.run_dict
    rows = stage_coverage(res)
    total = sum(n for _, n, _, _ in rows)
    covered = sum(n for _, n, calls, _ in rows if calls)
    uncovered = [(s, n, top) for s, n, calls, top in rows if n and not calls]
    unmatched_docs, tokens, documents = document_state(res)
    orphan_packages, packages = norm_link(run, res)
    pct = f"{100.0 * covered / total:.1f}"
    facts = {"stages": len(rows), "numeric_leaves": total, "leaves_with_engine_call": covered, "coverage_pct": pct, "stages_with_numbers_and_no_call": len(uncovered),
             "document_number_tokens": tokens, "documents": documents, "engine_packages": packages, "packages_without_norm_record": len(orphan_packages), **{f"stage_{s}_numeric_leaves": n for s, n, _ in uncovered}}
    evidence = [f"De {total} valores numéricos de las salidas de las {len(rows)} etapas, {covered} ({pct} %) pertenecen a una etapa con al menos una llamada a motor registrada.",
                f"Los {documents} documentos de la etapa 15 traen {tokens} números escritos en su texto; cada documento tiene registrada la llamada de su motor "
                f"({len(unmatched_docs)} documentos sin llamada).",
                f"De {packages} paquetes de motor llamados, {packages - len(orphan_packages)} tienen registros de norma en los manifiestos; los otros {len(orphan_packages)} no tienen registros propios "
                "(motores de dibujo, listas y verificación)."]
    gaps = [f"Etapa {s}: {n} valores numéricos y ninguna llamada a motor (claves: {', '.join(top[:6])})." for s, n, top in uncovered]
    gaps.append("La traza es por etapa: la llamada a motor registrada (motor, función, versión) no indica qué claves de salida ni qué registros de norma produjo, "
                "así que no se puede probar número por número.")
    gaps += [f"Documento sin llamada de su motor: {name}." for name in unmatched_docs]
    return result(3, "partial", evidence, gaps, facts)


# ------------------------------------------------------------------ C5
def classify_difference(S, rel, one, two):
    """'stamped' (DXF or the xlsx the drawing engine writes), 'embedded' (JSON that differs only in the DXF hashes) or 'unexplained'."""
    if rel.endswith(".dxf") or rel.rsplit("/", 1)[-1] == "input_for_sld.xlsx":
        return "stamped"
    try:
        same = S.normalise_dxf_hashes(json.loads(one.read_bytes())) == S.normalise_dxf_hashes(json.loads(two.read_bytes()))
    except ValueError:
        return "unexplained"
    return "embedded" if same else "unexplained"


def deliverable_hashes(proj):
    return {p.name: M.S.read_json(p)["output_sha256"] for p in proj.manifests()}


PINNED_DATE = "2026-03-04"


def differences(one, two):
    """(file names, files that differ by kind, deliverables that differ) between two runs of the same inputs."""
    fa, fb = files_of(one.project), files_of(two.project)
    kinds = {"stamped": [], "embedded": [], "unexplained": []}
    for rel in fa:
        if rel in fb and fa[rel].read_bytes() != fb[rel].read_bytes():
            kinds[classify_difference(M.S, rel, fa[rel], fb[rel])].append(rel)
    ha, hb = deliverable_hashes(one), deliverable_hashes(two)
    return {"names_equal": sorted(fa) == sorted(fb), "files": len(fa), "kinds": kinds, "deliverables": len(ha), "deliverable_diffs": sorted(n for n in ha if ha[n] != hb.get(n))}


def c5(run):
    """Two runs of the same inputs and the same clock WITH the drawing date pinned (`engine_inputs.drawings.date`) must give the same bytes everywhere; the same pair without
    the date is measured too and reported as a note (the default behaviour stays: the DXF writer stamps the clock and random GUIDs)."""
    pinned = differences(run.started("pinned_a", drawing_date=PINNED_DATE), run.started("pinned_b", drawing_date=PINNED_DATE))
    plain = differences(run.primary, run.started("second"))
    diff = sum(len(v) for v in pinned["kinds"].values())
    facts = {"files": pinned["files"], "files_identical": pinned["files"] - diff, "files_differ": diff,
             "deliverables": pinned["deliverables"], "deliverables_identical": pinned["deliverables"] - len(pinned["deliverable_diffs"]),
             "unpinned_files": plain["files"], "unpinned_differ_stamped": len(plain["kinds"]["stamped"]), "unpinned_differ_embedded_hash": len(plain["kinds"]["embedded"]),
             "unpinned_differ_unexplained": len(plain["kinds"]["unexplained"]), "unpinned_deliverables_identical": plain["deliverables"] - len(plain["deliverable_diffs"])}
    evidence = [f"Dos corridas del mismo proyecto con las mismas entradas, el mismo reloj y la fecha del dibujo fijada (engine_inputs.drawings.date): de {facts['files']} archivos, "
                f"{facts['files_identical']} son idénticos byte a byte (los planos DXF y la planilla de entrada del dibujo incluidos).",
                f"{facts['deliverables_identical']} de {facts['deliverables']} entregables tienen el mismo hash de salida en sus manifiestos."]
    evidence.append(f"Nota: sin fijar la fecha del dibujo (comportamiento por defecto, sin cambios) de {facts['unpinned_files']} archivos difieren {facts['unpinned_differ_stamped']} que llevan hora o "
                    f"identificadores aleatorios (DXF y la planilla de entrada del dibujo) y {facts['unpinned_differ_embedded_hash']} JSON que solo difieren en el hash de esos DXF; "
                    f"sin explicación: {facts['unpinned_differ_unexplained']}; {facts['unpinned_deliverables_identical']} de {plain['deliverables']} entregables con el mismo hash.")
    gaps = []
    if diff or pinned["deliverable_diffs"] or not pinned["names_equal"]:
        gaps.append("Con la fecha del dibujo fijada siguen difiriendo: "
                    + ", ".join(sorted(rel for v in pinned["kinds"].values() for rel in v) + [n for n in pinned["deliverable_diffs"]]) + ".")
    status = "pass" if not gaps else ("fail" if pinned["kinds"]["unexplained"] or not pinned["names_equal"] else "partial")
    return result(5, status, evidence, gaps, facts)


# ------------------------------------------------------------------ C6
SEEDED_ERRORS = (KeyError, IndexError, StopIteration, AssertionError, TypeError, AttributeError)


def seeded_outcome(base, project, files, spec):
    """'caught', 'missed' or 'not_applicable' for one mutation of the test module's table (mutation, rule, fragment)."""
    mutation, rule, fragment = spec
    mutated = copy.deepcopy(base)
    try:
        mutation(mutated)
    except SEEDED_ERRORS:
        return "not_applicable"
    if mutated == base:
        return "not_applicable"
    found = M.calc_check.check_run(mutated, project=copy.deepcopy(project), files=files, run_id="dry-run")
    hits = [f for f in found if M.seeded.rules_of([f]) == {rule}]
    return "caught" if any(fragment in f["field"] or fragment in str(f["value"]) for f in hits) else "missed"


def dxf_flip_outcome(base, project, files):
    key = next(iter(files))
    changed = dict(files, **{key: files[key] + b" "})
    found = M.calc_check.check_run(copy.deepcopy(base), project=copy.deepcopy(project), files=changed, run_id="dry-run")
    return "caught" if "CC-D06" in M.seeded.rules_of(found) else "missed"


def changed_input_outcome(run):
    """A byte appended to a frozen input behind the store's back, then a rerun: the gate IM-01 must stop the pipeline at stage 2."""
    proj = run.started("tamper")
    path = proj.project / "inputs" / "loads" / "loads.json"
    path.write_bytes(path.read_bytes() + b" ")
    proj.work.joinpath("c.json").write_text(json.dumps([{"note": "synthetic correction"}]), encoding="utf-8")
    M.S.envelope(proj.root, "review", M.S.CODE, "--corrections", str(proj.work / "c.json"), *M.S.ENGINEER)
    code, env = proj.run(run_id="dry-tamper")
    blocked = env["data"]["run"]["results"][1]
    ok = code == 0 and blocked["status"] == "blocked" and any(f["clause"] == "project criterion IM-01" for f in blocked["findings"])
    return "caught" if ok else "missed"


def c6(run):
    base, files = run.run_dict, dxf_bytes(run.primary)
    clean = [f for f in M.calc_check.check_run(copy.deepcopy(base), project=copy.deepcopy(run.check_project), files=files, run_id="dry-run") if f["severity"] != "note"]
    outcomes = {name: seeded_outcome(base, run.check_project, files, spec) for name, spec in M.seeded.CASES.items()}
    outcomes["a byte of a drawing file changed"] = dxf_flip_outcome(base, run.check_project, files)
    outcomes["an input file changed after intake (gate)"] = changed_input_outcome(run)
    applicable = {n: o for n, o in outcomes.items() if o != "not_applicable"}
    caught = sum(1 for o in applicable.values() if o == "caught")
    missed = sorted(n for n, o in applicable.items() if o == "missed")
    facts = {"seeded_total": len(applicable), "seeded_caught": caught, "seeded_missed": len(missed), "not_applicable": len(outcomes) - len(applicable),
             "clean_run_findings_above_note": len(clean)}
    evidence = [f"Sobre una copia del resultado de la corrida se sembró un error a la vez ({facts['seeded_total']} aplicables, tomados de la tabla de test_calc_check_seeded más un "
                f"byte de un plano cambiado y una entrada cambiada tras el intake): {caught} detectados, {len(missed)} sin detectar.",
                f"La corrida limpia no tiene hallazgos por encima de nota ({facts['clean_run_findings_above_note']} hallazgos)."]
    gaps = [f"Error sembrado que no se detectó: {name}." for name in missed]
    if facts["not_applicable"]:
        gaps.append(f"Mutaciones de la tabla que no cambian nada en este proyecto o no se pueden aplicar (no cuentan en el total): {facts['not_applicable']}.")
    status = "fail" if clean or missed else "pass"
    return result(6, status, evidence, gaps, facts)


# ------------------------------------------------------------------ C7
def norm_state(run):
    out = stage_of(run.run_dict, 16)["outputs"]
    manifest = M.S.read_json(run.primary.manifests()[0])
    return out["norm_records"], manifest


def approval_attempts(run, manifest):
    """(blocked by build_manifest for unverified records, accepted when the same records are all verified, schema errors of an approved copy)."""
    records, res = manifest["normative_profile"]["norm_records"], run.run_dict
    args = dict(deliverable_id="X-DOC-x", title="x", revision="R0", run_id="dry", inputs_manifest=run.primary.ssot("inputs_manifest.json"),
                engine_calls=all_calls(res), normative_profile=manifest["normative_profile"], findings=[], output_sha256="0" * 64)
    try:
        M.manifest.build_manifest(None, review_status=M.manifest.APPROVED, norm_reader=lambda _p: records, **args)
        blocked = False
    except M.manifest.ApprovalBlocked:
        blocked = True
    verified = [dict(r, review_status=M.manifest.VERIFIED) for r in records]
    try:
        M.manifest.build_manifest(None, review_status=M.manifest.APPROVED, norm_reader=lambda _p: verified, **args)
        accepted = True
    except M.manifest.ManifestError:
        accepted = False
    forged = dict(copy.deepcopy(manifest), review_status=M.manifest.APPROVED)
    return blocked, accepted, len(M.manifest.check(forged))


def cli_approval(run):
    """The engineer of record asks to approve and to issue a project in review, through the CLI: (approve code, issue code, project reached approved or issued)."""
    proj = run.started("perm")
    wf = M.workflow.Workflow(proj.project, M.events.EventLog.for_project(proj.project, M.S.clock), M.store.ProjectStore(proj.project))
    wf.transition("submit_for_review", "engineer_of_record", "eng-1", run_id="review")
    _, approve = M.S.envelope(proj.root, "approve", M.S.CODE, *M.S.ENGINEER)
    _, issue = M.S.envelope(proj.root, "issue", M.S.CODE, *M.S.ENGINEER)
    history = [h["to"] for h in M.store.ProjectStore(proj.project).read_workflow()["history"]]
    return approve["error"]["code"], issue["ok"], ("approved" in history or "issued" in history)


def c7(run):
    listed, manifest = norm_state(run)
    blocked, accepted, schema_errors = approval_attempts(run, manifest)
    approve_code, issue_ok, reached = cli_approval(run)
    _, pending = M.S.envelope(run.primary.root, "norms-pending", *M.S.ORCHESTRATOR)
    facts = {"records_listed": listed["listed"], "records_not_verified": listed["not_verified"], "schema_errors_when_forced": schema_errors,
             "pending_points_in_register": pending["data"]["pending_points"]}
    evidence = [f"La etapa 16 lista {facts['records_listed']} registros de norma en los manifiestos y {facts['records_not_verified']} no están verificados; el registro de norma "
                f"de los motores tiene {facts['pending_points_in_register']} puntos pendientes (epc norms-pending).",
                "Pedir approved_for_construction con esos registros levanta ApprovalBlocked" + (" (bloqueo verificado)." if blocked else " (NO se bloqueó)."),
                "Con los mismos registros marcados verificados el pedido se acepta, o sea que el bloqueo depende de los registros y no es general." if accepted else
                "Con registros verificados el pedido tampoco se acepta.",
                f"El esquema también rechaza un manifiesto aprobado con registros sin verificar ({facts['schema_errors_when_forced']} errores de esquema).",
                f"Por el CLI el ingeniero responsable recibe {approve_code} al aprobar y el proyecto no llega a aprobado ni emitido."]
    gaps = []
    if not (blocked and accepted and approve_code == "blocked_d21" and not issue_ok and not reached and schema_errors):
        gaps.append("Alguno de los intentos de aprobar no se bloqueó como se esperaba.")
    return result(7, "fail" if gaps else "pass", evidence, gaps, facts)


# ------------------------------------------------------------------ C8
def load_hook(projects_root):
    spec = importlib.util.spec_from_file_location("guard_paths_dry_run", REPO / "harness" / ".claude" / "hooks" / "guard_paths.py")
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    hook.PROJECTS = Path(projects_root).resolve()
    return hook


def hook_call(hook, project, role, event):
    event = dict(event, cwd=str(project))
    return hook.run(io.StringIO(json.dumps(event)), io.StringIO(), {"EPC_ACTOR_ROLE": role})


def hook_events(project, rel):
    path = str(project / rel)
    edits = [{"tool_name": t, "tool_input": {"file_path": path}} for t in ("Write", "Edit", "MultiEdit")]
    shells = [{"tool_name": "Bash", "tool_input": {"command": c.format(rel)}} for c in ("echo x > {}", "echo x >> {}", "printf x | tee {}", "sed -i s/a/b/ {}", "cp other.json {}",
                                                                                                   "python -c \"open('{}','w').write('x')\"", "rm {}")]
    return edits + shells


def hook_reads(project, rel):
    return [{"tool_name": "Read", "tool_input": {"file_path": str(project / rel)}}, {"tool_name": "Grep", "tool_input": {"path": str(project / rel), "pattern": "x"}},
            {"tool_name": "Bash", "tool_input": {"command": f"cat {rel}"}}]


def hook_matrix(proj, roles, files):
    hook = load_hook(proj.root)
    writes = [(hook_call(hook, proj.project, role, ev) == 2) for role in roles for rel in files for ev in hook_events(proj.project, rel)]
    reads = [(hook_call(hook, proj.project, role, ev) == 0) for role in roles for rel in files for ev in hook_reads(proj.project, rel)]
    opaque = hook_call(hook, proj.project, roles[0], {"tool_name": "Bash", "tool_input": {"command": "python tool.py"}}) == 0
    return writes, reads, opaque, hook.EXEMPT_CLASSES


def permission_matrix(roles):
    classes = ("ssot", "deliverables", "inputs", "audit", "config_normative", "schemas")
    denied = [not M.perm.check(r, a, c, True).allowed for r in roles for a in ("write", "create", "delete") for c in classes]
    allowed_somewhere = sum(1 for r in M.rules.ROLES for c in M.rules.PROJECT_CLASSES if M.perm.check(r, "read", c, True).allowed)
    return denied, allowed_somewhere


def c8(run):
    roles = [a["name"] for a in M.S.read_json(REPO / "harness" / ".claude" / "roster.json")["agents"]]
    files = (".epc/project_profile.json", ".epc/master_project_state.json", ".epc/ssot/stage_01_intake.json", ".epc/ssot/stage_16_package_issue.json", "inputs/intake_answers.json",
             ".epc/audit/events.jsonl", run.primary.manifests()[0].relative_to(run.primary.project).as_posix())
    denied, reads_allowed = permission_matrix(roles)
    writes, reads, opaque, exempt = hook_matrix(run.primary, roles, files)
    settings = (REPO / "harness" / ".claude" / "settings.json").read_text(encoding="utf-8")
    wired = "guard_paths" in settings and "PreToolUse" in settings
    facts = {"roles": len(roles), "matrix_cells": len(denied), "matrix_denied": sum(denied), "hook_write_events": len(writes), "hook_write_blocked": sum(writes),
             "hook_read_events": len(reads), "hook_read_allowed": sum(reads), "role_class_pairs_with_read": reads_allowed}
    evidence = [f"Matriz de permisos: {facts['roles']} roles de agente por escritura, creación y borrado sobre las clases protegidas; {facts['matrix_denied']} de {facts['matrix_cells']} combinaciones se niegan.",
                f"El hook de guardia sobre archivos reales del proyecto bloquea {facts['hook_write_blocked']} de {facts['hook_write_events']} intentos de escritura (herramientas de edición y redirecciones, sed, cp, rm, python -c) "
                f"y deja pasar {facts['hook_read_allowed']} de {facts['hook_read_events']} lecturas.",
                "El hook está conectado en la configuración de Claude (PreToolUse)." if wired else "El hook NO figura en la configuración de Claude."]
    gaps = []
    if not (all(denied) and all(writes) and all(reads) and wired):
        gaps.append("Alguna combinación no se bloqueó, una lectura se bloqueó o el hook no está conectado.")
    notes = ["Nota (no bloquea el criterio): un script opaco (python script.py) no se puede inspeccionar y el hook lo deja pasar; las clases " + ", ".join(exempt) +
             " quedan fuera del hook por diseño." if opaque else "Nota: las clases " + ", ".join(exempt) + " quedan fuera del hook por diseño."]
    return result(8, "fail" if gaps else "pass", evidence, gaps + notes, facts)


# ------------------------------------------------------------------ C9
COST_KEYS = re.compile(r"cost|token|usd|duration|elapsed|wall|latency|budget", re.I)


def recorded_measurements(run):
    """(cost or time related keys found in the project files, schemas and roster; distinct timestamps of the stage entries; keys of a stage entry)."""
    names = set()
    for path in list(files_of(run.primary.project).values()) + sorted((REPO / "harness" / "schemas").glob("*.json")) + [REPO / "harness" / ".claude" / "roster.json"]:
        if path.suffix == ".json":
            names |= {k for k in key_names(json.loads(path.read_text(encoding="utf-8"))) if COST_KEYS.search(k)}
    stages = M.S.read_json(run.primary.project / ".epc" / "master_project_state.json")["stages"]
    stamps = {e[k] for e in stages for k in ("started", "finished")}
    return sorted(names), len(stamps), sorted(stages[0])


def c9(run):
    names, stamps, entry_keys = recorded_measurements(run)
    prd = (REPO / "harness" / "docs" / "prsad" / "PRD.md").read_text(encoding="utf-8")
    targets_open = "cost and time targets" in prd
    events = run.primary.project / ".epc" / "audit" / "events.jsonl"
    record_keys = sorted(json.loads(events.read_text(encoding="utf-8").splitlines()[0]))
    facts = {"cost_or_time_keys_found": len(names), "distinct_stage_timestamps": stamps, "event_record_keys": len(record_keys)}
    evidence = [f"Se buscaron claves de costo, tokens o duración en los archivos del proyecto, los esquemas y el roster: {len(names)} encontradas.",
                f"Existe el registro de eventos con {len(record_keys)} campos por evento y, por etapa, la hora de inicio y fin ({', '.join(entry_keys)}); en la corrida de prueba el reloj "
                f"es inyectado y fijo, por lo que hay {stamps} marca distinta."]
    gaps = ["No se registra el costo ni los tokens por agente ni el tiempo de reloj por etapa o por agente.",
            "El dueño no fijó metas de costo y tiempo (PRD §24, punto cuatro): hoy no hay contra qué comparar."] if targets_open else ["Revisar PRD §24."]
    status = "not_instrumented" if not names else "partial"
    if names:
        gaps.insert(0, f"Claves relacionadas: {', '.join(names)}.")
    return result(9, status, evidence, gaps, facts)


# ------------------------------------------------------------------ C10
def sign_manifest(proj):
    """A synthetic signature on one R0 manifest in the temporary copy (signing is a human act, so the file is written by hand here)."""
    path = next(p for p in proj.manifests() if "calculation_memo" in p.name)
    data = M.S.read_json(path)
    data["signed"] = {"signer": "Synthetic Engineer", "date": "2026-01-01"}
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path, data["signed"]


def change_one_load(proj):
    doc = M.S.read_json(M.S.GOLDEN / "loads.json")
    first = next(x for x in doc["loads"] if x["id"] == "T-01")
    first["power"]["value"] = round(first["power"]["value"] * 1.5, 3)
    target = proj.work / "loads.corrected.json"
    target.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    return target


def stage_outputs(proj):
    return {n: M.S.read_json(p)["outputs"] for n, p in zip(range(1, 17), proj.stage_files())}


def executed_stages(proj, run_id):
    lines = (proj.project / ".epc" / "epc-progress.txt").read_text(encoding="utf-8").splitlines()
    return sorted(int(m.group(1)) for line in lines for m in [re.search(rf"run {run_id} \| stage (\d+) ", line)] if m)


def run_correction(run):
    proj = run.started("correction")
    before, signed_path, signature = stage_outputs(proj), *sign_manifest(proj)
    proj.work.joinpath("c.json").write_text(json.dumps([{"note": "synthetic correction: T-01 power"}]), encoding="utf-8")
    review_code, _ = M.S.envelope(proj.root, "review", M.S.CODE, "--corrections", str(proj.work / "c.json"), *M.S.ENGINEER)
    frozen_before = M.S.read_json(proj.project / ".epc" / "ssot" / "inputs_manifest.json")
    corrected = change_one_load(proj)
    code, env = M.S.envelope(proj.root, "run", M.S.CODE, "--loads", str(corrected), "--engine-inputs", str(proj.engine_inputs_file), "--run-id", "dry-run-2",
                             "--revision", "R1", "--detail", *M.S.ORCHESTRATOR)
    after = stage_outputs(proj)
    old = [M.S.read_json(p) for p in proj.manifests() if "/R0/" in p.as_posix()]
    new = [M.S.read_json(p) for p in proj.manifests() if "/R1/" in p.as_posix()]
    signed_old = M.S.read_json(signed_path)
    return {"review_code": review_code, "run_code": code, "run_ok": env["ok"] and env["data"]["run"]["summary"]["ok"],
            "unfrozen_loads_accepted": env["ok"] and env["data"]["run"]["summary"]["stopped_at"] is None,
            "executed": executed_stages(proj, "dry-run-2"), "changed": sorted(n for n in before if before[n] != after[n]),
            "old": len(old), "old_superseded": sum(1 for m in old if m["superseded_by"]), "new": len(new), "new_supersedes": sum(1 for m in new if m["supersedes"]),
            "signature_moved": signed_old["signed"] is None and signed_old["superseded_signature"] == signature,
            "inputs_manifest_unchanged": frozen_before == M.S.read_json(proj.project / ".epc" / "ssot" / "inputs_manifest.json")}


def c10(run):
    d = run.correction
    executed, changed = d["executed"], d["changed"]
    unchanged_rerun = sorted(set(executed) - set(changed))
    facts = {"stages_total": len(M.pipeline.STAGES), "stages_reexecuted": len(executed), "stages_with_changed_output": len(changed), "stages_reexecuted_unchanged": len(unchanged_rerun),
             "manifests_previous": d["old"], "manifests_superseded": d["old_superseded"], "manifests_new": d["new"], "new_with_supersedes": d["new_supersedes"]}
    evidence = [f"Se corrigió una carga (T-01) en una copia, se registró la corrección con review y se re-ejecutó como revisión R1: se re-ejecutaron {facts['stages_reexecuted']} de "
                f"{facts['stages_total']} etapas; cambió la salida de {facts['stages_with_changed_output']}; {facts['stages_reexecuted_unchanged']} etapas se corrieron sin que su salida cambiara.",
                f"Los manifiestos de R0 quedan marcados como reemplazados: {facts['manifests_superseded']} de {facts['manifests_previous']}; los de R1 citan al anterior: {facts['new_with_supersedes']} de {facts['manifests_new']}.",
                "Una firma sintética puesta en un manifiesto de R0 se movió a superseded_signature y signed quedó vacío." if d["signature_moved"] else
                "La firma sintética de R0 NO se movió a superseded_signature."]
    gaps = []
    if len(executed) == len(M.pipeline.STAGES):
        gaps.append("El pipeline siempre re-ejecuta todas las etapas: no existe selección de etapas afectadas (la API solo admite detenerse tras una etapa), "
                    "como pide el PRD.")
    if d["unfrozen_loads_accepted"] and d["inputs_manifest_unchanged"]:
        gaps.append("La corrección se aplicó pasando otra lista de cargas por el CLI: no existe un mecanismo soportado para corregir una entrada (inputs/ es inmutable), "
                    "y los manifiestos de R1 siguen citando el hash de las cargas originales congeladas.")
    ok = d["run_ok"] and d["signature_moved"] and d["old_superseded"] == d["old"] and d["new_supersedes"] == d["new"]
    if not ok:
        gaps.append("El reemplazo de manifiestos o de la firma no funcionó como se esperaba.")
    status = "fail" if gaps else "pass"
    return result(10, status, evidence, gaps, facts)


# ------------------------------------------------------------------ evaluation and report
CRITERIA = (c1, c2, c3, c4, c5, c6, c7, c8, c9, c10)


def evaluate():
    """The ten criterion results, from a fresh dry run in temporary folders. Raises nothing for a failing criterion: an exception becomes a `fail` result."""
    run = DryRun()
    try:
        return [guarded(number, fn, run) for number, fn in enumerate(CRITERIA, start=1)]
    finally:
        run.close()


def guarded(number, fn, run):
    t0 = time.time()
    try:
        out = fn(run)
    except Exception as exc:  # a bug in a criterion check is itself a finding
        out = result(number, "fail", ["La comprobación de este criterio no pudo ejecutarse."], [f"Error al ejecutar la comprobación: {type(exc).__name__}: {exc}"])
    print(f"C{number}: {out['status']} ({time.time() - t0:.1f} s)", file=sys.stderr)
    return out


HEADER = ["# Simulacro del spike: los diez criterios del PRD §21 sobre el proyecto sintético",
          "",
          "> Archivo GENERADO por `harness/tools/build/spike_dry_run.py` (tarea MIG-44p); no se edita a mano. Es un simulacro sobre datos SINTÉTICOS (el proyecto inventado "
          "`synthetic_lv_small`): NO es el spike del proyecto de 309 kVA. Todas las cifras de este archivo se calculan en cada corrida; ninguna está escrita a mano.",
          "",
          "Estados: `cumple` (demostrado por la corrida sintética y una comprobación automática), `parcial` (demostrado salvo una brecha identificada), "
          "`requiere valores del dueño` (no se puede evaluar sin los valores de referencia y las tolerancias de 309 kVA; solo se revisó que existan las conexiones), "
          "`falla` (un requisito no se cumple), `sin medición` (nada lo mide).",
          ""]


def cell(items):
    return "; ".join(i.replace("|", "/").replace("\n", " ") for i in items) or "ninguna"


def table(results):
    rows = ["| Criterio | Estado | Evidencia | Brecha |", "| --- | --- | --- | --- |"]
    for r in results:
        rows.append(f"| C{r['criterion']}. {r['title']} | {STATUS_ES[r['status']]} | {cell(r['evidence'])} | {cell(r['gaps'])} |")
    return rows


def summary_lines(results):
    counts = {s: sum(1 for r in results if r["status"] == s) for s in STATUSES}
    lines = ["## Resumen", ""]
    lines += [f"- {STATUS_ES[s]}: {counts[s]} de {len(results)}." for s in STATUSES if counts[s]]
    lines += ["", "Los criterios C2 y C4 se comparan en la tarea MIG-44 cuando el dueño entregue los valores de referencia y las tolerancias (tarea MIG-42).", ""]
    return lines


def render(results):
    """The Spanish report text for the results (LF line endings)."""
    return "\n".join(HEADER + summary_lines(results) + ["## Criterios", ""] + table(results) + [""])


def main(argv=None, results=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 when the report on disk differs from a fresh dry run")
    ap.add_argument("--out", default=str(REPORT), help="report path (tests use a temp file)")
    args = ap.parse_args(argv)
    text = render(results if results is not None else evaluate())
    out = Path(args.out)
    if args.check:
        current = out.read_text(encoding="utf-8") if out.is_file() else None
        if current != text:
            print(f"STALE {out}: run `python harness/tools/build/spike_dry_run.py` to regenerate")
            return 1
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
