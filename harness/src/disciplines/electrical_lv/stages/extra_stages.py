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
  raceway_sizing   epc_plan.sizing.size_containers: the smallest tray or conduit that holds the cables of each run of the routed floors, with the sections stage 6 sized
  coordination     epc_plan.footprint and epc_plan.clash: the clashes of the routed floors with the drawings of other disciplines given in `engine_inputs["coordination"]`
  special_locations  epc_aea90364.aea_special_locations for the rooms the building declares as bathrooms (701: induction of a conductor, radius of zone 2) or electric-vehicle charging (722:
                   multiple load, demand factor), with the data the engineer gives for each (`engine_inputs["special_locations"]["locations"]`)
  icc_decay        epc_short_circuit.aea_icc_decay: the peak factor and the peak current of the short circuit at the bars (`peak`: R and X of the loop) and the decay of the short-circuit current of
                   a generator (`generator`: its reactances and time constants), for `engine_inputs["icc_decay"]`
  earthing         epc_grounding.aea_earthing: the resistance of the earth electrodes given in `engine_inputs["earthing"]` (soil resistivity and the geometry of each rod, conductor, plate or mesh), their
                   parallel, and, in a TT scheme with a residual current device, whether it complies with the maximum Ra; the engine formulas are called as they are (D15, D26)
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


class RacewaySizingStage(ExtraStage):
    key, engine = "raceway_sizing", "cad/plan"
    functions = ("epc_plan.sizing.size_containers",)

    def applies(self, context):
        return enabled(context, self.key) and bool(_inputs(context).get("routing"))

    def run(self, context):
        import epc_plan.core as core
        from epc_plan import sizing
        from disciplines.electrical_lv.stages.routing_stage import routed_document
        ch = EC.chain(context)
        line_kinds = core._kinds(core.load_profile("electrica_BT"))[0]
        floors, findings = {}, []
        for floor, design in sorted(_inputs(context)["routing"].items()):
            done = core.process(routed_document(design))
            sections = {tag: ch["calc"]["datos"][c["load"]]["S"] for tag, c in design["circuits"].items()}
            sized = sizing.size_containers(done["schedule"]["containers"], sections, {}, line_kinds, core.PARAMS)
            floors[floor] = sized
            findings += [engine_finding(len(findings) + 1, context.pipeline_run_id, self.spec.slug, f"{floor}/{s['tag']}", "fits_largest_size", False, True) for s in sized if not s["fits"]]
        return {"floors": floors}, findings


class CoordinationStage(ExtraStage):
    key, engine = "coordination", "cad/plan"
    functions = ("epc_plan.footprint.footprints", "epc_plan.clash.detect")

    def applies(self, context):
        return self.section(context) is not None and bool(_inputs(context).get("routing"))

    def run(self, context):
        import epc_plan.core as core
        from epc_plan import clash, footprint
        from disciplines.electrical_lv.stages.routing_stage import routed_document
        given = self.section(context)
        items = []
        for floor, design in sorted(_inputs(context)["routing"].items()):
            items += footprint.footprints(routed_document(design), f"floor-{floor}")
        for other in given.get("documents") or []:
            items += footprint.footprints(other["document"], other["sheet"])
        try:
            found = clash.detect(items, given.get("rules"))
        except core.PlanError as exc:
            raise StageInputError([str(exc)]) from exc
        findings = [engine_finding(n, context.pipeline_run_id, self.spec.slug, c["id"], f"clash_{c['type']}", c["gap_m"], c["clearance_m"]) for n, c in enumerate(found, start=1) if c["severity"] == "error"]
        return {"elements": len(items), "clashes": found}, findings


SPECIAL_REQUIRED = {"bathroom": ("conductor_current_a", "distance_m"), "ev_charging": ("outlets", "points", "circuit_current_a", "max_point_current_a")}


