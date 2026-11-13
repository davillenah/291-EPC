"""Shared guards of the API functions: project folders, actors and the permission gate (every decision goes to the event log)."""
import re
from pathlib import Path

from epc_platform.api.envelope import ApiError
from epc_platform.events import EventLog
from epc_platform.permissions import PermissionDenied, check, enforce

CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
PROJECT_CODE = re.compile(r"[0-9]{4}-[A-Z]{2,4}-[A-Z]{2,4}-[A-Z0-9]{3,6}")       # AAAA-PROVIDER-CLIENT-CODE, e.g. 2026-ES-HNDA-3085
NAME = re.compile(r"[A-Z0-9]+(_[A-Z0-9]+)*")                                      # client folder and project description: upper case ASCII words joined by _
TEMPLATE_FOLDER = "_template"
API_RUN = "api"


def check_code(code):
    """A project code as one safe folder name."""
    text = code if isinstance(code, str) else ""
    if not CODE.fullmatch(text) or ".." in text or text.endswith("."):
        raise ApiError("invalid_project", "a project code uses letters, digits, dot, dash and underscore (at most 64 characters)")
    return text


def _matches(folder, code):
    return folder.name == code or folder.name.startswith(code + "_")


def project_path(projects_root, code, must_exist=True):
    """The project folder of `code`: `<projects_root>/<code>` (flat) or `<projects_root>/<CLIENT>/<code>_<DESCRIPTION>` (the code is the part before the first `_`).

    A project that exists is searched in both places; two folders with the same code are refused. Refuses anything that leaves the projects root.
    """
    root, code = Path(projects_root).resolve(), check_code(code)
    flat = (root / code).resolve()
    if flat.parent != root:
        raise ApiError("invalid_project", "the project is outside the projects root")
    if not must_exist or flat.is_dir():
        return flat
    found = sorted(_find(root, code)) if root.is_dir() else []
    if len(found) > 1:
        raise ApiError("ambiguous_project", f"{len(found)} folders match the project code {code}: {', '.join(p.parent.name + '/' + p.name for p in found)}")
    if not found:
        raise ApiError("project_not_found", f"unknown project {code}")
    return found[0].resolve()


def new_project_path(projects_root, code, client, description):
    """`<projects_root>/<CLIENT>/<code>_<DESCRIPTION>` for a project that does not exist yet.

    `code` is `AAAA-PROVIDER-CLIENT-CODE` (4-digit year, 2-4 letter provider and client abbreviations, 3-6 letter or digit code); `client` is the full client name and
    `description` the project description (in the client's language), both upper case ASCII words joined by `_`.
    """
    code = check_code(code)
    if not PROJECT_CODE.fullmatch(code):
        raise ApiError("invalid_project", "a project code is AAAA-PROVIDER-CLIENT-CODE, for example 2026-ES-HNDA-3085")
    for what, text in (("client", client), ("description", description)):
        if not (isinstance(text, str) and NAME.fullmatch(text) and len(text) <= 64):
            raise ApiError("invalid_project", f"the {what} is upper case ASCII words joined by _ (at most 64 characters), for example HONDA or ILUMINACION_PERIMETRAL_CARPOOL")
    root = Path(projects_root).resolve()
    if root.is_dir() and (project_path(root, code, must_exist=False).is_dir() or _find(root, code)):
        raise ApiError("project_exists", f"a project with the code {code} already exists")
    return (root / client / f"{code}_{description}").resolve()


def _find(root, code):
    return [p for client in sorted(root.iterdir()) if client.is_dir() and client.name != TEMPLATE_FOLDER for p in client.iterdir() if p.is_dir() and _matches(p, code)]


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
