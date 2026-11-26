# Dependencias e impacto

> Archivo generado por `python harness/tools/build/impact_map.py` a partir del código (importaciones y referencias a módulos del motor). No se edita a mano: el gate avisa si quedó desactualizado.

Cómo leerlo: **Usa** = de qué depende la unidad; **Lo usan** = quién se rompe o cambia si esta unidad cambia; **Impacto** = todo lo que alcanza, directa o indirectamente.

## Motores

| Unidad | Usa | Lo usan | Impacto si la modificas |
|---|---|---|---|
| `aea90364` | `calc_common`, `feeder_sizing`, `grounding`, `load_balance`, `selectivity`, `short_circuit`, `voltage_drop` | `calc_check`, `calc_common`, `draw`, `drawing`, `feeder_sizing`, `grounding`, `lighting`, `load_balance`, `selectivity`, `short_circuit`, `voltage_drop` | `arch`, `boq`, `calc_check`, `calc_common`, `design_basis`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `lighting`, `load_balance`, `mld`, `plan`, `report`, `rfq`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `transformer_sizing`, `voltage_drop` |
| `arch` | `draw` | `draw` | `boq`, `draw`, `drawing`, `dxf`, `mld`, `plan`, `report`, `rfq`, `sld`, `symbols`, `titleblock` |
| `arrays` | — | — | — |
| `boq` | `plan`, `pv` | `rfq` | `rfq` |
| `calc_check` | `aea90364` | — | — |
| `calc_common` | `aea90364` | `aea90364`, `feeder_sizing`, `grounding`, `load_balance`, `selectivity`, `short_circuit`, `voltage_drop` | `aea90364`, `arch`, `boq`, `calc_check`, `design_basis`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `lighting`, `load_balance`, `mld`, `plan`, `report`, `rfq`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `transformer_sizing`, `voltage_drop` |
| `changes` | — | — | — |
| `cutlist` | — | — | — |
| `datasheets` | — | `rfq` | `rfq` |
| `descriptive_report` | — | — | — |
| `design_basis` | `grounding`, `load_balance`, `short_circuit`, `voltage_drop` | — | — |
| `dims` | — | — | — |
| `documents` | — | — | — |
| `draw` | `aea90364`, `arch`, `drawing`, `dxf`, `plan`, `pv`, `symbols`, `titleblock` | `arch`, `drawing`, `dxf`, `mld`, `plan`, `report`, `sld`, `symbols`, `titleblock` | `arch`, `boq`, `drawing`, `dxf`, `mld`, `plan`, `report`, `rfq`, `sld`, `symbols`, `titleblock` |
| `drawing` | `aea90364`, `draw`, `dxf`, `mld`, `report`, `sld`, `symbols`, `titleblock` | `draw` | `arch`, `boq`, `draw`, `dxf`, `mld`, `plan`, `report`, `rfq`, `sld`, `symbols`, `titleblock` |
| `dxf` | `draw` | `draw`, `drawing` | `arch`, `boq`, `draw`, `drawing`, `mld`, `plan`, `report`, `rfq`, `sld`, `symbols`, `titleblock` |
| `expr` | — | — | — |
| `feeder_sizing` | `aea90364`, `calc_common`, `voltage_drop` | `aea90364`, `grounding`, `short_circuit` | `aea90364`, `arch`, `boq`, `calc_check`, `calc_common`, `design_basis`, `draw`, `drawing`, `dxf`, `grounding`, `lighting`, `load_balance`, `mld`, `plan`, `report`, `rfq`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `transformer_sizing`, `voltage_drop` |
| `grounding` | `aea90364`, `calc_common`, `feeder_sizing` | `aea90364`, `design_basis`, `selectivity` | `aea90364`, `arch`, `boq`, `calc_check`, `calc_common`, `design_basis`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `lighting`, `load_balance`, `mld`, `plan`, `report`, `rfq`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `transformer_sizing`, `voltage_drop` |
| `hvac` | — | — | — |
| `lighting` | `aea90364` | — | — |
| `load_balance` | `aea90364`, `calc_common` | `aea90364`, `design_basis`, `selectivity` | `aea90364`, `arch`, `boq`, `calc_check`, `calc_common`, `design_basis`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `lighting`, `mld`, `plan`, `report`, `rfq`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `transformer_sizing`, `voltage_drop` |
| `mld` | `draw` | `drawing` | `arch`, `boq`, `draw`, `drawing`, `dxf`, `plan`, `report`, `rfq`, `sld`, `symbols`, `titleblock` |
| `plan` | `draw` | `boq`, `draw` | `arch`, `boq`, `draw`, `drawing`, `dxf`, `mld`, `report`, `rfq`, `sld`, `symbols`, `titleblock` |
| `pv` | — | `boq`, `draw`, `report` | `arch`, `boq`, `draw`, `drawing`, `dxf`, `mld`, `plan`, `report`, `rfq`, `sld`, `symbols`, `titleblock` |
| `receptacles` | — | — | — |
| `report` | `draw`, `pv` | `drawing` | `arch`, `boq`, `draw`, `drawing`, `dxf`, `mld`, `plan`, `rfq`, `sld`, `symbols`, `titleblock` |
| `rfq` | `boq`, `datasheets` | — | — |
| `rules` | — | — | — |
| `select` | — | — | — |
| `selectivity` | `aea90364`, `calc_common`, `grounding`, `load_balance` | `aea90364` | `aea90364`, `arch`, `boq`, `calc_check`, `calc_common`, `design_basis`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `lighting`, `load_balance`, `mld`, `plan`, `report`, `rfq`, `short_circuit`, `sld`, `symbols`, `titleblock`, `transformer_sizing`, `voltage_drop` |
| `short_circuit` | `aea90364`, `calc_common`, `feeder_sizing` | `aea90364`, `design_basis`, `transformer_sizing` | `aea90364`, `arch`, `boq`, `calc_check`, `calc_common`, `design_basis`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `lighting`, `load_balance`, `mld`, `plan`, `report`, `rfq`, `selectivity`, `sld`, `symbols`, `titleblock`, `transformer_sizing`, `voltage_drop` |
| `sld` | `draw` | `drawing` | `arch`, `boq`, `draw`, `drawing`, `dxf`, `mld`, `plan`, `report`, `rfq`, `symbols`, `titleblock` |
| `standards` | — | — | — |
| `symbols` | `draw` | `draw`, `drawing` | `arch`, `boq`, `draw`, `drawing`, `dxf`, `mld`, `plan`, `report`, `rfq`, `sld`, `titleblock` |
| `terminal_blocks` | — | — | — |
| `titleblock` | `draw` | `draw`, `drawing` | `arch`, `boq`, `draw`, `drawing`, `dxf`, `mld`, `plan`, `report`, `rfq`, `sld`, `symbols` |
| `transformer_sizing` | `short_circuit` | — | — |
| `voltage_drop` | `aea90364`, `calc_common` | `aea90364`, `design_basis`, `feeder_sizing` | `aea90364`, `arch`, `boq`, `calc_check`, `calc_common`, `design_basis`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `lighting`, `load_balance`, `mld`, `plan`, `report`, `rfq`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `transformer_sizing` |
| `walls` | — | — | — |

