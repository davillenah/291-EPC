"""Read-only engine queries: the stage table, the engine packages, their public modules and their norm records.

The engine packages are found by scanning `harness/src/engines/<group>/<area>/src/epc_*` (nothing is imported: versions are read from the
package text), because the platform may not import the repository tools. Numbers are never computed here.
"""
import json
import re
from pathlib import Path

from disciplines.electrical_lv import norm_review
from disciplines.electrical_lv.norm_records import read_norm_records
from disciplines.electrical_lv.stages import STAGES
from epc_platform.api.access import actor_of, existing_project, gate, open_log
from epc_platform.api.envelope import ApiError, api_call, ok

ENGINES_DIR = Path(__file__).resolve().parents[3] / "engines"
REPO = ENGINES_DIR.parents[2]
VERSION = re.compile(r"""^(?:__version__|VERSION)\s*=\s*["']([^"']+)["']""", re.MULTILINE)


def _version(package_dir):
    """`__version__` of the package, or the `VERSION` of its `config.py` (the engines that re-export it); None when neither is text."""
    for name in ("__init__.py", "config.py"):
        path = package_dir / name
        found = VERSION.search(path.read_text(encoding="utf-8")) if path.is_file() else None
        if found:
            return found.group(1)
    return None


def scan_engines(engines_dir=None):
    """Every engine package: [{'package', 'area', 'group', 'version'}] sorted by group and area."""
    base = Path(engines_dir or ENGINES_DIR)
    found = []
    for src in sorted(base.glob("*/*/src")):
        for folder in sorted(p for p in src.glob("epc_*") if p.is_dir() and (p / "__init__.py").is_file()):
            found.append({"package": folder.name, "area": src.parent.name, "group": src.parent.parent.name, "version": _version(folder)})
    return found


def _folder(engine):
    return ENGINES_DIR / engine["group"] / engine["area"] / "src" / engine["package"]


def _public_modules(package_dir):
    names = [p.stem for p in package_dir.glob("*.py") if not p.name.startswith("_")]
    names += [p.name for p in package_dir.iterdir() if p.is_dir() and (p / "__init__.py").is_file() and not p.name.startswith("_")]
    return sorted(names)


def _find(name):
    for engine in scan_engines():
        if name in (engine["package"], engine["area"]):
            return engine
    raise ApiError("unknown_engine", f"no engine {name!r}; use list_engines() for the names")


class _NoLog:
    """A log that keeps nothing: the decision is still made by `enforce`, there is just no project to record it in."""

    def append(self, event):
        return event


def _read_gate(actor, project_dir, clock, path_class, target):
    """Queries need no project. With an actor the role is checked; with a project folder too, the decision is logged there."""
    if actor is None:
        return
    who = actor_of(actor)
    log = _NoLog() if project_dir is None else open_log(existing_project(project_dir), clock)
    gate(log, who, "read", path_class, target)


@api_call
def stage_table(*, actor=None, project_dir=None, clock=None):
    """The 12 stages of the PRD in order: number, slug, title, engines, PRD status and whether the stage runs real work today."""
    _read_gate(actor, project_dir, clock, "schemas", "stage_table")
    rows = [{"number": s.number, "slug": s.spec.slug, "title": s.spec.title, "engines": s.spec.engines_text, "status": s.spec.status_text,
             "phase1_status": s.spec.phase1_status, "wired": s.wired, "wiring_task": s.wiring_task} for s in STAGES]
    return ok({"count": len(rows), "stages": rows})


@api_call
def list_engines(*, actor=None, project_dir=None, clock=None):
    """The engine packages found in the repository, with group, area and version."""
    _read_gate(actor, project_dir, clock, "harness_code", "engines")
    engines = scan_engines()
    return ok({"count": len(engines), "engines": engines})


@api_call
def engine_info(name, *, actor=None, project_dir=None, clock=None):
    """Version, folder and public modules of one engine (`name` is the package, `epc_aea90364`, or the area, `aea90364`)."""
    _read_gate(actor, project_dir, clock, "harness_code", f"engine:{name}")
    engine = _find(name)
    folder = _folder(engine)
    info = dict(engine, public_modules=_public_modules(folder), has_norm_register=(folder / "norm_register").is_dir(),
                path=folder.relative_to(REPO).as_posix())
    return ok(info)


@api_call
def engine_schema(name, *, actor=None, project_dir=None, clock=None):
    """The JSON schemas an engine publishes (`<package>/schema/*.json`: its input, and its output when it has one), read as they are. Read only.

    `name` is the package or the area. The schemas are the engine's own contract (what an agent must send, with types, required keys and limits); an engine
    with no schema gives an empty list, and says so in a note."""
    _read_gate(actor, project_dir, clock, "harness_code", f"engine_schema:{name}")
    engine = _find(name)
    folder = _folder(engine) / "schema"
    files = sorted(folder.glob("*.json")) if folder.is_dir() else []
    schemas = {f.name: json.loads(f.read_text(encoding="utf-8")) for f in files}
    warnings = [] if schemas else [f"{engine['package']} publishes no schema yet"]
    return ok({"package": engine["package"], "count": len(schemas), "schemas": schemas}, warnings)


@api_call
def norm_records(package=None, *, actor=None, project_dir=None, clock=None):
    """Norm records (id, review status) of one engine package, or of every engine when no package is given. Read only; never a review change."""
    _read_gate(actor, project_dir, clock, "config_normative", f"norm_records:{package or '*'}")
    packages = [_find(package)["package"]] if package else [e["package"] for e in scan_engines()]
    records = read_norm_records(packages)
    by_status = {}
    for record in records:
        by_status[record["review_status"]] = by_status.get(record["review_status"], 0) + 1
    return ok({"packages": packages, "count": len(records), "by_status": dict(sorted(by_status.items())), "records": records})


@api_call
def norms_pending(detail=False, *, actor=None, project_dir=None, clock=None):
    """Norm values still to be reviewed: units, units with pending points and the number of pending points (pending + stale). Read only; never a review change.

    The count is platform-wide (the review units of the engines), not filtered by project."""
    _read_gate(actor, project_dir, clock, "config_normative", "norms_pending")
    found = norm_review.summary()
    rows = [{"unit": r["id"], "name": r["name"], "total": r["total"], "pending": r["pending"]} for r in found["rows"] if r["pending"]]
    data = {"units": found["units"], "units_with_pending": found["units_with_pending"], "pending_points": found["pending_points"]}
    if detail:
        data["rows"] = rows
    return ok(data, ["these are the platform's unreviewed norm values; they are not filtered by project"])
