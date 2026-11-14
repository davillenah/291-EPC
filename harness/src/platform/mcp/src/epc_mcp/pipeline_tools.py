"""Tools over the platform API (MIG-33b): the pipeline, the project state and the read-only engine queries.

They call `epc_platform.api` only (the same functions the `epc` CLI uses). The API returns the envelope; this layer adds
no value of its own: every number in a result comes from an engine call inside the pipeline. Read tools are in both profiles; the write tools
(`epc_project_init`, `epc_pipeline_run`, `epc_project_review`, `epc_project_approve`, `epc_project_issue`) are in the `full` profile only.
"""
import importlib

from epc_mcp.envelope import ToolError
from epc_mcp.registry import Context, Registry, Tool

PROJECT = {"project": {"type": "string", "description": "project code (folder name under the projects root)"}}
OPTIONAL_PROJECT = {"project": {"type": "string", "description": "optional: record the query in this project's audit log"}}
TEXT = {"type": "string"}
OBJECT = {"type": "object"}


def _api():
    """`epc_platform.api`, imported on first use: the server starts without the platform on the path."""
    return importlib.import_module("epc_platform.api")


def _dir(ctx: Context, args: dict):
    api = _api()
    try:
        return _api().project_path(ctx.projects_root, args.get("project"))
    except api.ApiError as exc:
        raise ToolError(exc.code, exc.message)


def _query_scope(ctx: Context, args: dict) -> dict:
    """The keyword arguments that make a query role-checked (and audited when a project is named)."""
    scope = {"actor": ctx.who()}
    if args.get("project"):
        scope.update(project_dir=_dir(ctx, args), clock=ctx.now)
    return scope


def epc_stage_table(ctx: Context, args: dict):
    return _api().stage_table(**_query_scope(ctx, args))


def epc_engine_list(ctx: Context, args: dict):
    return _api().list_engines(**_query_scope(ctx, args))


def epc_engine_info(ctx: Context, args: dict):
    return _api().engine_info(args["name"], **_query_scope(ctx, args))


def epc_norm_records(ctx: Context, args: dict):
    return _api().norm_records(args.get("package"), **_query_scope(ctx, args))


def epc_norms_pending(ctx: Context, args: dict):
    return _api().norms_pending(bool(args.get("detail", False)), **_query_scope(ctx, args))


def epc_project_status(ctx: Context, args: dict):
    return _api().status(_dir(ctx, args), clock=ctx.now, actor=ctx.who())


def epc_project_init(ctx: Context, args: dict):
    return _api().init_project(ctx.projects_root, args.get("project"), args["answers"], clock=ctx.now, actor=ctx.who(),
                                 client=args.get("client"), description=args.get("description"))


def epc_pipeline_run(ctx: Context, args: dict):
    return _api().run_pipeline(_dir(ctx, args), loads=args.get("loads"), engine_inputs=args.get("engine_inputs"), stop_after=args.get("stop_after"),
                            from_stage=args.get("from_stage"), run_id=args.get("run_id"), revision=args.get("revision", "R0"), detail=bool(args.get("detail", False)),
                            clock=ctx.now, actor=ctx.who())


def epc_project_review(ctx: Context, args: dict):
    return _api().review(_dir(ctx, args), ctx.who(), args["corrections"], clock=ctx.now)


def epc_project_submit(ctx: Context, args: dict):
    return _api().submit(_dir(ctx, args), ctx.who(), clock=ctx.now)


def epc_project_approve(ctx: Context, args: dict):
    return _api().approve(_dir(ctx, args), ctx.who(), clock=ctx.now)


def epc_project_issue(ctx: Context, args: dict):
    return _api().issue(_dir(ctx, args), ctx.who(), clock=ctx.now)


def register(reg: Registry) -> None:
    full, both = ("full",), ("full", "readonly")
    reg.register(Tool("epc_stage_table", "The 12 stages of the pipeline (PRD 12): title, engines, status and whether each runs real work.",
                      epc_stage_table, OPTIONAL_PROJECT, [], both))
    reg.register(Tool("epc_engine_list", "The engine packages (name, group, area, version).", epc_engine_list, OPTIONAL_PROJECT, [], both))
    reg.register(Tool("epc_engine_info", "Version and public modules of one engine (package name or area).", epc_engine_info,
                      dict(OPTIONAL_PROJECT, name=TEXT), ["name"], both))
    reg.register(Tool("epc_norm_records", "Norm records and their review status for one engine package, or all of them. Read only.", epc_norm_records,
                      dict(OPTIONAL_PROJECT, package=TEXT), [], both))
    reg.register(Tool("epc_norms_pending", "Norm points still to be reviewed: units, units with pending points and the pending total (units with detail=true). Platform-wide, read only.",
                      epc_norms_pending, dict(OPTIONAL_PROJECT, detail={"type": "boolean"}), [], both))
    reg.register(Tool("epc_project_status", "Workflow state, master_project_state, review files and the last audit events of a project.",
                      epc_project_status, PROJECT, ["project"], both))
    reg.register(Tool("epc_project_init", "Create a project from the guided-form answers (earthing scheme and short-circuit level are required).",
                      epc_project_init, dict(PROJECT, answers=OBJECT, client={"type": "string"}, description={"type": "string"}), ["project", "answers"], full))
    reg.register(Tool("epc_pipeline_run", "Run the pipeline in a project; the result holds the engines' numbers. `detail: true` returns every stage output.",
                      epc_pipeline_run, dict(PROJECT, loads=OBJECT, engine_inputs=OBJECT, stop_after={"type": "integer"}, from_stage={"type": "integer"}, run_id=TEXT, revision=TEXT,
                                             detail={"type": "boolean"}), ["project"], full))
    reg.register(Tool("epc_project_review", "Record the reviewer's corrections (a workflow transition and a file under reviews/). Never edits ssot.",
                      epc_project_review, dict(PROJECT, corrections={"type": "array", "items": OBJECT}), ["project", "corrections"], full))
    reg.register(Tool("epc_project_submit", "Put a finished run in review (workflow transition `submit_for_review`: draft_ready -> in_review); it approves and signs nothing.",
                      epc_project_submit, PROJECT, ["project"], full))
    reg.register(Tool("epc_project_approve", "Approve the reviewed deliverables (workflow transition `approve`: engineer of record only; refused while a norm value is not verified, D21).",
                      epc_project_approve, PROJECT, ["project"], full))
    reg.register(Tool("epc_project_issue", "Issue the approved deliverables (workflow transition `issue`; refused while a norm value is not verified, D21).",
                      epc_project_issue, PROJECT, ["project"], full))
