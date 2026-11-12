"""Stage 13 (calc_check) and the helpers stage 16 shares with it (MIG-35a).

The discipline verifies nothing itself: it hands the JSON form of the stage results collected so far to `epc_calc_check.check_run` and returns what comes
back. Stage 13 runs the recalculation, invariant and format groups on the stages that exist at that point (1-12); the cross-document groups need the
drawings and documents of stages 14-15 and run from stage 16 (`package_stage.py`). The stage reports, it never blocks: a blocking finding is recorded in
the run like any other finding and the run goes on.
"""
import copy
import dataclasses

from disciplines.electrical_lv.stages.base import Stage

STAGE_GROUPS = ("recalc", "invariants", "format")
SEVERITIES = ("blocking", "major", "minor", "note")


def run_dict(context, last_stage):
    """The pipeline result so far in its JSON form: the results of stages 1..`last_stage` (as dicts) under the run id."""
    results = [dataclasses.asdict(context.results[k]) for k in sorted(context.results) if k <= last_stage]
    return {"pipeline_run_id": context.pipeline_run_id, "results": results}


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


def by_severity(findings):
    counts = {s: 0 for s in SEVERITIES}
    for f in findings:
        counts[f["severity"]] += 1
    return counts


class CalcCheckStage(Stage):
    """Stage 13: deterministic checks (recalculation, invariants, format) of stages 4-12."""

    wired = True
    wiring_task = "MIG-35a"

    def execute(self, context):
        import epc_calc_check
        found = epc_calc_check.check_run(run_dict(context, 12), project=engine_inputs_for_check(context), run_id=context.pipeline_run_id, groups=STAGE_GROUPS)
        outputs = {"findings_count": len(found), "by_severity": by_severity(found)}
        calls = [{"engine": "validation/calc_check", "function": "epc_calc_check.check_run", "version": epc_calc_check.__version__}]
        return self.result("ok", outputs=outputs, findings=found, engine_calls=calls,
                           message=f"{len(found)} finding(s): " + ", ".join(f"{n} {s}" for s, n in by_severity(found).items()))