class SpecialLocationsStage(ExtraStage):
    key, engine = "special_locations", "calculation/aea90364"
    functions = ("epc_aea90364.aea_special_locations.induccion_conductor_t", "epc_aea90364.aea_special_locations.induccion_admisible",
                 "epc_aea90364.aea_special_locations.radio_zona2_con_tabique_m", "epc_aea90364.aea_special_locations.load_multiple_complies",
                 "epc_aea90364.aea_special_locations.factor_demand")

    def applies(self, context):
        return self.section(context) is not None

    @staticmethod
    def _missing(location):
        return [k for k in SPECIAL_REQUIRED[location["type"]] if k not in location]

    @staticmethod
    def _bathroom(SL, loc):
        out = {"induction_t": SL.induccion_conductor_t(loc["conductor_current_a"], loc["distance_m"]), "induction_complies": SL.induccion_admisible(loc["conductor_current_a"], loc["distance_m"])}
        if loc.get("partition_width_m") is not None:
            out["zone2_radius_m"] = SL.radio_zona2_con_tabique_m(loc["partition_width_m"])
        return out

    @staticmethod
    def _charging(SL, loc):
        out = {"multiple_load": SL.load_multiple_complies(loc["outlets"], loc["points"], loc["circuit_current_a"], loc["max_point_current_a"])}
        if loc.get("max_demand") is not None and loc.get("installed_load") is not None:
            out["demand_factor"] = SL.factor_demand(loc["max_demand"], loc["installed_load"])
        return out

    def run(self, context):
        from epc_aea90364 import aea_special_locations as SL
        rows, findings = [], []
        for loc in (self.section(context) or {}).get("locations") or []:
            missing = self._missing(loc)
            if missing:
                raise StageInputError([f"`special_locations`: {loc.get('room')} ({loc['type']}) is missing {', '.join(missing)} (no default)"])
            try:
                result = self._bathroom(SL, loc) if loc["type"] == "bathroom" else self._charging(SL, loc)
            except ValueError as exc:
                raise StageInputError([f"`special_locations`: {loc['room']}: {exc}"]) from exc
            rows.append({"room": loc["room"], "name": loc.get("name", ""), "type": loc["type"], **result})
            complies = result.get("induction_complies", (result.get("multiple_load") or {}).get("cumple", True))
            if not complies:
                findings.append(engine_finding(len(findings) + 1, context.pipeline_run_id, self.spec.slug, loc["room"], "special_location_complies", False, True))
        return {"locations": rows}, findings


class IccDecayStage(ExtraStage):
    key, engine = "icc_decay", "calculation/short_circuit"
    functions = ("epc_short_circuit.aea_icc_decay.kappa_exacto", "epc_short_circuit.aea_icc_decay.current_peak_to", "epc_short_circuit.aea_icc_decay.corrientes_generador",
                 "epc_short_circuit.aea_icc_decay.constantes_tiempo", "epc_short_circuit.aea_icc_decay.mu_generador")
    GENERATOR = ("e2", "e1", "e", "x_d2", "x_d1", "x_d", "t2_0", "t1_0", "t_min")

    def applies(self, context):
        return self.section(context) is not None

    @staticmethod
    def _peak(ID, context, loop):
        icc_a = EC.chain(context)["form"]["board"]["icc_ka"] * 1000.0
        kappa = ID.kappa_exacto(loop["r_ohm"], loop["x_ohm"])
        return {"icc_a": icc_a, "kappa": kappa, "peak_a": ID.current_peak_to(kappa, icc_a)}

    def _generator(self, ID, gen):
        missing = [k for k in self.GENERATOR if k not in gen]
        if missing:
            raise StageInputError([f"`icc_decay.generator`: missing {', '.join(missing)} (no default)"])
        x_n = gen.get("x_n", 0.0)
        ik2, ik1, ik = ID.corrientes_generador(gen["e2"], gen["e1"], gen["e"], gen["x_d2"], gen["x_d1"], gen["x_d"], x_n)
        t2_n, t1_n = ID.constantes_tiempo(gen["t2_0"], gen["t1_0"], gen["x_d2"], gen["x_d1"], gen["x_d"], x_n)
        return {"ik2_a": ik2, "ik1_a": ik1, "ik_a": ik, "t2_n_s": t2_n, "t1_n_s": t1_n, "mu": ID.mu_generador(gen["t_min"], t2_n, gen["x_d2"], gen["x_d1"], x_n)}

    def run(self, context):
        from epc_short_circuit import aea_icc_decay as ID
        given, out = self.section(context), {}
        unknown = sorted(set(given) - {"peak", "generator"})
        if unknown:
            raise StageInputError([f"`icc_decay`: unknown input(s) {', '.join(unknown)}"])
        try:
            if given.get("peak"):
                loop = given["peak"]
                if not {"r_ohm", "x_ohm"} <= set(loop):
                    raise StageInputError(["`icc_decay.peak`: needs r_ohm and x_ohm of the short-circuit loop (no default)"])
                out["peak"] = self._peak(ID, context, loop)
            if given.get("generator"):
                out["generator"] = self._generator(ID, given["generator"])
        except (ValueError, ZeroDivisionError) as exc:
            raise StageInputError([f"`icc_decay`: {exc}"]) from exc
        return out, []


