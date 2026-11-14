"""Stages 1 and 2: they only call the MIG-30a intake and requirements functions. Nothing is calculated."""
from disciplines.electrical_lv.intake.form import IntakeError
from disciplines.electrical_lv.intake.hashing import build_manifest
from disciplines.electrical_lv.intake.loads import LoadListError, check_load_list, read_load_list
from disciplines.electrical_lv.intake.profile import build_profile
from disciplines.electrical_lv.requirements.design_basis import build_design_basis
from disciplines.electrical_lv.requirements.verify_inputs import verify_inputs
from disciplines.electrical_lv.stages.base import Stage, StageInputError
from disciplines.electrical_lv.stages.grouped import GroupedStage


class IntakeStage(Stage):
    """Stage 1: profile from the form answers, manifest of `inputs/`, load list from its file."""

    wired = True

    @staticmethod
    def _load_list(context):
        """Reads the load list from its file, or validates the one handed in memory (for example by `epc run --loads`)."""
        if context.loads is None and context.load_list_path:
            context.loads = read_load_list(context.load_list_path)
        elif context.loads is not None:
            check_load_list(context.loads)

    def execute(self, context):
        try:
            if context.profile is None:
                context.profile = build_profile(context.answers)
            if context.inputs_manifest is None and context.inputs_dir:
                context.inputs_manifest = build_manifest(context.inputs_dir)
            self._load_list(context)
        except (IntakeError, LoadListError) as exc:
            raise StageInputError(exc.errors) from exc
        outputs = {"profile": context.profile, "inputs_manifest": context.inputs_manifest, "loads": context.loads}
        return self.result("ok", outputs={k: v for k, v in outputs.items() if v is not None})


class RequirementsStage(Stage):
    """Slice 2: design basis copied and merged from the profile, criteria, assumptions and requirements."""

    wired = True

    def execute(self, context):
        try:
            basis = build_design_basis(context.profile, context.criteria, context.assumptions, context.requirements)
        except IntakeError as exc:
            raise StageInputError(exc.errors) from exc
        except ValueError as exc:
            raise StageInputError([str(exc)]) from exc
        context.design_basis = basis
        return self.result("ok", outputs={"design_basis": basis})


class InputVerificationStage(Stage):
    """Slice 3: cross-checks of loads, areas and plans (rules IV-01..IV-04). Any finding blocks the run."""

    wired = True

    def execute(self, context):
        findings = verify_inputs(context.loads, context.inputs_manifest, context.pipeline_run_id, context.inputs_dir)
        if findings:
            return self.result("blocked", findings=findings, message=f"{len(findings)} blocking finding(s) in the inputs", reason="findings")
        return self.result("ok", outputs={"verified": True, "manifest_sha256": context.inputs_manifest["manifest_sha256"]})


class RequirementsInputsStage(GroupedStage):
    """Stage 2: the design basis (what is copied and merged from the profile), then the verification of the inputs. Any finding of the verification blocks."""

    slice_classes = {2: RequirementsStage, 3: InputVerificationStage}
