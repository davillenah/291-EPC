# `disciplines`

Status: **in development**

One folder per engineering discipline. Each discipline is a plugin of the platform: it brings its own engines, norms, stages and lead agent and shares the core (SSOT store, permissions, event log, MCP, CLI).

| Discipline | Status | Lead agent |
|---|---|---|
| `electrical_lv` | in development (12-stage pipeline) | `electrical_lv` |
| `electrical_mv` | planned | (none yet) |
| `civil_structural` | planned | `civil_structural_lead` |
| `mechanical` | planned | `mechanical_lead` |
| `hvac` | planned | `hvac_lead` |
| `piping_plumbing` | planned | `piping_plumbing_lead` |
| `fire_protection` | planned | `fire_protection_lead` |
| `instrumentation_control` | planned | `instrumentation_control_lead` |
| `telecommunications` | planned | `telecommunications_lead` |

## Discipline contract

A discipline folder holds a README (scope, status, lead agent, reference standards) and, later, its stages, its engines registered under `harness/src/engines/`, its norm records under `harness/config/normative/<country>/<discipline>/` (every value `pending review` until the owner approves it), and a README. Cross-discipline coordination is done by the `multidisciplinary_orchestrator`. The generic pipeline core will be extracted from `electrical_lv` when a second discipline gets its first engine.
