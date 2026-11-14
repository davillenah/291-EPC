"""Grouped stages: one stage of the table that runs several slices (the former stages of the 16-stage table) and returns one result.

The outputs of a grouped stage hold one section per slice, named by the slice slug; each section is exactly what the slice returned, so the
consumers that read a slice (`epc_calc_check`, the documents) keep their vocabulary. The slices run in order and the first one that does not finish
`ok` ends the stage with its status, its findings and its message (the message names the slice). A slice marked `optional` that is `not_available` (its inputs were not given) is skipped: it leaves no section and does not end the stage. The findings, the engine calls and the messages of the
slices that did run are kept.
"""
from disciplines.electrical_lv.stages.base import Stage, StageResult
from disciplines.electrical_lv.stages.table import SLICES, slice_spec


class GroupedStage(Stage):
    """Subclasses give `slice_classes`: the slice classes in run order; each slice is built with the spec of its own number and slug."""

    wired = True
    slice_classes = {}                # {slice number: Stage subclass}

    def slices(self):
        return [(number, cls(slice_spec(number))) for number, cls in self.slice_classes.items()]

    def execute(self, context):
        sections, findings, calls, notes = {}, [], [], []
        for number, part in self.slices():
            res = part._guarded(context)
            if res.status == "not_available" and getattr(part, "optional", False):
                continue                  # an optional slice without its inputs is left out: no section, no status
            findings += res.findings
            calls += res.engine_calls
            slug = SLICES[number][0]
            if res.status != "ok":
                text = f"{slug}: {res.message}" if res.message else slug
                return StageResult(self.number, res.status, findings=findings, engine_calls=calls, message=text, reason=res.reason)
            sections[slug] = res.outputs
            if res.message:
                notes.append(f"{slug}: {res.message}")
        return self.result("ok", outputs=sections, findings=findings, engine_calls=calls, message="; ".join(notes))
