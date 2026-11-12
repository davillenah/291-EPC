"""Stage 6 (supply and transformer sizing, MIG-39a).

The discipline calculates nothing: it passes the `transformer` section of `context.engine_inputs` to `epc_transformer_sizing.size_transformer` and
returns what comes back. The section is `{"demand_kva", "reserve_pct", "secondary_v"}`, all explicit: the board total kVA is an input here (the
engines do not produce it yet) and no reserve criterion has been decided. Without the section the stage is `not_available`; a missing or invalid
value makes it `blocked` with the engine's message. Every assumption of the engine becomes a `note` finding. The outputs are drafts (D21).
"""
from disciplines.electrical_lv.stages import engine_calls as EC
from disciplines.electrical_lv.stages.base import Stage, StageInputError

ENGINE = "calculation/transformer_sizing"
FUNCTION = "epc_transformer_sizing.size_transformer"
KEYS = ("demand_kva", "reserve_pct", "secondary_v")
NOT_PROVIDED = "not available in Phase 1: transformer inputs not provided"


def assumption_finding(n, run_id, slug, text):
    """A note-severity finding that states one assumption of the engine result."""
    return {"id": f"F-{n:04d}", "run_id": run_id, "verifier": "calc-check", "severity": "note", "document": slug, "field": "assumption",
            "value": text, "expected": "reviewed by the engineer of record", "clause": "engine assumption", "action": "Confirm or replace the assumption.",
            "evidence": [f"engine {FUNCTION}"], "status": "open"}


class SupplyTransformerStage(Stage):
    wired = True
    wiring_task = "MIG-39a"

    def execute(self, context):
        section = (context.engine_inputs or {}).get("transformer")
        if section is None:
            return self.result("not_available", message=NOT_PROVIDED, reason="no_transformer_inputs")
        if not isinstance(section, dict):
            raise StageInputError(["transformer: must be an object with demand_kva, reserve_pct and secondary_v"])
        unknown = sorted(set(section) - set(KEYS))
        if unknown:
            raise StageInputError([f"transformer: unknown input(s) {', '.join(unknown)}"])
        import epc_transformer_sizing as TS
        try:
            result = TS.size_transformer(section.get("demand_kva"), section.get("secondary_v"), section.get("reserve_pct"))
        except ValueError as exc:
            raise StageInputError([str(exc)]) from exc
        findings = [assumption_finding(n, context.pipeline_run_id, self.spec.slug, a) for n, a in enumerate(result["assumptions"], start=1)]
        outputs = {**result, "inputs": {k: section.get(k) for k in KEYS}}
        return self.result("ok", outputs=outputs, findings=findings, engine_calls=[EC.record_for(ENGINE, FUNCTION)],
                           message=f"transformer {result['rating_kva']:g} kVA (draft)")
