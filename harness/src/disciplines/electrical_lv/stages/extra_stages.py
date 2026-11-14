"""Slices of the calculation stages that call engine functions the pipeline did not call before: motor start and protection, reactive compensation, board thermal balance, back-up
(generator, UPS), lightning protection and the thermal load of the air conditioning.

The discipline calculates nothing: each slice builds the input of an engine function from the results of the run (or from the section of `engine_inputs` it names) and copies what comes back.
A datum the run does not have is never invented: a slice with an input that must come from the engineer (back-up loads, structure of the lightning study, thermal design conditions) runs only when
its section is given. The slices that need no extra input (motors, reactive, board thermal) run when the run is a building run (stage 3 routed the floors) or when `engine_inputs["studies"]`
lists them, so the runs of the golden projects keep their results.

  motors           caida_arranque and proteccion_motor of epc_aea90364.aea_motor for every motor circuit sized by stage 6
  reactive         balance, reactiva_a_compensar and banco of epc_aea90364.aea_reactive over the loads of stage 3 (`engine_inputs["reactive"]["target_fp"]` or the engine's own default, said as a note)
  panel_thermal    the power dissipated by the protections of the board (epc_aea90364.aea_panel_thermal); verified against `engine_inputs["panel_thermal"]["p_admissible_w"]` only when given
  backup           grupo, ups and transferencia of epc_aea90364.aea_backup for the loads named in `engine_inputs["backup"]`
  lightning        evaluar of epc_aea90364.aea_lightning for the structure given in `engine_inputs["lightning"]`
  hvac             epc_hvac.run for the `engine_inputs["hvac"]` document (design conditions and spaces)
  phase_balance    epc_load_balance.phase_balance: the phase of each single-phase circuit (`phase_assigned` of `engine_inputs["circuits"]` is kept) and the unbalance between R, S and T

The values the engines use from their norm records are pending review (D21): every slice says so with a note finding.
"""
import copy

from disciplines.electrical_lv.stages import engine_calls as EC
from disciplines.electrical_lv.stages.base import Stage, StageInputError, engine_finding

NOTE = "typical values of the engine, pending review by the owner (D21)"
STUDIES = "studies"


def _inputs(context):
    return EC.inputs_of(context)


def enabled(context, name):
    """True when the slice has to run without a section of its own: a building run (the floors were routed: `engine_inputs["routing"]`) or the study listed in `engine_inputs["studies"]`."""
    return bool(_inputs(context).get("routing")) or name in (_inputs(context).get(STUDIES) or [])


def note(n, run_id, slug, text):
    return {"id": f"F-{n:04d}", "run_id": run_id, "verifier": "calc-check", "severity": "note", "document": slug, "field": "assumption", "value": text,
            "expected": "reviewed by the engineer of record", "clause": "engine record pending review", "action": "Confirm the values with the owner before issuing.",
            "evidence": ["norm records not verified"], "status": "open"}


class ExtraStage(Stage):
    """A slice that calls one engine function family. Subclasses give `engine`, `functions`, `key` and `run(context)` (returns (outputs, findings))."""

    wired = True
    wiring_task = "MIG-42"
    optional = True
    engine = ""
    functions = ()
    key = ""

    def calls(self):
        return [EC.record_for(self.engine, fn) for fn in self.functions]

    def section(self, context):
        given = _inputs(context).get(self.key)
        if given is not None and not isinstance(given, dict):
            raise StageInputError([f"`{self.key}` must be an object"])
        return given

    def applies(self, context):
        """Whether the slice runs in this run (its section is given, or it needs none and the run asks for it)."""
        return self.section(context) is not None or enabled(context, self.key)

    def execute(self, context):
        if not self.applies(context):
            return self.result("not_available", message=f"{self.key} inputs not provided", reason=f"no_{self.key}_inputs")
        outputs, findings = self.run(context)
        findings = findings + [note(len(findings) + 1, context.pipeline_run_id, self.spec.slug, NOTE)]
        return self.result("ok", outputs=outputs, findings=findings, engine_calls=self.calls())


