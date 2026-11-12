# `_template`

Status: **planned**

Empty project skeleton copied by `/init`; holds no client data.

`ProjectStore.init_from_template()` (`harness/src/disciplines/electrical_lv/store.py`) copies this structure into a new, empty project folder (READMEs are not copied). Files: `project_profile.json` and `master_project_state.json` (status `template`, nulls allowed; schemas in `harness/schemas`), `epc-progress.txt`; folders: `inputs/` (immutable and hashed after intake), `ssot/` (written only by the pipeline), `runs/<pipeline_run_id>/`, `deliverables/<rev>/`, `reviews/`, `transmittals/`, `audit/`. Nothing is ever written in this folder by the code.
