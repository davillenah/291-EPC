"""Stage 9 (calc_check) and the helpers stage 12 shares with it (MIG-35a).

The discipline verifies nothing itself: it hands the JSON form of the stage results collected so far to `epc_calc_check.check_run` and returns what comes
back. Stage 9 runs the recalculation, invariant and format groups on the stages that exist at that point (1-8); the cross-document groups need the
drawings and documents of stages 10-11 and run from stage 12 (`package_stage.py`). The stage reports, it never blocks: a blocking finding is recorded in
the run like any other finding and the run goes on.
"""
import copy
import dataclasses

from disciplines.electrical_lv.stages.base import Stage
from disciplines.electrical_lv.stages.table import SLICES

STAGE_GROUPS = ("recalc", "invariants", "format")
SEVERITIES = ("blocking", "major", "minor", "note")


# The stage results of the 12-stage pipeline in the vocabulary of `epc_calc_check` (the 16 slices it was written for): physical stage -> slice numbers.
SLICES_OF = {1: (1,), 2: (2, 3), 3: (4, 5), 4: (6,), 5: (7,), 6: (8, 9, 10, 11), 8: (12,), 9: (13,), 10: (14,), 11: (15,), 12: (16,)}
SELECTIVITY = 7                     # its outputs and findings join the protection slice (11)


def _slice(res, number, outputs, findings):
    entry = dict(res, stage=number, outputs=outputs, findings=findings)
    entry.pop("slug", None)
    return entry


def _slices_of_result(res, numbers):
    """{slice number: result} of one physical stage result: one slice as it is, or a grouped stage split into its slices."""
    if len(numbers) == 1:
        return {numbers[0]: _slice(res, numbers[0], res["outputs"], res["findings"])}
    slugs = {slug for slug, group in SLICES.values() if group == res["stage"]}       # includes the slices calc_check does not see
    return {n: _grouped_slice(res, n, n == numbers[0], slugs) for n in numbers}


def _grouped_slice(res, n, first, slugs):
    """Slice `n` of a grouped stage: its own output and the findings that name it (the first slice also takes those that name no slice)."""
    slug = SLICES[n][0]
    outputs = res["outputs"].get(slug) if res["status"] == "ok" else None
    mine = [f for f in res["findings"] if f.get("document") == slug or (first and f.get("document") not in slugs)]
    return _slice(res, n, outputs or {}, mine)


def _join_selectivity(first, res):
    """Slice 11 (`first`) with the findings and the outputs of the selectivity stage `res` joined to it."""
    joined = dict(first, findings=first["findings"] + res["findings"])
    if res["status"] == "ok" and first["status"] == "ok":
        joined["outputs"] = dict(first["outputs"], **res["outputs"])
    elif res["status"] != "ok":
        joined["status"] = res["status"]
    return joined


def logical_results(results):
    """[dict] of the 16 slice results of a run, from the (physical) stage results as dicts: a grouped stage becomes one result per slice, the outputs of
    the selectivity stage join slice 11. A stage that did not finish ok gives each of its slices its status and no outputs."""
    out = {}
    for res in results:
        if res["stage"] in SLICES_OF:
            out.update(_slices_of_result(res, SLICES_OF[res["stage"]]))
    for res in results:
        if res["stage"] == SELECTIVITY and 11 in out:
            out[11] = _join_selectivity(out[11], res)
    return [out[n] for n in sorted(out)]


def run_dict(context, last_stage):
    """The pipeline result so far in the vocabulary of `epc_calc_check`: the slices of stages 1..`last_stage` under the run id."""
    results = [dataclasses.asdict(context.results[k]) for k in sorted(context.results) if k <= last_stage]
    return {"pipeline_run_id": context.pipeline_run_id, "results": logical_results(results)}


def engine_inputs_for_check(context):
    """What `epc_calc_check` needs to recompute: the installation inputs of every circuit exactly as the calculation chain used them (selection, no arithmetic).

    None when the calculation chain did not run in this context (the checks then report the recalculation as not recomputable)."""
    chain = context.engine_cache.get("chain")
    if chain is None:
        return None
    rows = {c["tag"]: c for c in chain["data"]["circuits"]}
    circuits = {}
    for tag, detail in chain["calc"]["detalle"].items():
        inst, row = detail["instalacion"], rows.get(tag, {})
        entry = {"TEMP_AMBIENTE_C": inst["t_amb"], "TEMP_SUELO_C": inst["t_suelo"], "RESIST_TERMICA_KMW": inst["rho"]}
        if row.get("grouped") not in (None, ""):
            entry["AGRUP_CIRCUITOS"] = row["grouped"]
        if row.get("moments"):
            entry["MOMENTOS"] = row["moments"]
        circuits[tag] = entry
    return {"circuits": circuits, "voltage_v": copy.deepcopy(chain["form"]["board"]["voltage_v"])}


def diagram_findings(context, first_number):
    """Advisory notes (severity `note`) where a protective device of the calculation differs from the one the diagram rules select for its current
    (`epc_drawing.diagram_knowledge`, criteria of `knowledge/diagrams`). No result changes; a person reviews them. [] when the chain did not run."""
    chain = context.engine_cache.get("chain")
    if chain is None:
        return []
    from epc_drawing import diagram_knowledge
    board = {tag: d["proteccion"] for tag, d in chain["calc"]["detalle"].items() if d.get("proteccion")}
    return [{"id": f"F-{first_number + i:04d}", "run_id": context.pipeline_run_id, "verifier": "calc-check", "severity": "note", "document": "protection",
             "field": f"{n['circuit']}/device_per_rules", "value": n["drawn"], "expected": "/".join(n["suggested"]), "clause": f"diagram rule {n['rule']} ({n['status']})",
             "action": n["en"] + " | " + n["es"], "evidence": [f"decision rule {n['rule']} of knowledge/diagrams, status {n['status']}"], "status": "open"}
            for i, n in enumerate(diagram_knowledge.check_board(board))]


def by_severity(findings):
    counts = {s: 0 for s in SEVERITIES}
    for f in findings:
        counts[f["severity"]] += 1
    return counts


def run_totals(context, number, found):
    """Findings of the stages before this one plus this stage's own: what the manifest will carry (B-03)."""
    every = [f for k in sorted(context.results) if k < number for f in context.results[k].findings] + list(found)
    return {"count": len(every), "by_severity": by_severity(every)}


def _counts(by):
    return ", ".join(f"{n} {s}" for s, n in by.items())


def summary_message(found, total):
    return f"{len(found)} finding(s): {_counts(by_severity(found))}; whole run: {total['count']} finding(s): {_counts(total['by_severity'])}"


class CalcCheckStage(Stage):
    """Stage 9: deterministic checks (recalculation, invariants, format) of stages 3-8."""

    wired = True
    wiring_task = "MIG-35a"

    def execute(self, context):
        import epc_calc_check
        found = epc_calc_check.check_run(run_dict(context, 8), project=engine_inputs_for_check(context), run_id=context.pipeline_run_id, groups=STAGE_GROUPS)
        found = list(found) + diagram_findings(context, len(found) + 1)
        outputs = {"findings_count": len(found), "by_severity": by_severity(found)}
        calls = [{"engine": "validation/calc_check", "function": "epc_calc_check.check_run", "version": epc_calc_check.__version__}]
        outputs["run_findings"] = run_totals(context, self.spec.number, found)
        return self.result("ok", outputs=outputs, findings=found, engine_calls=calls, message=summary_message(found, outputs["run_findings"]))
