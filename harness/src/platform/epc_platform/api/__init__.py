"""The platform's function layer: plain functions over JSON-serialisable dicts, independent of any transport.

The MCP server (`epc_mcp`, MIG-33b) and the `epc` CLI (MIG-33c) call exactly these functions, so both expose the same behaviour
(PRD 14.5; the parity tests compare them with the direct pipeline call).

Conventions
  * Every function returns an envelope: `{"ok": True, "data": ..., "warnings": []}` or `{"ok": False, "error": {"code", "message"}}`.
    Nothing raises across the boundary (`envelope.api_call`).
  * `actor` is `{"role": <RACI role>, "id": <name>}`; `clock` is a callable returning the timestamp text (injected, never the system clock).
  * Project functions check the RACI with `permissions.enforce` and append the decision to `audit/events.jsonl` (`allowed` or `denied`).
  * The only writes go through `ProjectStore`: the `/init` flow, the pipeline run and the workflow. No function here writes `ssot/` itself.
"""
from epc_platform.api.access import project_path
from epc_platform.api.engines import engine_info, list_engines, norm_records, norms_pending, stage_table
from epc_platform.api.envelope import ApiError, fail, ok
from epc_platform.api.project import approve, init_project, issue, review, status, submit
from epc_platform.api.run import run_pipeline

__all__ = ["ApiError", "approve", "engine_info", "fail", "init_project", "issue", "list_engines", "norm_records", "norms_pending", "ok", "project_path", "review", "submit",
           "run_pipeline", "stage_table", "status"]
