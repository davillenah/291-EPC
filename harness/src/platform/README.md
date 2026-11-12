# `platform`

Status: **in development**

The platform layer: workflow, permissions, audit, event log (MIG-33a), then the MCP server (`mcp/`, its own package `epc_mcp`) and the `epc` CLI (`cli/`, planned).

**Import layout.** A directory named `platform` cannot be an importable package: it would shadow the standard library module `platform` (which `uuid`, `subprocess` and others import). So there is no `__init__.py` here. The code of workflow, permissions, audit and events is ONE package, `epc_platform`, at `harness/src/platform/epc_platform/` (subpackages `workflow`, `permissions`, `audit`, `events`; `cli` follows in MIG-33c). Tests and the gate put `harness/src/platform` on `PYTHONPATH`; the MCP package keeps its own layout (`mcp/src/epc_mcp`). The folders `workflow/`, `permissions/`, `audit/`, `events/` and `cli/` stay as the PRD tree names them and each README points to the code.