## Módulos del backend

| Módulo | Usa | Lo usan |
|---|---|---|

## Paquetes externos por unidad del motor

Lo declarado en `pyproject.toml` frente a lo que el código importa de verdad.

| Unidad | Importa | Declarado | Falta declarar |
|---|---|---|---|
| `aea90364` | `openpyxl` | `openpyxl` | — |
| `arch` | — | `epc-draw` | — |
| `arrays` | — | — | — |
| `boq` | — | — | — |
| `calc_check` | — | `epc-aea90364` | — |
| `calc_common` | — | — | — |
| `changes` | — | — | — |
| `cutlist` | — | — | — |
| `datasheets` | — | — | — |
| `descriptive_report` | — | — | — |
| `design_basis` | — | — | — |
| `dims` | — | — | — |
| `documents` | `playwright`, `pypdf`, `python-docx` | `playwright`, `pypdf`, `python-docx` | — |
| `draw` | `cairosvg`, `engines`, `ezdxf`, `lxml`, `numpy`, `openpyxl`, `pillow`, `pypdfium2`, `shapely`, `svgelements`, `vtracer` | `cairosvg`, `epc-aea90364`, `ezdxf`, `lxml`, `numpy`, `openpyxl`, `pillow`, `pypdfium2`, `shapely`, `svgelements`, `vtracer` | `engines` |
| `drawing` | `ezdxf`, `matplotlib`, `openpyxl` | `epc-aea90364`, `epc-draw`, `epc-mld`, `epc-sld`, `epc-titleblock`, `ezdxf`, `matplotlib`, `numpy`, `openpyxl`, `pillow`, `svgelements` | — |
| `dxf` | — | `ezdxf`, `lxml`, `shapely`, `svgelements`, `vtracer` | — |
| `expr` | — | — | — |
| `feeder_sizing` | — | `epc-calc-common`, `epc-voltage-drop` | — |
| `grounding` | — | `epc-calc-common`, `epc-feeder-sizing` | — |
| `hvac` | — | — | — |
| `lighting` | `engines` | — | `engines` |
| `load_balance` | — | `epc-calc-common` | — |
| `mld` | — | `epc-draw` | — |
| `plan` | — | `epc-draw` | — |
| `pv` | `timezonefinder` | `timezonefinder` | — |
| `receptacles` | — | — | — |
| `report` | `matplotlib`, `numpy`, `openpyxl`, `pillow`, `svgelements` | `matplotlib`, `numpy`, `openpyxl`, `pillow`, `svgelements` | — |
| `rfq` | — | — | — |
| `rules` | `engines` | — | `engines` |
| `select` | — | — | — |
| `selectivity` | — | `epc-calc-common`, `epc-grounding`, `epc-load-balance` | — |
| `short_circuit` | — | `epc-calc-common`, `epc-feeder-sizing` | — |
| `sld` | — | `epc-draw` | — |
| `standards` | `engines`, `jsonschema`, `pypdf`, `pypdfium2` | `jsonschema`, `pillow`, `pypdf`, `pypdfium2` | `engines` |
| `symbols` | — | `epc-draw` | — |
| `terminal_blocks` | — | — | — |
| `titleblock` | — | `epc-draw` | — |
| `transformer_sizing` | — | `epc-short-circuit` | — |
| `voltage_drop` | — | `epc-calc-common` | — |
| `walls` | — | — | — |

