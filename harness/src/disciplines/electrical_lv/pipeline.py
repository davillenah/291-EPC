"""The electrical_lv pipeline: the 16 stages of PRD section 12 run in fixed order over an in-memory context.

The discipline calculates and draws nothing (PRD principle 3). Same inputs and same injected run id give the same
result; timestamps come only from an injected `clock` (a callable returning an ISO string).

Without a `store` in the context nothing is written (everything stays in memory). With a `ProjectStore` (MIG-31) `run()` opens
the only write session of the store and records the run in the project folder: see `recorder.py`.
"""
import contextlib
import copy
import uuid
from dataclasses import asdict, dataclass, field

from disciplines.electrical_lv.recorder import RunRecorder
from disciplines.electrical_lv.stages import STAGE_TABLE, STAGES, PipelineContext, StageResult

STOP_STATUSES = ("failed", "blocked")
DRAWINGS = 14          # the stage that writes files (drawings/) under the run folder


class ResumeError(ValueError):
    """The stages before `from_stage` cannot be reused; the message says why. Nothing was written."""

__all__ = ["STAGES", "STAGE_TABLE", "PipelineContext", "ResumeError", "RunResult", "StageResult", "run"]


@dataclass
class RunResult:
    pipeline_run_id: str
    results: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    started_at: str = None
    finished_at: str = None

    def to_dict(self):
        return asdict(self)


def _renumber(results):
    """Copies of the results with finding ids unique across the run (F-0001, F-0002, ...)."""
    out, n = [], 0
    for res in results:
        res = copy.deepcopy(res)
        for finding in res.findings:
            n += 1
            finding["id"] = f"F-{n:04d}"
        out.append(res)
    return out


def _summary(results, stopped_at, stop_after, reused=()):
    """`reused`: the numbers of the stages taken from an earlier run."""
    by_status = {}
    for res in results:
        by_status[res.status] = by_status.get(res.status, 0) + 1
    return {
        "stages_run": len(results),
        "by_status": dict(sorted(by_status.items())),
        "ok": not any(r.status in STOP_STATUSES for r in results),
        "stopped_at": stopped_at,
        "stop_after": stop_after,
        "reused": list(reused),
        "not_available": [r.stage for r in results if r.status == "not_available"],
        "findings": sum(len(r.findings) for r in results),
    }


def _recorded(store, stage):
    """The StageResult recorded in `ssot/` for a stage, or a ResumeError."""
    name = f"stage_{stage.number:02d}_{stage.spec.slug}.json"
    try:
        data = store.read_ssot(name)
    except Exception as exc:
        raise ResumeError(f"stage {stage.number} has no recorded result ({exc}): run the pipeline from the start") from exc
    res = StageResult(**data)
    if res.status != "ok":
        raise ResumeError(f"stage {stage.number} was recorded as {res.status}: only stages that finished ok can be reused")
    return res


def _engine_changed(call):
    """True when the engine that produced a recorded call reports another version now."""
    from disciplines.electrical_lv.stages.engine_calls import record_for
    return record_for(call["engine"], call["function"])["version"] != call.get("version")


def _check_reusable(context, reused):
    """Reuse is safe only while the frozen inputs, the load list and every engine version are the ones that produced the recorded stages."""
    store = context.store
    if not store.is_frozen() or store.verify_inputs_unchanged(context.pipeline_run_id):
        raise ResumeError("the inputs changed since intake: stages cannot be reused, run the pipeline from the start")
    stale = sorted({call["engine"] for res in reused for call in res.engine_calls if _engine_changed(call)})
    if stale:
        raise ResumeError(f"engine version changed since the recorded run ({', '.join(stale)}): run the pipeline from the start")


def _replay(context, stages, reused):
    """Run stages 1 and 2 again in memory (they only copy and merge, in 0.03 s, and write nothing) so the context holds exactly what a full run
    leaves in it, in the same order; their output must equal the recorded one, which proves the reused part still describes these inputs."""
    context.inputs_dir = str(context.store.inputs_dir)
    for stage, recorded in zip(stages[:2], reused):
        again = stage.run(context)
        if again.status != "ok" or again.outputs != recorded.outputs:
            raise ResumeError(f"stage {stage.number} gives another result now than the recorded one: run the pipeline from the start")
        context.results[stage.number] = again


