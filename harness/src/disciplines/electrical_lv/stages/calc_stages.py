"""The calculation stages: slices of the calculation chain (MIG-30c).

`engine_calls.chain` runs the engines once; each stage here selects keys of that raw result (pure selection, no rounding, no
unit change, no arithmetic) and copies them into `outputs`. A verdict flag that the engine returned as False becomes a finding. A grouped stage (`grouped.py`) runs several slices
and keeps one section of outputs per slice.
"""
import copy

from disciplines.electrical_lv.stages import engine_calls as EC
from disciplines.electrical_lv.stages.base import Stage, engine_finding
from disciplines.electrical_lv.stages.grouped import GroupedStage
from disciplines.electrical_lv.stages.extra_stages import BackupStage, HvacStage, LightningStage, MotorsStage, CoordinationStage, PanelThermalStage, PhaseBalanceStage, RacewaySizingStage, ReactiveStage
from disciplines.electrical_lv.stages.lighting_stage import LightingStage
from disciplines.electrical_lv.stages.routing_stage import RoutingStage
from disciplines.electrical_lv.stages.mappings import ENGINE_CHAIN, KIND_SYSTEM, PENDING_ITEMS

CALC = "epc_aea90364.aea_pipeline.calculate"
MEMO = "epc_aea90364.board_memo.build"
FORM = "epc_drawing.board_design.calculate"
GROUPS = "epc_drawing.board_design.groups_in"
BASE = (GROUPS, FORM, CALC)
WITH_MEMO = BASE + (MEMO,)


def _get(obj, path):
    for key in path:
        obj = obj.get(key) if isinstance(obj, dict) else None
    return obj


def _source(ch, kind, tag):
    return {"datos": ch["calc"]["datos"], "detalle": ch["calc"]["detalle"], "memo": ch["memo_by_tag"]}[kind][tag]


def circuit_rows(ch, fields):
    """One row per circuit: {circuit, load_id} plus the engine keys named in `fields` ({output key: (source, path)})."""
    rows = []
    for tag in ch["calc"]["datos"]:
        row = {"circuit": tag, "load_id": ch["tags"].get(tag)}
        row.update({name: copy.deepcopy(_get(_source(ch, src, tag), path)) for name, (src, path) in fields.items()})
        rows.append(row)
    return rows


def false_flags(rows, names):
    """(circuit, flag) of every row whose engine verdict `flag` is False (None = not applicable, not a failure)."""
    return [(r["circuit"], n) for r in rows for n in names if r.get(n) is False]


class ChainStage(Stage):
    """A stage that reads a slice of the engine chain. Subclasses give `calls`, `fields`, `flags` and may override `extra`."""

    wired = True
    wiring_task = "MIG-30c"
    calls = BASE
    fields = {}
    flags = ()
    row_key = "circuits"
    pending_key = None              # the key of PENDING_ITEMS (the number of the slice in the former 16-stage table)

    def extra(self, ch, rows):
        return {}

    def execute(self, context):
        ch = EC.chain(context)
        rows = circuit_rows(ch, self.fields)
        outputs = {self.row_key: rows, **self.extra(ch, rows)}
        if PENDING_ITEMS.get(self.pending_key):
            outputs["pending"] = copy.deepcopy(PENDING_ITEMS[self.pending_key])
        return self.result("ok", outputs=outputs, findings=self.findings(context, rows), engine_calls=EC.calls(ch, *self.calls))

    def findings(self, context, rows):
        pairs = false_flags(rows, self.flags)
        return [engine_finding(n, context.pipeline_run_id, self.spec.slug, c, f, False, True) for n, (c, f) in enumerate(pairs, start=1)]


class LoadScheduleStage(ChainStage):
    pending_key = 4
    fields = {"ib_a": ("detalle", ("ib_a",)), "p_kw": ("detalle", ("p_kw",)), "phases": ("detalle", ("fases",)), "fp": ("detalle", ("fp",)),
              "parent": ("detalle", ("padre",))}


class DemandStage(ChainStage):
    """Demand factors of the engine table for the type of each load (`aea_demand.factor_demanda_sistema`)."""

    def execute(self, context):
        from epc_aea90364 import aea_demand
        ch = EC.chain(context)
        rows = [{"circuit": tag, "load_id": ch["tags"][tag], "kind": kind, "system": KIND_SYSTEM[kind],
                 "demand_factor": aea_demand.factor_demanda_sistema(KIND_SYSTEM[kind])} for tag, kind in ch["kinds"].items()]
        record = EC.record_for(ENGINE_CHAIN, "epc_aea90364.aea_demand.factor_demanda_sistema")
        return self.result("ok", outputs={"circuits": rows, "pending": copy.deepcopy(PENDING_ITEMS[5])}, engine_calls=[record])


class BoardStructureStage(ChainStage):
    calls = WITH_MEMO
    fields = {"type": ("detalle", ("tipo",)), "parent": ("detalle", ("padre",)), "device_kind": ("detalle", ("kind",)),
              "topology": ("detalle", ("topologia",)), "device": ("datos", ("disp",)), "chain": ("detalle", ("cadena",)),
              "solution": ("detalle", ("solucion",))}

    def extra(self, ch, rows):
        groups = {c["tag"]: copy.deepcopy(c["group_of"]) for c in ch["data"]["circuits"] if c.get("group_of")}
        return {"board": copy.deepcopy(ch["memo"]["board"]), "supply": copy.deepcopy(ch["memo"]["acometida"]), "differential_groups_added": groups}

    def execute(self, context):
        from epc_aea90364 import aea_export
        result = super().execute(context)
        check = aea_export.validate_calculation(EC.chain(context)["calc"]["datos"])
        result.outputs["contract_check"] = check
        result.engine_calls.append(EC.record_for(ENGINE_CHAIN, "epc_aea90364.aea_export.validate_calculation"))
        if check["errores"]:
            return self._blocked(context, check["errores"], "ST-07")
        return result


