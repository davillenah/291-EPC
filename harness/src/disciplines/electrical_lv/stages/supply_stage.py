"""Stage 6 (supply and transformer sizing, MIG-39a).

The discipline calculates nothing: it passes the `transformer` section of `context.engine_inputs` to `epc_transformer_sizing.size_transformer` and
returns what comes back. The section is `{"demand_kva", "reserve_pct", "secondary_v"}`, all explicit: no reserve criterion has been decided. The demand is either given
(`demand_kva`) or asked from the board (`"demand": "board"`): then it is the apparent power (`epc_transformer_sizing.apparent_power_kva`) of the head current of the board that the calculation
engine gives with the simultaneity of the project criteria (`board_feeders.head`), at the voltage of the board. Without the section the stage is `not_available`; a missing or invalid
value makes it `blocked` with the engine's message. Every assumption of the engine becomes a `note` finding. The outputs are drafts (D21).
"""
from disciplines.electrical_lv.stages import engine_calls as EC
from disciplines.electrical_lv.stages.base import Stage, StageInputError

ENGINE = "calculation/transformer_sizing"
ENGINE_CHAIN = "calculation/aea90364"
FUNCTION = "epc_transformer_sizing.size_transformer"
KEYS = ("demand_kva", "demand", "reserve_pct", "secondary_v")
NOT_PROVIDED = "no transformer to size: no `transformer` inputs were given (the installation is taken from the low-voltage network as the supply data say)"


def assumption_finding(n, run_id, slug, text):
    """A note-severity finding that states one assumption of the engine result."""
    return {"id": f"F-{n:04d}", "run_id": run_id, "verifier": "calc-check", "severity": "note", "document": slug, "field": "assumption",
            "value": text, "expected": "reviewed by the engineer of record", "clause": "engine assumption", "action": "Confirm or replace the assumption.",
            "evidence": [f"engine {FUNCTION}"], "status": "open"}


class SupplyTransformerStage(Stage):
    wired = True
    wiring_task = "MIG-39a"

    @staticmethod
    def _demand(context, section, TS):
        """(demand kVA, extra engine calls, extra assumptions): the given `demand_kva`, or the one of the head current of the board when the section says `"demand": "board"`."""
        if section.get("demand") is None:
            return section.get("demand_kva"), [], []
        if section["demand"] != "board" or section.get("demand_kva") is not None:
            raise ValueError("transformer: give `demand_kva` or `\"demand\": \"board\"`, not both, and no other value of `demand`")
        from epc_aea90364 import board_feeders
        ch = EC.chain(context)
        amps, record = board_feeders.head(ch["calc"]["datos"], ch["calc"]["detalle"], ch["criteria"])
        kva = TS.apparent_power_kva(amps, ch["form"]["board"]["voltage_v"])
        note = f"demand of the board: head current {amps} A (sum of the circuits that hang from the board, simultaneity {'of the criteria' if record else 'none'}) as three-phase apparent power"
        return kva, [EC.record_for(ENGINE_CHAIN, "epc_aea90364.board_feeders.head"), EC.record_for(ENGINE, "epc_transformer_sizing.apparent_power_kva")], [note]

    @staticmethod
    def _section(context):
        """The `transformer` section, checked: None when it was not given."""
        section = (context.engine_inputs or {}).get("transformer")
        if section is None:
            return None
        if not isinstance(section, dict):
            raise StageInputError(["transformer: must be an object with demand_kva, reserve_pct and secondary_v"])
        unknown = sorted(set(section) - set(KEYS))
        if unknown:
            raise StageInputError([f"transformer: unknown input(s) {', '.join(unknown)}"])
        return section

    def execute(self, context):
        section = self._section(context)
        if section is None:
            return self.result("not_available", message=NOT_PROVIDED, reason="no_transformer_inputs")
        import epc_transformer_sizing as TS
        try:
            demand, calls, extra = self._demand(context, section, TS)
            result = TS.size_transformer(demand, section.get("secondary_v"), section.get("reserve_pct"))
        except ValueError as exc:
            raise StageInputError([str(exc)]) from exc
        findings = [assumption_finding(n, context.pipeline_run_id, self.spec.slug, a) for n, a in enumerate(result["assumptions"] + extra, start=1)]
        outputs = {**result, "inputs": {k: section.get(k) for k in KEYS if k != "demand" or k in section}}
        return self.result("ok", outputs=outputs, findings=findings, engine_calls=[EC.record_for(ENGINE, FUNCTION)] + calls,
                           message=f"transformer {result['rating_kva']:g} kVA (draft)")
