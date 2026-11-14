"""The `epc` subcommands: each loads the user's JSON files, calls ONE `epc_platform.api` function and returns its envelope.

Nothing is computed here: arguments are parsed, files are read, the api function answers. A file that cannot be read or is not valid JSON
becomes an error envelope (`unreadable_file`, `invalid_json`), never a traceback. `COMMANDS` is the table the parser is built from; each
entry names the api function it calls (`api_name`), which the parity test compares with the MCP tools.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from epc_platform import api
from epc_platform.api.engines import REPO

PROJECT = (("project_code",), {"help": "project code (folder name under the projects root)"})
PROJECT_OPT = (("--project",), {"metavar": "CODE", "help": "record the query in this project's audit log"})


@dataclass(frozen=True)
class Session:
    """What every command needs: where the projects live, who acts (RACI role and id) and the injected clock."""

    projects_root: Path
    actor: dict
    clock: Callable[[], str]


@dataclass(frozen=True)
class Command:
    key: str
    help: str
    api_name: str
    handler: Callable[[Session, Any], dict]
    arguments: tuple = ()


def default_projects_root():
    """`projects` next to the harness: in the repository root."""
    return REPO / "projects"


def load_json(path, what):
    """The parsed JSON file; `ApiError` (unreadable_file / invalid_json) when it cannot be read."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise api.ApiError("unreadable_file", f"cannot read the {what} file {path}: {exc}") from exc
    try:
        return json.loads(text)
    except ValueError as exc:
        raise api.ApiError("invalid_json", f"the {what} file {path} is not valid JSON: {exc}") from exc


def _optional_json(path, what):
    return None if path is None else load_json(path, what)


def _project(session, args):
    return api.project_path(session.projects_root, args.project_code)


def _scope(session, args):
    """The keyword arguments that make a query role-checked (and audited in the project named with --project)."""
    scope = {"actor": session.actor}
    if args.project:
        scope.update(project_dir=api.project_path(session.projects_root, args.project), clock=session.clock)
    return scope


def _init(session, args):
    answers = load_json(args.answers, "answers")
    return api.init_project(session.projects_root, args.project_code, answers, clock=session.clock, actor=session.actor, client=args.client, description=args.description)


def _run(session, args):
    loads, inputs = load_json(args.loads, "loads"), _optional_json(args.engine_inputs, "engine inputs")
    return api.run_pipeline(_project(session, args), loads=loads, engine_inputs=inputs, stop_after=args.stop_after, run_id=args.run_id, from_stage=args.from_stage,
                            revision=args.revision, detail=args.detail, clock=session.clock, actor=session.actor)


def _status(session, args):
    return api.status(_project(session, args), clock=session.clock, actor=session.actor)


def _review(session, args):
    corrections = load_json(args.corrections, "corrections")
    return api.review(_project(session, args), session.actor, corrections, clock=session.clock)


def _approve(session, args):
    return api.approve(_project(session, args), session.actor, clock=session.clock)


def _issue(session, args):
    return api.issue(_project(session, args), session.actor, clock=session.clock)


def _engines_list(session, args):
    return api.list_engines(**_scope(session, args))


def _engines_info(session, args):
    return api.engine_info(args.name, **_scope(session, args))


def _norms(session, args):
    return api.norm_records(args.package, **_scope(session, args))


def _norms_pending(session, args):
    return api.norms_pending(args.detail, **_scope(session, args))


def _stages(session, args):
    return api.stage_table(**_scope(session, args))


COMMANDS = {c.key: c for c in (
    Command("init", "create a project from the guided-form answers", "init_project", _init,
            (PROJECT, (("--answers",), {"required": True, "metavar": "FILE.json", "help": "the intake answers (JSON file)"}),
             (("--client",), {"metavar": "NAME", "help": "full client name, upper case words joined by _ (creates projects/<NAME>/<code>_<DESCRIPTION>; the code is then AAAA-PROV-CLI-CODE)"}),
             (("--description",), {"metavar": "TEXT", "help": "project description in the client's language, upper case words joined by _ (with --client)"}))),
    Command("run", "run the pipeline in a project", "run_pipeline", _run, (
        PROJECT,
        (("--loads",), {"required": True, "metavar": "FILE.json", "help": "the load list (JSON file)"}),
        (("--engine-inputs",), {"metavar": "FILE.json", "help": "extra calculation inputs (JSON file)"}),
        (("--stop-after",), {"type": int, "metavar": "N", "help": "stop after stage N"}),
        (("--from-stage",), {"type": int, "metavar": "N", "help": "re-run only stages N.. and reuse the recorded earlier stages when still valid"}),
        (("--run-id",), {"metavar": "ID", "help": "run id (default: generated)"}),
        (("--revision",), {"default": "R0", "metavar": "R", "help": "document revision (default R0)"}),
        (("--detail",), {"action": "store_true", "help": "return every stage output, not only the summary"}))),
    Command("status", "workflow state, project state, reviews and the last audit events", "status", _status, (PROJECT,)),
    Command("review", "record the reviewer's corrections", "review", _review,
            (PROJECT, (("--corrections",), {"required": True, "metavar": "FILE.json", "help": "a JSON list of corrections"}))),
    Command("approve", "approve the reviewed deliverables (engineer of record; D21 guard)", "approve", _approve, (PROJECT,)),
    Command("issue", "issue the approved deliverables (D21 guard)", "issue", _issue, (PROJECT,)),
    Command("engines list", "list the engine packages", "list_engines", _engines_list, (PROJECT_OPT,)),
    Command("engines info", "version and public modules of one engine", "engine_info", _engines_info,
            ((("name",), {"help": "engine package (epc_sld) or area (sld)"}), PROJECT_OPT)),
    Command("norms", "norm records and their review status", "norm_records", _norms,
            ((("package",), {"nargs": "?", "help": "engine package; all engines when omitted"}), PROJECT_OPT)),
    Command("norms-pending", "norm points still to be reviewed (units and totals)", "norms_pending", _norms_pending,
            ((("--detail",), {"action": "store_true", "help": "list the units with pending points"}), PROJECT_OPT)),
    Command("stages", "the 12 pipeline stages", "stage_table", _stages, (PROJECT_OPT,)),
)}


def run_command(session, args):
    """The envelope of the chosen command; nothing raises."""
    try:
        return COMMANDS[args.key].handler(session, args)
    except api.ApiError as exc:
        return api.fail(exc.code, exc.message, exc.details)
    except Exception as exc:  # the CLI never prints a traceback
        return api.fail("internal_error", f"{type(exc).__name__}: {exc}")
