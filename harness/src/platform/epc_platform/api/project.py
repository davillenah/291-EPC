"""Project functions: `init_project`, `status`, `review`, `approve` and `issue`.

Each one checks the RACI (`permissions.enforce`, which appends the decision to `audit/events.jsonl`) and returns an envelope. The only writes
go through `ProjectStore`: `init_with_answers` (the `/init` flow) and the workflow (`Workflow.transition`, which writes `reviews/` in its own
session). Nothing here writes `ssot/`.
"""
import json

from disciplines.electrical_lv.intake.form import IntakeError
from disciplines.electrical_lv.intake.profile import build_profile
from disciplines.electrical_lv.store import ProjectStore, StoreError
from epc_platform.api import flow
from epc_platform.api.access import actor_of, check_code, existing_project, gate, new_project_path, open_log, pre_gate, project_path
from epc_platform.api.envelope import ApiError, api_call, ok
from epc_platform.workflow import Workflow

LAST_EVENTS = 5
EVENT_KEYS = ("seq", "ts", "pipeline_run_id", "actor", "action", "target", "result")


def _complete_answers(answers, code):
    """The answers with the project code filled in; every reason they cannot become a profile is reported (D24 included)."""
    if not isinstance(answers, dict):
        raise ApiError("invalid_answers", "answers must be an object")
    full = dict(answers)
    if full.setdefault("project_code", code) != code:
        raise ApiError("invalid_answers", f"answers.project_code {full['project_code']!r} differs from the project code {code!r}")
    try:
        build_profile(full)
    except IntakeError as exc:
        raise ApiError("invalid_answers", str(exc), {"errors": exc.errors}) from exc
    return full


@api_call
def init_project(projects_root, project_code, answers, *, clock, actor, client=None, description=None):
    """Create a project from the template with the guided-form answers (D24: earthing scheme and short-circuit level required).

    With `client` and `description` the folder is `<projects_root>/<CLIENT>/<project_code>_<DESCRIPTION>` and the code must be `AAAA-PROVIDER-CLIENT-CODE`;
    without them it is `<projects_root>/<project_code>` (the code is only checked as a safe folder name).
    """
    who = actor_of(actor)
    code = check_code(project_code)
    pre_gate(who, "create", "inputs")           # no project folder yet: a denial leaves nothing behind (and no log)
    full = _complete_answers(answers, code)
    root = _new_root(projects_root, code, client, description)
    try:
        ProjectStore(root).init_with_answers(full)
    except StoreError as exc:
        raise ApiError("project_exists", str(exc)) from exc
    log = open_log(root, clock)
    gate(log, who, "create", "inputs", f"projects/{code}", run_id="init")
    log.append({"pipeline_run_id": "init", "actor": who, "action": "init", "target": f"projects/{code}", "result": "ok", "detail": {}})
    return ok({"project": code, "path": str(root), "workflow_state": Workflow(root, log).state})


def _new_root(projects_root, code, client, description):
    """The folder of a project that does not exist yet: flat without client and description, in the client folder with both."""
    if (client is None) != (description is None):
        raise ApiError("invalid_project", "give both the client and the description, or neither")
    if client is None:
        return project_path(projects_root, code, must_exist=False)
    return new_project_path(projects_root, code, client, description)


def _read_state(store):
    try:
        return store.read_state()
    except StoreError:
        return None


def _events(log):
    records = log.read()
    return {"count": len(records), "chain_intact": not log.verify(), "last": [{k: r[k] for k in EVENT_KEYS} for r in records[-LAST_EVENTS:]]}


def _edit_notice(workflow):
    """For a project in edit mode whose manifests are all edit-mode ones (the D21 guard was not applied): what the answer must say, so nobody takes it for a production approval."""
    if workflow.store.read_mode() != "edit":
        return {}
    return {"mode": "edit", "notice": "edit mode: norm records that are not verified did not stop this step; the package is not for production and nothing was signed"}


