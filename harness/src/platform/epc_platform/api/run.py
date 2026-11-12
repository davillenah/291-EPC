"""`run_pipeline`: the 16 stages over a project folder, recorded by the pipeline itself (the only writer of `ssot/`, `runs/`, `deliverables/`).

The role must be allowed to `start_run` (RACI: the orchestrator). The workflow is walked to `running` first and to `draft_ready` after a
complete, healthy run. Every number in the result is a stage result produced by an engine call inside the pipeline.
"""
from disciplines.electrical_lv import pipeline
from disciplines.electrical_lv.stages import STAGES, PipelineContext
from disciplines.electrical_lv.store import ProjectStore, StoreError, check_run_id
from epc_platform.api import flow
from epc_platform.api.access import actor_of, existing_project, open_log
from epc_platform.api.envelope import ApiError, api_call, ok
from epc_platform.audit import AuditTrail
from epc_platform.permissions import may_trigger
from epc_platform.workflow import Workflow


def _trail(log, clock, run_id, rng):
    try:
        trail = AuditTrail(log, clock, rng=rng, run_id=check_run_id(run_id) if run_id else None)
    except StoreError as exc:
        raise ApiError("invalid_arguments", str(exc)) from exc
    if run_id is None:
        trail.new_run_id()
    return trail


def _check_objects(loads, engine_inputs):
    for name, value in (("loads", loads), ("engine_inputs", engine_inputs)):
        if value is not None and not isinstance(value, dict):
            raise ApiError("invalid_arguments", f"{name} must be an object")


def _authorise(trail, actor, root):
    if may_trigger(actor["role"], "start_run"):
        return
    reason = f"{actor['role']} may not start a run (RACI)"
    trail.record(actor, "run:start", root.name, "denied", {"reason": reason})
    raise ApiError("permission_denied", reason, {"role": actor["role"], "transition": "start_run"})


def _execute(trail, actor, context, stop_after, clock):
    name = context.store.root.name
    try:
        result = pipeline.run(context, stop_after=stop_after, run_id=trail.run_id, clock=clock)
    except Exception as exc:  # the run is reported, not raised
        trail.record(actor, "run:finish", name, "failed", {"error": f"{type(exc).__name__}: {exc}"})
        raise ApiError("run_failed", f"{type(exc).__name__}: {exc}", {"pipeline_run_id": trail.run_id}) from exc
    trail.record(actor, "run:finish", name, "ok" if result.summary["ok"] else "failed", result.summary)
    return result


def _brief(run):
    """The run without the stage outputs: per stage the status, message, reason and the counts of findings and engine calls."""
    rows = [{"stage": r["stage"], "status": r["status"], "message": r["message"], "reason": r["reason"], "findings": len(r["findings"]),
             "engine_calls": r["engine_calls"]} for r in run["results"]]
    return dict(run, results=rows)


def _prepare(root, who, loads, engine_inputs):
    """The project store and its intake answers, after the argument checks."""
    _check_objects(loads, engine_inputs)
    store = ProjectStore(root)
    answers = store.read_answers()
    if answers is None:
        raise ApiError("no_answers", "the project has no intake answers: create it with init_project")
    return store, answers


@api_call
def run_pipeline(project_dir, *, loads=None, engine_inputs=None, stop_after=None, run_id=None, clock, actor, revision="R0", detail=True, rng=None):
    """Run the pipeline in the project. `loads` and `engine_inputs` are the load list and the extra calculation inputs (see the stage docs)."""
    root, who = existing_project(project_dir), actor_of(actor)
    log = open_log(root, clock)
    trail = _trail(log, clock, run_id, rng)
    _authorise(trail, who, root)
    store, answers = _prepare(root, who, loads, engine_inputs)
    workflow = Workflow(root, log, store)
    flow.enter_running(workflow, who, trail.run_id)
    trail.record(who, "run:start", root.name, "allowed", {"stop_after": stop_after, "revision": revision})
    context = PipelineContext(answers=answers, loads=loads, engine_inputs=engine_inputs, store=store, revision=revision)
    result = _execute(trail, who, context, stop_after, clock)
    if result.summary["ok"] and result.summary["stages_run"] == len(STAGES):
        flow.apply(workflow, "finish_run", who, trail.run_id)
    run = result.to_dict()
    return ok({"pipeline_run_id": trail.run_id, "workflow_state": workflow.state, "run": run if detail else _brief(run), "audit": trail.summary()})