def _restore(context, stages, reused):
    """Give the context what the reused stages left in it (profile, manifest, load list, design basis) and their results."""
    _replay(context, stages, reused)
    for res in reused:
        context.results[res.stage] = res
    if context.work_dir is None and len(reused) >= DRAWINGS:                    # the drawings of the reused stage 14 live in the run folder that made them
        context.work_dir = context.store.run_dir_of_stage(DRAWINGS)


def _reuse(context, stages, from_stage):
    """The recorded results of the stages before `from_stage`, checked and restored into the context."""
    if context.store is None:
        raise ResumeError("resuming needs a project store: the recorded stages live in the project folder")
    if not isinstance(from_stage, int) or isinstance(from_stage, bool) or not 2 <= from_stage <= len(stages):
        raise ResumeError(f"from_stage must be a stage number 2..{len(stages)}, got {from_stage!r}")
    reused = [_recorded(context.store, stage) for stage in stages[:from_stage - 1]]
    _check_reusable(context, reused)
    _restore(context, stages, reused)
    return reused


def _check_stop_after(stop_after, stages):
    if stop_after is not None and stop_after not in [s.number for s in stages]:
        raise ValueError(f"stop_after must be a stage number 1..{len(stages)}, got {stop_after!r}")


@contextlib.contextmanager
def _recording(context, clock):
    """The run recorder when the context has a store (it holds the store's write token), otherwise None."""
    store = getattr(context, "store", None)
    if store is None:
        yield None
        return
    with store.pipeline_session(context.pipeline_run_id) as token:
        recorder = RunRecorder(store, token, context.pipeline_run_id, clock)
        recorder.open(context)
        yield recorder


def _execute(context, stage, recorder):
    """(raw result, result kept in the run). With a recorder the result is also persisted."""
    if recorder is None:
        res = stage.run(context)
        return res, res
    started = recorder.now()
    res = recorder.check_inputs(stage) or stage.run(context)
    return res, recorder.record(context, stage, res, started)


def _run_stages(context, stages, stop_after, stop_on, recorder):
    results, stopped_at = [], None
    for stage in stages:
        raw, kept = _execute(context, stage, recorder)
        context.results[stage.number] = raw
        results.append(kept)
        if raw.status in stop_on:
            stopped_at = stage.number
            break
        if stop_after is not None and stage.number == stop_after:
            break
    return results, stopped_at


def _start(context, stages, stop_after, run_id, from_stage):
    """Check the arguments, reset the context for a new run and (with `from_stage`) restore the reused stages; returns those stages."""
    _check_stop_after(stop_after, stages)
    context.pipeline_run_id = run_id or str(uuid.uuid4())
    context.results = {}
    context.engine_cache = {}
    return _reuse(context, stages, from_stage) if from_stage is not None else []


def _record_all(context, stages, reused, stop_after, stop_on, clock):
    """Run (and record, when the context has a store) the stages that are not reused; returns (results, stopped_at)."""
    with _recording(context, clock) as recorder:
        if recorder and reused:
            recorder.adopt(reused, stages)
        results, stopped_at = _run_stages(context, stages[len(reused):], stop_after, stop_on, recorder)
        if recorder:
            recorder.finish(stages[-1].number)
    return results, stopped_at


def run(context, stop_after=None, run_id=None, clock=None, stages=None, stop_on=STOP_STATUSES, from_stage=None):
    """Run the stages in order; stop at the first stage whose status is in `stop_on` or after stage `stop_after`.

    With `from_stage` N (2 or more) the stages before N are not run again: their recorded results are reused when the frozen inputs, the load list
    and the engine versions are unchanged (else `ResumeError`, before anything is written), and the stages from N on run as usual. The caller
    chooses N: the first stage that reads something that changed (see docs/architecture/GUIA_MOTORES.md, "Re-run from a stage").
    """
    stages = STAGES if stages is None else stages
    reused = _start(context, stages, stop_after, run_id, from_stage)
    started = clock() if clock else None
    results, stopped_at = _record_all(context, stages, reused, stop_after, stop_on, clock)
    results = _renumber(reused + results)
    finished = clock() if clock else None
    return RunResult(context.pipeline_run_id, results, _summary(results, stopped_at, stop_after, [r.stage for r in reused]), started, finished)
