"""Shared guards of the API functions: project folders, actors and the permission gate (every decision goes to the event log)."""
import re
from pathlib import Path

from epc_platform.api.envelope import ApiError
from epc_platform.events import EventLog
from epc_platform.permissions import PermissionDenied, check, enforce

CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
API_RUN = "api"


def check_code(code):
    """A project code as one safe folder name."""
    text = code if isinstance(code, str) else ""
    if not CODE.fullmatch(text) or ".." in text or text.endswith("."):
        raise ApiError("invalid_project", "a project code uses letters, digits, dot, dash and underscore (at most 64 characters)")
    return text


def project_path(projects_root, code, must_exist=True):
    """`<projects_root>/<code>` as a resolved path; refuses anything that leaves the projects root."""
    root = Path(projects_root).resolve()
    target = (root / check_code(code)).resolve()
    if target.parent != root:
        raise ApiError("invalid_project", "the project is outside the projects root")
    if must_exist and not target.is_dir():
        raise ApiError("project_not_found", f"unknown project {code}")
    return target


def existing_project(project_dir):
    """The resolved project folder (it must exist and look like a project: it has an `.epc/audit/` folder)."""
    root = Path(project_dir).resolve()
    if not (root / ".epc" / "audit").is_dir():
        raise ApiError("project_not_found", f"{root.name} is not an initialised project folder")
    return root


def actor_of(actor):
    """`{'role', 'id'}` of the caller; anything else is refused before a log is touched."""
    if not (isinstance(actor, dict) and isinstance(actor.get("role"), str) and isinstance(actor.get("id"), str) and actor["role"] and actor["id"]):
        raise ApiError("invalid_actor", "actor must be {'role': str, 'id': str}")
    return {"role": actor["role"], "id": actor["id"]}


def open_log(root, clock):
    if not callable(clock):
        raise ApiError("invalid_arguments", "an injected clock is required")
    return EventLog.for_project(root, clock)


def gate(log, actor, action, path_class, target, run_id=API_RUN):
    """Check the RACI for the actor; the decision (allowed or denied) is appended to the log. A denial becomes `ApiError('permission_denied')`."""
    try:
        return enforce(actor["role"], action, path_class, log=log, actor_id=actor["id"], run_id=run_id, target=target)
    except PermissionDenied as exc:
        raise ApiError("permission_denied", str(exc), {"rule_id": exc.decision.rule_id, "role": actor["role"], "action": action, "path_class": path_class}) from exc


def pre_gate(actor, action, path_class):
    """The same decision without a log (for the one call that has no project folder yet): `ApiError` when denied."""
    decision = check(actor["role"], action, path_class)
    if not decision.allowed:
        raise ApiError("permission_denied", f"{actor['role']} may not {action} {path_class}: {decision.reason} [{decision.rule_id}]",
                       {"rule_id": decision.rule_id, "role": actor["role"], "action": action, "path_class": path_class})
    return decision
