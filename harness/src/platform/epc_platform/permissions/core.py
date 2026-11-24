"""`check`, `classify_path` and `enforce`: the policy of `rules.py` applied to a role, an action and a path."""
from collections import namedtuple
from pathlib import Path

from disciplines.electrical_lv.store import StoreError, clean_parts
from epc_platform.permissions import rules as R

Decision = namedtuple("Decision", "allowed reason rule_id")

REPO_CLASSES = (("harness/config/normative", R.CONFIG_NORMATIVE), ("harness/schemas", R.SCHEMAS), ("harness/src", R.HARNESS_CODE),
                ("harness/tools", R.HARNESS_CODE), ("harness/.claude", R.HARNESS_CODE), ("harness/tests", R.HARNESS_CODE))
INTERNAL = ".epc"
MANIFESTS = "manifests"
ROOT_FILES = ("project_profile.json", "master_project_state.json", "epc_progress.txt")      # files directly inside `.epc/`
INTERNAL_CLASSES = (R.SSOT, R.RUNS, R.REVIEWS, R.AUDIT)                                        # folders inside `.epc/`
OPEN_CLASSES = (R.INPUTS, R.DELIVERABLES, R.TRANSMITTALS)                                      # folders directly in the project


class PermissionDenied(PermissionError):
    """`enforce` refused. `decision` carries the rule."""

    def __init__(self, message, decision):
        super().__init__(message)
        self.decision = decision


class PathError(ValueError):
    """A path that is outside the project (or the repository) or that cannot be classified."""


def _matches(value, options):
    return value in options


def check(role, action, path_class, inputs_frozen=False):
    """The `Decision(allowed, reason, rule_id)` for a role doing an action on a class of path. Unknown names are denied (`D-98`)."""
    if role not in R.ROLES or action not in R.ACTIONS or path_class not in R.PATH_CLASSES:
        return Decision(False, f"unknown role, action or path class: {role!r}, {action!r}, {path_class!r}", "D-98")
    for rule_id, reason, roles, actions, classes, frozen_only in R.DENY:
        if _matches(role, roles) and _matches(action, actions) and _matches(path_class, classes) and (inputs_frozen or not frozen_only):
            return Decision(False, reason, rule_id)
    for rule_id, reason, roles, actions, classes in R.ALLOW:
        if _matches(role, roles) and _matches(action, actions) and _matches(path_class, classes):
            return Decision(True, reason, rule_id)
    return Decision(False, R.DEFAULT_RULE[1], R.DEFAULT_RULE[0])


def may_trigger(role, transition):
    """True when `role` may trigger the workflow transition (RACI)."""
    return role in R.TRIGGERS.get(transition, ())


def _resolve(project_dir, path):
    root = Path(project_dir).resolve()
    if isinstance(path, str) and not Path(path).is_absolute() and not (len(path) > 1 and path[1] == ":"):
        try:
            parts = clean_parts(path)
        except StoreError as exc:
            raise PathError(str(exc)) from exc
        return root, root.joinpath(*parts).resolve()
    return root, Path(path).resolve()


def _inside(path, base):
    try:
        return path.relative_to(base)
    except ValueError:
        return None


def _internal_class(parts):
    """The class of a path inside `.epc/` (`parts` are the parts after `.epc`), or None."""
    if not parts:
        return None
    if parts[0] in INTERNAL_CLASSES:
        return parts[0]
    if parts[0] == MANIFESTS:
        return R.DELIVERABLES            # the manifests are the record of the deliverables: same rules (pipeline writes, engineer signs)
    if len(parts) == 1 and parts[0] in ROOT_FILES:
        return R.SSOT
    return None


def _project_class(rel):
    if not rel.parts:
        raise PathError("the project folder itself is not a classified path")
    if rel.parts[0] in OPEN_CLASSES:
        return rel.parts[0]
    cls = _internal_class(rel.parts[1:]) if rel.parts[0] == INTERNAL else None
    if cls is None:
        raise PathError(f"{rel.as_posix()} is not a known project path")
    return cls


def _repo_class(repo_root, target):
    base = Path(repo_root).resolve()
    for prefix, cls in REPO_CLASSES:
        if _inside(target, base / prefix) is not None:
            return cls
    return None


def classify_path(project_dir, path, repo_root=None):
    """The path class of `path`: a relative POSIX string or an absolute path. Symlinks and junctions are resolved first.

    Inside the project: inputs, deliverables, transmittals and, inside `.epc/`: ssot (also the three project files), runs, reviews, audit, and manifests (classified as deliverables). Inside `repo_root`
    (optional): config_normative, schemas, harness_code. Anything else, or any path that escapes after resolution, raises `PathError`.
    """
    root, target = _resolve(project_dir, path)
    rel = _inside(target, root)
    if rel is not None:
        return _project_class(rel)
    cls = _repo_class(repo_root, target) if repo_root is not None else None
    if cls is None:
        raise PathError(f"{path} is outside the project folder")
    return cls


def enforce(role, action, path_class, inputs_frozen=False, log=None, actor_id="-", run_id="-", target="-"):
    """Like `check`, but raises `PermissionDenied` when denied. Every decision is appended to `log` (an EventLog) when one is given."""
    decision = check(role, action, path_class, inputs_frozen)
    if log is not None:
        log.append({"pipeline_run_id": run_id, "actor": {"role": str(role), "id": str(actor_id)}, "action": f"{action}:{path_class}",
                    "target": str(target), "result": "allowed" if decision.allowed else "denied",
                    "detail": {"rule_id": decision.rule_id, "reason": decision.reason}})
    if not decision.allowed:
        raise PermissionDenied(f"{role} may not {action} {path_class}: {decision.reason} [{decision.rule_id}]", decision)
    return decision
