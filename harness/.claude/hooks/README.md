# `hooks`

Status: **in development**

Hooks of the product Claude layer, wired in [`../settings.json`](../settings.json).

| File | What it does |
|---|---|
| `guard_paths.py` | PreToolUse guard (PRD 14.4). Blocks (exit code 2, one line on stderr with the rule id) any write to `ssot/`, `deliverables/`, `inputs/`, `audit/`, `config/normative/`, `schemas/`, any delete, any git write and any shell redirection or copy into those paths. It fails closed. |

The rules are not copied: paths are classified and decided with `epc_platform.permissions` (matrix D-01..D-10, A-01..A-08).

## Usage

```
echo {"tool_name":"Write","tool_input":{"file_path":"projects/p1/ssot/x.json"}} | python harness/.claude/hooks/guard_paths.py
```

| Environment variable | Meaning |
|---|---|
| `EPC_ACTOR_ROLE` | Role of the actor (default `orchestrator`). An unknown role is blocked on writes. |
| `EPC_PROJECT_DIR` | When set, every block is appended as a `denied` event to that project's audit log. |
| `EPC_HOOK_NOW` | Timestamp text for that event (the hook reads no clock; default `-`). |
| `EPC_RUN_ID`, `EPC_ACTOR_ID` | Optional run and actor ids for the audit event. |

Not enforced by the hook: `runs/` (the pipeline's folder) and harness code (reviewed through CODEOWNERS). Tests: `harness/tests/architecture/test_guard_hook.py`, `test_settings_consistency.py`.
