# ADR-0035: Run modes, production and edit

Status: accepted. Date: 2026-11-14. Requested by the owner: to check the whole system end to end (up to approve and issue) while the norm values are still `pending review`. Follows D21 (a package is never approved for construction while it uses a norm record that is not verified), ADR-0011 (norm review) and ADR-0034 (the harness).

## Context
D21 keeps a package a draft and blocks `approve` and `issue` while any norm record listed in its manifests is not `verified`. Until the owner verifies the values (NORM-01) no package can reach approve or issue, so the end of the workflow cannot be tested.

## Decisions
1. **Two modes of a run: `production` (the default) and `edit`.** Chosen per run (`epc run --mode production|edit`, API `run_pipeline(mode=...)`, MCP `epc_pipeline_run` argument `mode`). The run records the mode in the project (`.epc/reviews/mode.json`, written only when it is not the production default) and in the signatures of its inputs.
2. **`production` is the behaviour of always.** Nothing in a production run, answer, manifest or file changes: no `mode` key, no mode file, the same bytes. D21 is untouched.
3. **`edit` changes how the workflow reacts to records that are not verified, and nothing else.** The manifests made in edit mode carry `mode: "edit"`; while the project is in edit mode and every manifest in force is an edit one, the D21 guard of `approve` and `issue` is not applied (the event log says so) and their answer carries a notice. The stage 12 message, a note finding, the footer of every rendered report, the transmittal cover and the manifest say "EDIT MODE: norm values not verified, not for production". The records are never changed or marked verified, the manifest status stays `draft` (the schema still forbids `approved_for_construction` with records not verified), and nothing is signed: the signature is a human act.
4. **An edit package is not for production.** A production run does not take over the transmittal of a revision made in edit mode (it needs a new revision), and a project in edit mode whose manifest in force is a production one keeps the D21 guard.
5. **The default mode depends on the branch.** Without `--mode` the default is, in order: the environment variable `EPC_RUN_MODE`, the single versioned file `harness/config/default_run_mode` (`production` or `edit`), and `production` when the file is missing or wrong. The file says `edit` on `dev` (the system is built and checked in edit mode) and `production` on `main`. An explicit `--mode` always wins. The gate check `default-run-mode` (`tools/ci/check_default_run_mode.py`) fails when the file says `edit` on the branch `main`, with `EPC_RELEASE=1` (a release check) or in the CI of a pull request to `main`; `tools/build/set_default_run_mode.py production|edit` is the promotion step (see `docs/BRANCHING.md`). The test suite pins `EPC_RUN_MODE=production` (`tests/conftest.py`), so it checks the strict behaviour on both branches.
6. **Where it does not reach.** The DXF drawings carry no mark (the manifest and the transmittal do). The norm review, the norm register and the rules of the standards stay as they are.

## Consequences
The workflow can be exercised to `issued` with unverified norms, and what it produces says it must not be built from. Production needs the owner's NORM-01 review as before.
