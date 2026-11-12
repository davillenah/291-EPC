# `epc_platform`

Status: **in development**

The one importable package of the platform layer. `harness/src/platform/` itself cannot be a package: a package named `platform` would shadow the standard library module of that name. Put `harness/src/platform` on `PYTHONPATH` and import `epc_platform.<name>`.

| Subpackage | What it holds |
| --- | --- |
| `events` | Append-only, hash-chained event log (`projects/<code>/audit/events.jsonl`). |
| `permissions` | The RACI (PRD 5, 14.4) as data, path classification, `check` / `enforce`. |
| `audit` | `AuditTrail`: run ids, recording, summaries. |
| `workflow` | The project lifecycle state machine and its guards (including D21). |
| `api` | The transport-independent function layer (MIG-33b): `init_project`, `run_pipeline`, `status`, `review`, `approve`, `issue` and the read-only engine queries `list_engines`, `engine_info`, `norm_records`, `stage_table`. Plain functions over JSON dicts returning `{ok, data, warnings}` or `{ok: false, error}`; each checks the RACI with `permissions.enforce` and logs the decision; writes only through `ProjectStore`. The MCP server and the CLI call these functions (parity tested). |

`cli` (MIG-33c) is the `epc` command line over `epc_platform.api` (see `harness/src/platform/cli/README.md`); `cli/main.py` holds the only read of the system clock in the platform (`utc_now`), every api function receives the clock as a parameter. Imports allowed: the standard library, `epc_platform.*`, `disciplines.*` and engine packages `epc_*`. `disciplines` never imports `epc_platform` (architecture test).