class ElectrodeStage(ExtraStage):
    key, engine = "earthing", "calculation/grounding"
    functions = ("epc_grounding.aea_earthing.resistance_rod", "epc_grounding.aea_earthing.resistance_conductor_horizontal", "epc_grounding.aea_earthing.resistencia_placa_circular",
                 "epc_grounding.aea_earthing.resistencia_malla", "epc_grounding.aea_earthing.resistance_parallel", "epc_grounding.aea_earthing.ra_maxima",
                 "epc_grounding.aea_earthing.verifica_ra")
    NEEDS = {"rod": ("length_m", "diameter_m"), "horizontal": ("length_m", "diameter_m", "depth_m"), "plate": ("diameter_m", "depth_m"), "mesh": ("area_m2", "conductor_length_m")}

    def applies(self, context):
        return self.section(context) is not None

    def _one(self, EA, rho, electrode):
        kind = electrode.get("type")
        if kind not in self.NEEDS:
            raise StageInputError([f"`earthing`: electrode type {kind!r} is not one of {', '.join(self.NEEDS)}"])
        missing = [k for k in self.NEEDS[kind] if k not in electrode]
        if missing:
            raise StageInputError([f"`earthing`: a {kind} electrode is missing {', '.join(missing)} (no default)"])
        if kind == "rod":
            return EA.resistance_rod(rho, electrode["length_m"], electrode["diameter_m"], bool(electrode.get("simplified")))
        if kind == "horizontal":
            return EA.resistance_conductor_horizontal(rho, electrode["length_m"], electrode["diameter_m"], electrode["depth_m"], bool(electrode.get("simplified")))
        if kind == "plate":
            return EA.resistencia_placa_circular(rho, electrode["diameter_m"], electrode["depth_m"])
        return EA.resistencia_malla(rho, electrode["area_m2"], electrode["conductor_length_m"], *([electrode["depth_m"]] if "depth_m" in electrode else []))

    @staticmethod
    def _check_ra(EA, context, total):
        """{ra_max, complies} for a TT scheme with a residual current device (the sensitivity of the board criteria); {} otherwise."""
        ch = EC.chain(context)
        i_dn = (ch["memo"]["criteria"] or {}).get("rcd_ma")
        if ch["form"]["board"]["system"] != "TT" or not i_dn:
            return {}
        limit = EA.ra_maxima(i_dn / 1000.0)
        return {"i_dn_a": i_dn / 1000.0, "ra_max": limit, "complies": EA.verifica_ra(total, i_dn / 1000.0)}

    def run(self, context):
        from epc_grounding import aea_earthing as EA
        given = self.section(context)
        rho, electrodes = given.get("soil_resistivity_ohm_m"), given.get("electrodes")
        if rho is None or not electrodes:
            raise StageInputError(["`earthing`: needs soil_resistivity_ohm_m and at least one electrode (no default)"])
        try:
            each = [{"type": e.get("type"), "resistance_ohm": self._one(EA, rho, e)} for e in electrodes]
            total = EA.resistance_parallel([e["resistance_ohm"] for e in each])
            check = self._check_ra(EA, context, total)
        except ValueError as exc:
            raise StageInputError([f"`earthing`: {exc}"]) from exc
        findings = [] if check.get("complies", True) else [engine_finding(1, context.pipeline_run_id, self.spec.slug, "earth electrode", "ra_complies", False, True)]
        return {"electrodes": each, "parallel_ohm": total, **({"ra": check} if check else {})}, findings
