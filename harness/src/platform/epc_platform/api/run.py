"""`run_pipeline`: the 12 stages over a project folder, recorded by the pipeline itself (the only writer of `ssot/`, `runs/`, `deliverables/`).

The role must be allowed to `start_run` (RACI: the orchestrator). The workflow is walked to `running` first and to `draft_ready` after a
complete, healthy run. Every number in the result is a stage result produced by an engine call inside the pipeline.
"""
from disciplines.electrical_lv import pipeline
from disciplines.electrical_lv.intake.building import BuildingError, derive_all
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


def _start_detail(stop_after, revision, from_stage):
    return {"stop_after": stop_after, "revision": revision, **({"from_stage": from_stage} if from_stage else {})}


def _fail(trail, actor, name, exc, from_stage):
    """Log the failed run and raise it as an API error: `cannot_resume` when the stages before `from_stage` cannot be reused, else `run_failed`."""
    resume = isinstance(exc, pipeline.ResumeError)
    message = str(exc) if resume else f"{type(exc).__name__}: {exc}"
    trail.record(actor, "run:finish", name, "failed", {"error": message})
    details = {"pipeline_run_id": trail.run_id, **({"from_stage": from_stage} if resume else {})}
    raise ApiError("cannot_resume" if resume else "run_failed", message, details) from exc


def _execute(trail, actor, context, stop_after, clock, from_stage=None):
    name = context.store.root.name
    try:
        result = pipeline.run(context, stop_after=stop_after, run_id=trail.run_id, clock=clock, from_stage=from_stage)
    except Exception as exc:  # the run is reported, not raised
        _fail(trail, actor, name, exc, from_stage)
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


def _with_building(loads, engine_inputs):
    """(loads, engine_inputs) after the building section, if any, has been turned into lighting loads and the lighting section of stage 3."""
    if not engine_inputs or "building" not in engine_inputs:
        return loads, engine_inputs
    if not isinstance(loads, dict):
        raise ApiError("invalid_arguments", "the building section adds lighting loads to a load list: give the load list")
    if "lighting" in engine_inputs:
        raise ApiError("invalid_arguments", "engine_inputs has both `building` and `lighting`: the lighting section is derived from the building")
    try:
        done = derive_all(engine_inputs["building"], loads)
    except BuildingError as exc:
        raise ApiError("invalid_arguments", f"building: {exc}", {"errors": exc.errors}) from exc
    loads = done["loads"]
    circuits = dict(engine_inputs.get("circuits") or {})
    for load_id, options in done["circuits"].items():
        if load_id in circuits:
            raise ApiError("invalid_arguments", f"building: circuit options of {load_id} are given twice (building floor and engine_inputs.circuits)")
        circuits[load_id] = options
    return loads, dict(engine_inputs, lighting=done["lighting"], circuits=circuits, **({"routing": done["routing"]} if done["routing"] else {}))


@api_call
def run_pipeline(project_dir, *, loads=None, engine_inputs=None, stop_after=None, run_id=None, clock, actor, revision="R0", detail=True, rng=None, from_stage=None):
    """Run the pipeline in the project. `loads` and `engine_inputs` are the load list and the extra calculation inputs (see the stage docs).

    `from_stage` N re-runs only stages N.. and reuses the recorded results of the earlier ones when they are still valid (a correction that
    only touches late inputs, such as the bill of quantities or the drawing date, does not repeat the calculation)."""
    root, who = existing_project(project_dir), actor_of(actor)
    log = open_log(root, clock)
    trail = _trail(log, clock, run_id, rng)
    _authorise(trail, who, root)
    store, answers = _prepare(root, who, loads, engine_inputs)
    loads, engine_inputs = _with_building(loads, engine_inputs)
    workflow = Workflow(root, log, store)
    flow.enter_running(workflow, who, trail.run_id)
    trail.record(who, "run:start", root.name, "allowed", _start_detail(stop_after, revision, from_stage))
    context = PipelineContext(answers=answers, loads=loads, engine_inputs=engine_inputs, store=store, revision=revision)
    result = _execute(trail, who, context, stop_after, clock, from_stage)
    if result.summary["ok"] and result.summary["stages_run"] == len(STAGES):
        flow.apply(workflow, "finish_run", who, trail.run_id)
    run = result.to_dict()
    return ok({"pipeline_run_id": trail.run_id, "workflow_state": workflow.state, "run": run if detail else _brief(run), "audit": trail.summary()})
