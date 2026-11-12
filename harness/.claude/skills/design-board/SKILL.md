---
name: "design-board"
description: "Designs a low-voltage board end to end: runs the circuit calculation under the project's design criteria and draws the single-line (SLD) and multi-line (MLD) diagrams from it, with memo and summary."
---

# design-board

Owner plugin: `board-design`. Thin wrapper over `python -m epc_drawing.board_design` (code in `harness/src/engines/cad/drawing`); use the project venv. All numbers come from the engine (`epc_aea90364.aea_pipeline`), never from the model.

## Hard rules
1. **Never invent data.** Loads, circuits and criteria come from the project's saved data. If one is missing, ask for it; do not assume a value.
2. **One source of truth.** The diagrams are drawn from the stored calculation; do not edit outputs by hand.
3. **Criteria govern the calculation** (voltage-drop limits, minimum sections, conductor material and insulation, RCD sensitivity). Report any criterion value marked unreviewed.
4. **`.svg` is internal only.** Deliverables are `.dxf` and `.pdf`.

## Run
```
python -m epc_drawing.board_design --project <project folder> --out <work folder> --name <BOARD-ID> --diagrams sld,mld
```
- Explicit files instead of a project: `--input board.json --criteria criteria.json`.
- Logos: `--logo provider=FILE` and `--logo client=FILE`.
- `--diagrams none` gives the calculation, memo and summary only; `--diagrams calc` gives the calculation alone.

## Steps
1. Confirm the board, its circuits and the design criteria exist for the project.
2. Run the command above into a work folder.
3. Read the calculation output and list every circuit that fails a criterion.
4. Report the produced files (calculation, SLD, MLD, memo, summary) and any finding, in the user's language.
