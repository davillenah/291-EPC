# `_template`

Status: **planned**

Empty project skeleton copied by `/init`; holds no client data.

`ProjectStore.init_from_template()` (`harness/src/disciplines/electrical_lv/store.py`) copies this structure into a new, empty project folder (READMEs are not copied). Visible to the user: `inputs/` (immutable and hashed after intake) and `deliverables/<rev>/`. Everything the harness keeps for itself lives in the hidden folder `.epc/` (a leading dot hides it on macOS and Linux; `init_from_template` also sets the hidden attribute on Windows): `project_profile.json` and `master_project_state.json` (status `template`, nulls allowed; schemas in `harness/schemas`), `epc-progress.txt`, `ssot/` (written only by the pipeline), `runs/<pipeline_run_id>/`, `reviews/` and `audit/`. Nothing is ever written in this folder by the code.
