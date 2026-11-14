"""The 12 stages of PRD section 12, as stage objects in fixed order (`STAGES`).

Stage 1 and the verification in stage 2 run the MIG-30a functions. Stages 3, 5-8, 10 and 11 are wired to the engines by MIG-30c (`wired = True`; the
calculation chain runs once per run in `engine_calls.chain`); stages 2, 3 and 6 are grouped stages (`grouped.py`) that run several slices; 12 (package
issue, MIG-32) builds the transmittal manifest; 9 (calc_check, MIG-35a) runs the deterministic checks; 4 (supply transformer, MIG-39a) sizes one transformer
when the `transformer` inputs are given.
"""
from disciplines.electrical_lv.stages.base import PipelineContext, Stage, StageResult
from disciplines.electrical_lv.stages.calc_check_stage import CalcCheckStage
from disciplines.electrical_lv.stages.calc_stages import BoardStructureStage, CableSizingStage, EarthingStage, LoadsDemandStage, SelectivityStage
from disciplines.electrical_lv.stages.early_stages import IntakeStage, RequirementsInputsStage
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
    1: IntakeStage, 2: RequirementsInputsStage, 3: LoadsDemandStage, 4: SupplyTransformerStage, 5: BoardStructureStage, 6: CableSizingStage,
    7: SelectivityStage, 8: EarthingStage, 9: CalcCheckStage, 10: DrawingsStage, 11: DocumentsStage, 12: PackageIssueStage}


def build_stages(table=STAGE_TABLE):
    return tuple(SPECIAL.get(spec.number, EngineStage)(spec) for spec in table)


STAGES = build_stages()

__all__ = ["STAGES", "STAGE_TABLE", "WIRED_STAGES", "EngineStage", "PipelineContext", "Stage", "StageResult", "StageSpec", "build_stages"]
