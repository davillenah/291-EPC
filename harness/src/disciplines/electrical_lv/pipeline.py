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

__all__ = ["STAGES", "STAGE_TABLE", "PipelineContext", "RunResult", "StageResult", "run"]


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


def _summary(results, stopped_at, stop_after):
    by_status = {}
    for res in results:
        by_status[res.status] = by_status.get(res.status, 0) + 1
    return {
        "stages_run": len(results),
        "by_status": dict(sorted(by_status.items())),
        "ok": not any(r.status in STOP_STATUSES for r in results),
        "stopped_at": stopped_at,
        "stop_after": stop_after,
        "not_available": [r.stage for r in results if r.status == "not_available"],
        "findings": sum(len(r.findings) for r in results),
    }


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


def run(context, stop_after=None, run_id=None, clock=None, stages=None, stop_on=STOP_STATUSES):
    """Run the stages in order; stop at the first stage whose status is in `stop_on` or after stage `stop_after`."""
    stages = STAGES if stages is None else stages
    _check_stop_after(stop_after, stages)
    context.pipeline_run_id = run_id or str(uuid.uuid4())
    context.results = {}
    context.engine_cache = {}
    started = clock() if clock else None
    with _recording(context, clock) as recorder:
        results, stopped_at = _run_stages(context, stages, stop_after, stop_on, recorder)
        if recorder:
            recorder.finish(stages[-1].number)
    results = _renumber(results)
    finished = clock() if clock else None
    return RunResult(context.pipeline_run_id, results, _summary(results, stopped_at, stop_after), started, finished)
