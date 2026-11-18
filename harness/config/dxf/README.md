# Editable DXF look (`harness/config/dxf/`)

Open these files with any text editor, change a value, save. The next DXF the harness writes uses it. **DXF files already written are not touched: generate them again.**

| File | What you can change |
|---|---|
| `layers.json` | Layer names (`"name"`), colour (`"color"`, AutoCAD 1-255), line weight, line type, on/frozen/locked/plot, per role. Example: `"plan.ELEC-BANDEJA"` is the tray layer. |
| `text.json` → `font` | Typeface file (`regular`, `bold`, e.g. `arial.ttf`) and the names of the text styles. |
| `text.json` → `heights` | Text heights: `plan_text_m` (plans, in metres of the plan), `titleblock_mm`, `legal_notice_mm`, `diagram_text_mm`, `frame_text_mm` (single-line and multi-line diagrams, in mm on the sheet). |
| `text.json` → `trays` | `as_block`: true draws each tray with its text as one block (`TRAY_<tag>`); false leaves them loose. `kinds`: which line kinds are drawn so (`BN` = tray). `block_prefix`: block name prefix. |
| `unify.json` | The final names of the layers in a transmittal (`ELEC-BANDEJA` becomes `E-TRAY`...) and the English word of each electrical element. The typeface of the final step comes from `text.json`. |

A file may carry only the fields you change (the rest keeps its default). The files here are the only copy of these values (the code has none). Another folder can be used with the environment variable `EPC_DXF_CONFIG_DIR`; the MASTER's global layer file (`EPC_LAYERS_JSON`) and the company/project files still win over this folder.
