# `cli`

Status: **in development**

The `epc` command line. The code is the package `epc_platform.cli` (`harness/src/platform/epc_platform/cli/`: `main.py`, `commands.py`, `render.py`); this folder only documents it, because `harness/src/platform/` is not a package. The CLI calls the same `epc_platform.api` functions as the MCP server (PRD 14.5); it parses arguments, reads the JSON files you name, calls the api and renders the answer. It computes nothing and writes no file itself.

## Running it

Put `harness/src`, `harness/src/platform` and the `src` folder of every engine (`harness/src/engines/*/*/src`) on `PYTHONPATH`, then:

```
python -m epc_platform.cli <command> [options]
```

## Commands

| Command | Api function | MCP tool |
| --- | --- | --- |
| `epc init <project> --answers FILE.json` | `init_project` | `epc_project_init` |
| `epc run <project> --loads FILE.json [--engine-inputs FILE.json] [--stop-after N] [--run-id ID] [--revision R0] [--detail]` | `run_pipeline` | `epc_pipeline_run` |
| `epc status <project>` | `status` | `epc_project_status` |
| `epc review <project> --corrections FILE.json` | `review` | `epc_project_review` |
| `epc approve <project>` | `approve` | `epc_project_approve` |
| `epc issue <project>` | `issue` | `epc_project_issue` |
| `epc engines list [--project CODE]` | `list_engines` | `epc_engine_list` |
| `epc engines info <name> [--project CODE]` | `engine_info` | `epc_engine_info` |
| `epc norms [package] [--project CODE]` | `norm_records` | `epc_norm_records` |
| `epc norms-pending [--detail] [--project CODE]` | `norms_pending` | `epc_norms_pending` |
| `epc stages [--project CODE]` | `stage_table` | `epc_stage_table` |

Global options (before or after the command): `--projects-root DIR` (env `EPC_PROJECTS_ROOT`; default `projects` in the repository root), `--actor-role ROLE` (env `EPC_ACTOR_ROLE`; default `orchestrator`), `--actor-id ID` (env `EPC_ACTOR_ID`; default `cli`), `--json` (print the api envelope as canonical JSON). The platform checks the RACI for the chosen role on every call and logs allowed and denied decisions in the project's `audit/events.jsonl`.

Exit codes: `0` ok, `1` the api answered with an error (permission denied, blocked by D21, bad state, unreadable file...), `2` usage error.

## Examples

```
python -m epc_platform.cli stages
python -m epc_platform.cli engines info sld
python -m epc_platform.cli init DEMO-1 --answers answers.json
python -m epc_platform.cli run DEMO-1 --loads loads.json --engine-inputs inputs.json --stop-after 5
python -m epc_platform.cli status DEMO-1 --json
python -m epc_platform.cli review DEMO-1 --corrections corrections.json --actor-role engineer_of_record --actor-id jdoe
python -m epc_platform.cli approve DEMO-1 --actor-role engineer_of_record --actor-id jdoe
```

`approve` and `issue` are refused (`blocked_d21`) while a norm record listed in the manifests is not verified. The CLI never changes a review state.

Tests: `harness/tests/unit/test_cli.py`, `test_cli_parity.py` (CLI = MCP = direct api) and `harness/tests/architecture/test_platform_clock.py`.
