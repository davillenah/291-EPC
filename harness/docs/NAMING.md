# File and folder names

One rule per kind of file, so that no folder shows an `X_Y` next to an `X-Y`. `python harness/tools/ci/check_file_names.py` enforces it in the gate (`file-names`).

| Kind | Rule | Example |
|---|---|---|
| Code and data (`.py .json .jsonl .toml .yml .ps1 .txt .xlsx .dxf .svg .png`) | lower `snake_case`, no `-`, no capitals | `epc_progress.txt`, `document_catalog.json` |
| Schemas | `<name>.schema.json`, name in snake_case | `norm_register.schema.json` |
| Folders and engine packages | lower `snake_case` (`epc_<area>`) | `epc_walls` |
| Documents of a project (issued) | `<code>_<description>.<ext>` (`harness/src/disciplines/electrical_lv/naming.py`) | `2026-ES-HNDA-3085-E-LV-SLD-001_general_diagram` |
| Coded symbol library | `<project>_<disc>_<sub>_<type>_<standard>_<name>` (`library/`) | `291_E_LV_SLD_IEC60617_acb.dxf` |
| Fixed names | `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `ADR-NNNN-<slug>.md`, dot files | |
| Markdown guides | `UPPER_SNAKE.md` for top-level guides of `harness/docs`; no mixing of `-` and `_` inside one folder | `ENGINE_CONTRACTS.md` |

Rules the check applies: (1) a code or data file is lower snake_case; (2) a folder never mixes `-` and `_` in its file names. Existing offenders are listed in `harness/tools/ci/file_names_legacy.json`; the list can only shrink, so a new file must comply, and a fixed file must be removed from the list (`--update`). Existing Spanish identifiers are not renamed. Skill and agent file names follow the Claude layer (`name` of the skill or agent).
