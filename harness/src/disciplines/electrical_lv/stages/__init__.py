"""The 16 stages of PRD section 12, as stage objects in fixed order (`STAGES`).

Stages 1-3 run the MIG-30a functions. Stages 4, 5, 7-12, 14 and 15 are wired to the engines by MIG-30c (`wired = True`; the
calculation chain runs once per run in `engine_calls.chain`); 16 (package issue, MIG-32) builds the deliverable manifests; 13 (calc_check, MIG-35a) runs the deterministic checks; 6 (supply transformer, MIG-39a) sizes one transformer when the `transformer` inputs are given.
"""
from disciplines.electrical_lv.stages.base import PipelineContext, Stage, StageResult
from disciplines.electrical_lv.stages.calc_check_stage import CalcCheckStage
from disciplines.electrical_lv.stages.calc_stages import (
    BoardStructureStage, DemandStage, EarthingStage, FeederSizingStage, LoadScheduleStage, ProtectionStage, ShortCircuitStage,
    VoltageDropStage)
from disciplines.electrical_lv.stages.early_stages import InputVerificationStage, IntakeStage, RequirementsStage
from disciplines.electrical_lv.stages.output_stages import DocumentsStage, DrawingsStage
from disciplines.electrical_lv.stages.package_stage import PackageIssueStage
from disciplines.electrical_lv.stages.supply_stage import SupplyTransformerStage
from disciplines.electrical_lv.stages.table import STAGE_TABLE, WIRED_STAGES, StageSpec


class EngineStage(Stage):
    """A stage whose engine is not wired yet: it returns `not_available` (the wired stages have their own classes)."""

    wired = False
    wiring_task = "MIG-30c"


class NoEngineStage(EngineStage):
    """Planned in the PRD, no engine exists in Phase 1."""

    wiring_task = None


SPECIAL = {
    1: IntakeStage, 2: RequirementsStage, 3: InputVerificationStage, 4: LoadScheduleStage, 5: DemandStage, 6: SupplyTransformerStage,
    7: BoardStructureStage, 8: FeederSizingStage, 9: VoltageDropStage, 10: ShortCircuitStage, 11: ProtectionStage, 12: EarthingStage,
    13: CalcCheckStage, 14: DrawingsStage, 15: DocumentsStage, 16: PackageIssueStage}


def build_stages(table=STAGE_TABLE):
    return tuple(SPECIAL.get(spec.number, EngineStage)(spec) for spec in table)


STAGES = build_stages()

__all__ = ["STAGES", "STAGE_TABLE", "WIRED_STAGES", "EngineStage", "PipelineContext", "Stage", "StageResult", "StageSpec", "build_stages"]
