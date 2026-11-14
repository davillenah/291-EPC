# mcp

Status: **in development**

The EPC MCP server (package `epc_mcp`, stdio): `pyproject.toml`, `src/epc_mcp/` and `tests/`. Further servers (for example one for the rules engine) are planned for the engine-extraction phase; each will wrap an `engine/` package.

## Tools

Retired in MIG-38b (the server has only tools that call `epc_platform.api`). The sixteen older tools read and wrote the data of the parked web backend through `backend_link`; the code and its two test files are archived in `_archive/mcp_web_tools/`.

| Retired tool | Why |
| --- | --- |
| `project_create`, `project_status` | Covered by `epc_project_init` and `epc_project_status`. |
| `norms_pending` | Re-implemented as `epc_norms_pending` (api `norms_pending`, CLI `norms-pending`). |
| `criteria_get`, `loads_list`, `boards_list`, `layout_get`, `documents_list`, `document_read` | Read the web app's project database; retired with the web (paused). |
| `intake_add`, `intake_pending`, `intake_apply`, `boards_declare`, `loads_add`, `layout_rooms_set`, `arch_read` | Wrote the web app's project database; retired with the web (paused). |

Not replaced on the platform yet (owner items): listing the loads, boards, layout sheets and documents of a project, reading a document by id, the design-criteria values of a project, and adding intake records one by one. The pipeline tools cover init, run, status, review, approve and issue.

Pipeline tools (MIG-33b). They call `epc_platform.api` only, the same functions the `epc` CLI uses (MIG-33c); numbers come only from engine calls inside the pipeline.

| Tool | Profile | What it does |
| --- | --- | --- |
| `epc_stage_table` | full, readonly | The 12 stages of the pipeline: title, engines, status, wired or not. |
| `epc_engine_list` | full, readonly | The engine packages with group, area and version. |
| `epc_engine_info` | full, readonly | Version and public modules of one engine. |
| `epc_norm_records` | full, readonly | Norm records and review status of one engine (or all). Read only. |
| `epc_norms_pending` | full, readonly | Norm points still to be reviewed: units, units with pending points, pending total (`detail: true` lists the units). Platform-wide, read only. |
| `epc_project_status` | full, readonly | Workflow state, `master_project_state`, review files and last audit events. |
| `epc_project_init` | full | Create a project from the guided-form answers (D24 data required). |
| `epc_pipeline_run` | full | Run the pipeline (`stop_after`, `run_id`, `detail`, `from_stage` or `resume`, `mode`: `production` by default or `edit`, ADR-0035). |
| `epc_project_review` | full | Record corrections (workflow transition plus a file under `reviews/`); never edits `ssot/`. |
| `epc_project_approve` | full | Workflow `approve` (engineer of record; D21 guard, `sign` permission). |
| `epc_project_issue` | full | Workflow `issue`; refused by D21 while a norm value is not verified. |

The write tools exist only in the `full` profile (`EPC_MCP_PROFILE=readonly` hides them). The server acts as one RACI role (`EPC_ACTOR_ROLE`, `EPC_ACTOR_ID`; default `orchestrator` / `mcp`): the platform checks every call against it and logs allowed and denied decisions in the project's `audit/events.jsonl`.

The pipeline tools need `harness/src`, `harness/src/platform` and the engine `src` folders on `PYTHONPATH`. Tests: `harness/tests/unit/test_mcp_parity.py` (in the gate's `harness-tests`) and `tests/` here (protocol, registry and guard tests; they need no backend; not in the gate).