class MotorsStage(ExtraStage):
    key, engine = "motors", "calculation/aea90364"
    functions = ("epc_aea90364.aea_motor.caida_arranque", "epc_aea90364.aea_motor.proteccion_motor")

    def applies(self, context):
        return enabled(context, self.key)

    def run(self, context):
        from epc_aea90364 import aea_motor
        from epc_aea90364.topology import MOTOR_TOPOLOGIES
        ch = EC.chain(context)
        un_v = ch["form"]["board"]["voltage_v"]
        rows, findings = [], []
        for tag, detail in ch["calc"]["detalle"].items():
            topology = detail.get("topologia")
            if topology not in MOTOR_TOPOLOGIES:
                continue
            i_n, section = detail["ib_a"], ch["calc"]["datos"][tag]["S"]
            start = aea_motor.caida_arranque(i_n, topology, detail["largo_m"], section, detail.get("material") or "cu", detail["fases"], un_v)
            rows.append({"circuit": tag, "topology": topology, "start": start, "protection": aea_motor.proteccion_motor(i_n, topology)})
            if start["cumple"] is False:
                findings.append(engine_finding(len(findings) + 1, context.pipeline_run_id, self.spec.slug, tag, "start_voltage_drop_complies", False, True))
        return {"motors": rows}, findings


class ReactiveStage(ExtraStage):
    key, engine = "reactive", "calculation/aea90364"
    functions = ("epc_aea90364.aea_reactive.balance", "epc_aea90364.aea_reactive.reactiva_a_compensar", "epc_aea90364.aea_reactive.banco")

    def run(self, context):
        from epc_aea90364 import aea_reactive
        schedule = context.results[3].outputs["load_schedule"]["circuits"]
        loads = [(c["p_kw"], c["fp"]) for c in schedule if not c["parent"]]
        total = aea_reactive.balance(loads)
        given = (self.section(context) or {}).get("target_fp")
        target = given if given is not None else aea_reactive.fp_objetivo_defecto()
        needed = aea_reactive.reactiva_a_compensar(total["p_kw"], total["fp"], target)
        u_v = EC.chain(context)["form"]["board"]["voltage_v"]
        outputs = {"balance": total, "target_fp": target, "target_origin": "engine_inputs" if given is not None else "engine default (pending review)", "q_to_compensate_kvar": needed,
                   "bank": aea_reactive.banco(needed, u_v)}
        return outputs, []


class PanelThermalStage(ExtraStage):
    key, engine = "panel_thermal", "calculation/aea90364"
    functions = ("epc_aea90364.aea_panel_thermal.potencia_disipada_aparato_w", "epc_aea90364.aea_panel_thermal.potencia_tablero_w", "epc_aea90364.aea_panel_thermal.verify_panel")

    def applies(self, context):
        return self.section(context) is not None or enabled(context, self.key)

    def run(self, context):
        from epc_aea90364 import aea_panel_thermal as PT
        ch = EC.chain(context)
        rows = []
        for tag, detail in ch["calc"]["detalle"].items():
            head = (detail.get("cadena") or [{}])[0]
            if head.get("poles") and detail.get("in_a"):
                rows.append({"circuit": tag, "in_a": detail["in_a"], "poles": head["poles"], "dissipated_w": PT.potencia_disipada_aparato_w(detail["in_a"], head["poles"])})
        total = PT.potencia_tablero_w(sum(r["dissipated_w"] for r in rows))
        outputs = {"devices": rows, "p_total_w": total}
        allowed = (self.section(context) or {}).get("p_admissible_w")
        findings = []
        if allowed is not None:
            outputs["p_admissible_w"], outputs["complies"] = allowed, PT.verify_panel(total, allowed)
            if not outputs["complies"]:
                findings.append(engine_finding(1, context.pipeline_run_id, self.spec.slug, ch["form"]["board"]["name"], "panel_thermal_complies", False, True))
        return outputs, findings


