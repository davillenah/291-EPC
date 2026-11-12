"""Workflow transitions for the API: errors of the state machine become API errors with stable codes."""
from epc_platform.api.envelope import ApiError
from epc_platform.permissions import PermissionDenied, may_trigger
from epc_platform.workflow import WorkflowBlocked, WorkflowError

# state -> transitions that bring a project to `running` (a run may also continue a project that is already running)
ENTRY = {"init": ("complete_intake", "start_run"), "intake_done": ("start_run",), "corrected": ("rerun",), "running": ()}


def _not_a_trigger(workflow, name, actor, run_id):
    """The RACI check first, whatever the state: a role that may not trigger the transition is refused and the denial is logged."""
    reason = f"{actor['role']} may not trigger {name} (RACI)"
    workflow.log.append({"pipeline_run_id": run_id, "actor": dict(actor), "action": f"transition:{name}", "target": "reviews/workflow.json",
                         "result": "denied", "detail": {"reason": reason}})
    raise ApiError("permission_denied", reason, {"role": actor["role"], "transition": name})


def apply(workflow, name, actor, run_id, review=None):
    """Apply one transition for the actor; returns the new state. The workflow logs its own `ok` and `denied` events."""
    if not may_trigger(actor["role"], name):
        _not_a_trigger(workflow, name, actor, run_id)
    try:
        return workflow.transition(name, actor["role"], actor["id"], run_id=run_id, review=review)
    except WorkflowBlocked as exc:
        raise ApiError("blocked_d21", str(exc)) from exc
    except WorkflowError as exc:
        raise ApiError("bad_state", str(exc)) from exc
    except PermissionDenied as exc:
        raise ApiError("permission_denied", str(exc), {"rule_id": exc.decision.rule_id, "role": actor["role"], "transition": name}) from exc


def enter_running(workflow, actor, run_id):
    """Walk the project to `running` (complete_intake, start_run or rerun as the state requires)."""
    state = workflow.state
    if state not in ENTRY:
        raise ApiError("bad_state", f"a run needs a project in {sorted(ENTRY)}, it is {state}")
    for name in ENTRY[state]:
        apply(workflow, name, actor, run_id)
    return workflow.state