## Plugins

| Plugin | Empaqueta (motor) | Requiere (plugins) | Lo requieren |
|---|---|---|---|
| `aea-calc` | `aea90364`, `calc_common`, `feeder_sizing`, `grounding`, `load_balance`, `selectivity`, `short_circuit`, `voltage_drop` | — | `board-design` |
| `board-design` | `aea90364`, `arch`, `calc_common`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `load_balance`, `mld`, `plan`, `pv`, `report`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `voltage_drop` | `aea-calc`, `dxf-output`, `iec-symbols`, `iram-titleblock`, `mld`, `sld` | — |
| `doc-quality` | `documents` | — | `pm2-docs`, `spec-writer` |
| `dxf-output` | `aea90364`, `arch`, `calc_common`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `load_balance`, `mld`, `plan`, `pv`, `report`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `voltage_drop` | — | `board-design` |
| `equipment-catalog` | — | — | `procurement` |
| `iec-symbols` | `aea90364`, `arch`, `calc_common`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `load_balance`, `mld`, `plan`, `pv`, `report`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `voltage_drop` | — | `board-design` |
| `intake-analysis` | — | — | — |
| `iram-titleblock` | `aea90364`, `arch`, `calc_common`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `load_balance`, `mld`, `plan`, `pv`, `report`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `voltage_drop` | — | `board-design` |
| `mld` | `aea90364`, `arch`, `calc_common`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `load_balance`, `mld`, `plan`, `pv`, `report`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `voltage_drop` | — | `board-design` |
| `plan-drawing` | `aea90364`, `arch`, `calc_common`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `load_balance`, `mld`, `plan`, `pv`, `report`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `voltage_drop` | — | — |
| `pm2-docs` | `documents` | `doc-quality` | — |
| `procurement` | — | `equipment-catalog` | — |
| `sld` | `aea90364`, `arch`, `calc_common`, `draw`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `load_balance`, `mld`, `plan`, `pv`, `report`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `voltage_drop` | — | `board-design` |
| `spec-writer` | `documents` | `doc-quality` | — |
| `standard-ingest` | `rules`, `standards` | — | — |