class BackupStage(ExtraStage):
    key, engine = "backup", "calculation/aea90364"
    functions = ("epc_aea90364.aea_backup.grupo", "epc_aea90364.aea_backup.ups", "epc_aea90364.aea_backup.transferencia")

    def section(self, context):
        given = super().section(context)
        unknown = sorted(set(given or {}) - {"genset", "ups"})
        if unknown:
            raise StageInputError([f"unknown input(s) {', '.join(unknown)}"])
        return given

    def applies(self, context):
        return self.section(context) is not None

    @staticmethod
    def _loads(context, ids):
        by_id = {c["load_id"]: c for c in context.results[3].outputs["load_schedule"]["circuits"]}
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise StageInputError([f"`backup`: load(s) {', '.join(missing)} are not in the load list"])
        return [by_id[i] for i in ids]

    def run(self, context):
        from epc_aea90364 import aea_backup
        given, ch, outputs = self.section(context), EC.chain(context), {}
        u_v = ch["form"]["board"]["voltage_v"]
        if given.get("genset"):
            rows = self._loads(context, given["genset"]["loads"])
            kva = [(r["circuit"], r["p_kw"] / r["fp"], ch["calc"]["detalle"][r["circuit"]].get("topologia") or "single") for r in rows]
            outputs["genset"] = aea_backup.grupo(kva, u_v)
            outputs["transfer_switch_a"] = aea_backup.transferencia(outputs["genset"]["corriente_a"])
        if given.get("ups"):
            spec = given["ups"]
            rows = self._loads(context, spec["loads"])
            outputs["ups"] = aea_backup.ups(sum(r["p_kw"] / r["fp"] for r in rows), sum(r["p_kw"] for r in rows), spec["autonomy_min"])
        return outputs, []


class LightningStage(ExtraStage):
    key, engine = "lightning", "calculation/aea90364"
    functions = ("epc_aea90364.aea_lightning.evaluar",)
    FIELDS = ("length_m", "width_m", "height_m", "ng", "environment", "structure", "content", "occupancy", "consequences")

    def applies(self, context):
        return self.section(context) is not None

    def run(self, context):
        from epc_aea90364 import aea_lightning
        given = self.section(context)
        missing = [k for k in self.FIELDS if k not in given]
        if missing:
            raise StageInputError([f"`lightning`: missing {', '.join(missing)} (no default)"])
        return {"structure": aea_lightning.evaluar(*(given[k] for k in self.FIELDS))}, []


class HvacStage(ExtraStage):
    key, engine = "hvac", "calculation/hvac"
    functions = ("epc_hvac.run",)

    def applies(self, context):
        return self.section(context) is not None

    def run(self, context):
        import epc_hvac
        given = self.section(context)
        try:
            result = epc_hvac.run(copy.deepcopy(given)).as_dict()
        except epc_hvac.HvacError as exc:
            raise StageInputError([str(exc)]) from exc
        return {"hvac": result}, []


class PhaseBalanceStage(ExtraStage):
    key, engine = "phase_balance", "calculation/load_balance"
    functions = ("epc_load_balance.phase_balance.balance",)

    def applies(self, context):
        return enabled(context, self.key)

    def run(self, context):
        from epc_load_balance import phase_balance
        ch = EC.chain(context)
        u_v = ch["form"]["board"]["voltage_v"]
        assigned = {tag: (spec or {}).get("phase_assigned", "") for tag, spec in (_inputs(context).get("circuits") or {}).items()}
        rows = []
        for tag, detail in ch["calc"]["detalle"].items():
            kva = phase_balance.apparent_kva(detail["ib_a"], u_v, detail["fases"])
            if not detail.get("padre") and kva:
                rows.append((tag, kva, detail["fases"], assigned.get(ch["tags"].get(tag, tag), "")))
        result = phase_balance.balance(rows)
        findings = [] if result["complies"] else [engine_finding(1, context.pipeline_run_id, self.spec.slug, ch["form"]["board"]["name"], "phase_unbalance_complies", False, True)]
        return {"phases": ["R", "S", "T"], **result}, findings