def _major_notice(workflow):
    """The `major` findings still open in the manifests in force: they do not stop the step, but the answer says how many there are (SIM-07)."""
    from epc_platform.workflow.machine import open_findings
    n = len(open_findings(workflow.store, "major"))
    return {"open_major_findings": n} if n else {}


def _mode_of(store):
    """{"mode": "edit"} when the project is in edit mode (ADR-0035), else nothing: the answers of a production project are what they always were."""
    return {"mode": "edit"} if store.read_mode() == "edit" else {}


@api_call
def status(project_dir, *, clock, actor):
    """`master_project_state.json`, the workflow state, the review files and the last events of the audit log (this call's own event included)."""
    root, who = existing_project(project_dir), actor_of(actor)
    log = open_log(root, clock)
    gate(log, who, "read", "ssot", "master_project_state.json")
    store = ProjectStore(root)
    workflow = Workflow(root, log, store)
    return ok({"project": root.name,
               "workflow": {"state": workflow.state, "allowed_transitions": workflow.allowed_transitions(), "transitions_done": len(workflow.history())},
               "state": _read_state(store), "reviews": store.list_reviews(), "audit": _events(log), **_mode_of(store)})


def _valid_corrections(corrections):
    if not (isinstance(corrections, list) and corrections and all(isinstance(c, dict) and c for c in corrections)):
        raise ApiError("invalid_arguments", "corrections must be a non-empty list of objects")
    try:
        json.dumps(corrections, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ApiError("invalid_arguments", f"corrections are not plain JSON: {exc}") from exc
    return corrections


@api_call
def review(project_dir, actor, corrections, *, clock):
    """Record the reviewer's corrections: a workflow transition plus `reviews/record_corrections-<n>.json` (both through the store).

    A project in `draft_ready` is first submitted for review (the actor must be allowed to). `ssot/` is never edited: a rerun regenerates it.
    """
    root, who = existing_project(project_dir), actor_of(actor)
    items = _valid_corrections(corrections)
    log = open_log(root, clock)
    gate(log, who, "write", "reviews", "reviews/", run_id="review")
    workflow = Workflow(root, log)
    if workflow.state == "draft_ready":
        flow.apply(workflow, "submit_for_review", who, "review")
    state = flow.apply(workflow, "record_corrections", who, "review", review={"corrections": items, "recorded_by": who})
    return ok({"workflow_state": state, "review_file": f".epc/reviews/record_corrections-{len(workflow.history())}.json", "corrections": len(items)})


@api_call
def issue(project_dir, actor, *, clock):
    """The workflow transition `issue` (approved -> issued). The D21 guard refuses it while a norm record is not verified or there is no manifest."""
    root, who = existing_project(project_dir), actor_of(actor)
    workflow = Workflow(root, open_log(root, clock))
    state = flow.apply(workflow, "issue", who, "issue")
    return ok({"workflow_state": state, **_edit_notice(workflow), **_major_notice(workflow)})


@api_call
def submit(project_dir, actor, *, clock):
    """The workflow transition `submit_for_review` (draft_ready -> in_review): what puts a finished run in front of the engineer of record, who then approves it (PRB-03). Nothing is approved or signed here."""
    root, who = existing_project(project_dir), actor_of(actor)
    workflow = Workflow(root, open_log(root, clock))
    state = flow.apply(workflow, "submit_for_review", who, "submit")
    return ok({"workflow_state": state})


@api_call
def approve(project_dir, actor, *, clock):
    """The workflow transition `approve` (in_review -> approved): engineer of record only, `sign` permission, and the D21 guard."""
    root, who = existing_project(project_dir), actor_of(actor)
    workflow = Workflow(root, open_log(root, clock))
    state = flow.apply(workflow, "approve", who, "approve")
    return ok({"workflow_state": state, **_edit_notice(workflow), **_major_notice(workflow)})