class FeederSizingStage(ChainStage):
    calls = WITH_MEMO
    flags = ("compliant", "overload_ok", "coordination_ok")
    fields = {"in_a": ("datos", ("In",)), "ib_a": ("datos", ("Ib",)), "s_mm2": ("datos", ("S",)), "s_internal_mm2": ("detalle", ("s_termica_mm2",)),
              "iz_a": ("detalle", ("iz_a",)), "min_section_mm2": ("detalle", ("seccion_min_mm2",)), "material": ("detalle", ("material",)),
              "insulation": ("detalle", ("aislacion",)), "method": ("detalle", ("metodo",)), "route": ("detalle", ("ruta",)),
              "route_limiting": ("detalle", ("ruta_limitante",)), "pe_mm2": ("detalle", ("pe_mm2",)), "neutral_mm2": ("detalle", ("neutro_mm2",)),
              "transition": ("memo", ("transicion",)), "i2_a": ("memo", ("proteccion", "i2_a")), "overload_ok": ("memo", ("proteccion", "sobrecarga_ok")),
              "coordination_ok": ("memo", ("proteccion", "coordinacion_ok")), "compliant": ("detalle", ("cumple",))}

    def extra(self, ch, rows):
        return {"engine_warnings": list(ch["calc"]["avisos"])}


class VoltageDropStage(ChainStage):
    fields = {"length_m": ("detalle", ("largo_m",)), "limit_pct": ("detalle", ("limite_pct",)), "own_pct": ("detalle", ("du_propia_pct",)),
              "accumulated_pct": ("detalle", ("du_acum_pct",)), "du_pct": ("datos", ("dU",)), "compliant": ("detalle", ("cumple",))}

    def extra(self, ch, rows):
        return {"limits_pct": copy.deepcopy(ch["calc"]["limites"])}


class ShortCircuitStage(ChainStage):
    calls = WITH_MEMO
    flags = ("breaking_ok", "trip_ok")
    fields = {"icu_ka": ("datos", ("icu",)), "icc_a": ("memo", ("proteccion", "icc_a")), "icc_min_a": ("detalle", ("icc_min_a",)),
              "breaking_ok": ("memo", ("proteccion", "icu_ok")), "trip_ok": ("memo", ("proteccion", "disparo_ok")),
              "k_min": ("memo", ("proteccion", "k_min")), "k_max": ("memo", ("proteccion", "k_max"))}

    def extra(self, ch, rows):
        return {"busbar_icc_ka": ch["form"]["board"]["icc_ka"]}


class ProtectionStage(ChainStage):
    """The protection device chosen for each circuit (slice 11 of the cable sizing stage)."""

    calls = WITH_MEMO
    pending_key = 11
    flags = ("protection_ok",)
    fields = {"device": ("datos", ("disp",)), "device_kind": ("memo", ("proteccion", "kind")), "curve": ("memo", ("proteccion", "curva")),
              "in_a": ("memo", ("proteccion", "In")), "overload_ok": ("memo", ("proteccion", "sobrecarga_ok")),
              "coordination_ok": ("memo", ("proteccion", "coordinacion_ok")), "protection_ok": ("memo", ("proteccion", "cumple"))}


class SelectivityStage(ChainStage):
    """Stage 7: the selectivity and coordination study between each protection and the one upstream (from the protections fixed by stage 6)."""

    calls = WITH_MEMO

    def execute(self, context):
        ch = EC.chain(context)
        pairs = ch["memo"]["selectividad"]
        outputs = {"selectivity": copy.deepcopy(pairs), "selectivity_summary": copy.deepcopy(ch["memo"]["resumen"]["selectividad"])}
        weak = [p for p in pairs if p["resultado"] == "revisar"]
        findings = [engine_finding(i, context.pipeline_run_id, self.spec.slug, p["aguas_abajo"], "selectivity", p["resultado"], "total or parcial")
                    for i, p in enumerate(weak, start=1)]
        return self.result("ok", outputs=outputs, findings=findings, engine_calls=EC.calls(ch, *self.calls))


class EarthingStage(ChainStage):
    calls = WITH_MEMO
    pending_key = 12
    flags = ("differential_ok",)
    fields = {"differential": ("memo", ("diferencial",)), "differential_ok": ("memo", ("diferencial", "cumple"))}

    def extra(self, ch, rows):
        return {"earthing_system": ch["form"]["board"]["system"], "rcd_ma": ch["memo"]["criteria"]["rcd_ma"]}


class LoadsDemandStage(GroupedStage):
    """Stage 3: load schedule and phase balance, then demand and simultaneity, then (only with `engine_inputs["lighting"]`) the lighting of the rooms, then (only with `engine_inputs["routing"]`) the runs and circuits of the floors."""

    slice_classes = {4: LoadScheduleStage, 5: DemandStage, 17: LightingStage, 18: RoutingStage, 24: HvacStage, 25: PhaseBalanceStage}


class CableSizingStage(GroupedStage):
    """Stage 6: the cable and its protection, sized together: section, voltage drop, short-circuit currents and the protection device."""

    slice_classes = {8: FeederSizingStage, 9: VoltageDropStage, 10: ShortCircuitStage, 11: ProtectionStage, 19: MotorsStage, 20: ReactiveStage, 21: PanelThermalStage, 22: BackupStage,
                     23: LightningStage, 26: RacewaySizingStage, 27: CoordinationStage}
