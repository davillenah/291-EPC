# Dependencias e impacto

> Archivo generado por `python harness/tools/build/impact_map.py` a partir del código (importaciones y referencias a módulos del motor). No se edita a mano: el gate avisa si quedó desactualizado.

Cómo leerlo: **Usa** = de qué depende la unidad; **Lo usan** = quién se rompe o cambia si esta unidad cambia; **Impacto** = todo lo que alcanza, directa o indirectamente.

## Motores

| Unidad | Usa | Lo usan | Impacto si la modificas |
|---|---|---|---|
| `aea90364` | `calc_common`, `feeder_sizing`, `grounding`, `load_balance`, `selectivity`, `short_circuit`, `voltage_drop` | `calc_check`, `calc_common`, `drawing`, `feeder_sizing`, `grounding`, `lighting`, `load_balance`, `mld`, `selectivity`, `short_circuit`, `sld`, `voltage_drop` | `calc_check`, `calc_common`, `design_basis`, `drawing`, `feeder_sizing`, `grounding`, `lighting`, `load_balance`, `mld`, `selectivity`, `short_circuit`, `sld`, `transformer_sizing`, `voltage_drop` |
| `arch` | `titleblock` | — | — |
| `boq` | — | `rfq` | `rfq` |
| `calc_check` | `aea90364` | — | — |
| `calc_common` | `aea90364` | `aea90364`, `feeder_sizing`, `grounding`, `load_balance`, `selectivity`, `short_circuit`, `voltage_drop` | `aea90364`, `calc_check`, `design_basis`, `drawing`, `feeder_sizing`, `grounding`, `lighting`, `load_balance`, `mld`, `selectivity`, `short_circuit`, `sld`, `transformer_sizing`, `voltage_drop` |
| `datasheets` | — | `rfq` | `rfq` |
| `descriptive_report` | — | — | — |
| `design_basis` | `grounding`, `load_balance`, `short_circuit`, `voltage_drop` | — | — |
| `documents` | — | — | — |
| `drawing` | `aea90364`, `dxf`, `mld`, `sld`, `titleblock` | — | — |
| `dxf` | — | `drawing`, `mld`, `plan`, `sld`, `titleblock` | `arch`, `drawing`, `mld`, `plan`, `sld`, `titleblock` |
| `feeder_sizing` | `aea90364`, `calc_common`, `voltage_drop` | `aea90364`, `grounding`, `short_circuit` | `aea90364`, `calc_check`, `calc_common`, `design_basis`, `drawing`, `grounding`, `lighting`, `load_balance`, `mld`, `selectivity`, `short_circuit`, `sld`, `transformer_sizing`, `voltage_drop` |
| `grounding` | `aea90364`, `calc_common`, `feeder_sizing` | `aea90364`, `design_basis`, `selectivity` | `aea90364`, `calc_check`, `calc_common`, `design_basis`, `drawing`, `feeder_sizing`, `lighting`, `load_balance`, `mld`, `selectivity`, `short_circuit`, `sld`, `transformer_sizing`, `voltage_drop` |
| `hvac` | — | — | — |
| `lighting` | `aea90364` | — | — |
| `load_balance` | `aea90364`, `calc_common` | `aea90364`, `design_basis`, `selectivity` | `aea90364`, `calc_check`, `calc_common`, `design_basis`, `drawing`, `feeder_sizing`, `grounding`, `lighting`, `mld`, `selectivity`, `short_circuit`, `sld`, `transformer_sizing`, `voltage_drop` |
| `mld` | `aea90364`, `dxf`, `symbols`, `titleblock` | `drawing` | `drawing` |
| `plan` | `dxf` | — | — |
| `pv` | — | — | — |
| `receptacles` | — | — | — |
| `rfq` | `boq`, `datasheets` | — | — |
| `rules` | — | — | — |
| `selectivity` | `aea90364`, `calc_common`, `grounding`, `load_balance` | `aea90364` | `aea90364`, `calc_check`, `calc_common`, `design_basis`, `drawing`, `feeder_sizing`, `grounding`, `lighting`, `load_balance`, `mld`, `short_circuit`, `sld`, `transformer_sizing`, `voltage_drop` |
| `short_circuit` | `aea90364`, `calc_common`, `feeder_sizing` | `aea90364`, `design_basis`, `transformer_sizing` | `aea90364`, `calc_check`, `calc_common`, `design_basis`, `drawing`, `feeder_sizing`, `grounding`, `lighting`, `load_balance`, `mld`, `selectivity`, `sld`, `transformer_sizing`, `voltage_drop` |
| `sld` | `aea90364`, `dxf`, `symbols`, `titleblock` | `drawing` | `drawing` |
| `standards` | — | — | — |
| `symbols` | — | `mld`, `sld` | `drawing`, `mld`, `sld` |
| `terminal_blocks` | — | — | — |
| `titleblock` | `dxf` | `arch`, `drawing`, `mld`, `sld` | `arch`, `drawing`, `mld`, `sld` |
| `transformer_sizing` | `short_circuit` | — | — |
| `voltage_drop` | `aea90364`, `calc_common` | `aea90364`, `design_basis`, `feeder_sizing` | `aea90364`, `calc_check`, `calc_common`, `design_basis`, `drawing`, `feeder_sizing`, `grounding`, `lighting`, `load_balance`, `mld`, `selectivity`, `short_circuit`, `sld`, `transformer_sizing` |

## Módulos del backend

| Módulo | Usa | Lo usan |
|---|---|---|

## Paquetes externos por unidad del motor

Lo declarado en `pyproject.toml` frente a lo que el código importa de verdad.

| Unidad | Importa | Declarado | Falta declarar |
|---|---|---|---|
| `aea90364` | `openpyxl` | `openpyxl` | — |
| `arch` | `ezdxf`, `numpy`, `pillow`, `pypdfium2` | `ezdxf`, `numpy`, `pillow`, `pypdfium2` | — |
| `boq` | — | — | — |
| `calc_check` | — | `epc-aea90364` | — |
| `calc_common` | — | — | — |
| `datasheets` | — | — | — |
| `descriptive_report` | — | — | — |
| `design_basis` | — | — | — |
| `documents` | `playwright`, `pypdf`, `python-docx` | `playwright`, `pypdf`, `python-docx` | — |
| `drawing` | `ezdxf`, `matplotlib`, `numpy`, `openpyxl`, `pillow`, `svgelements` | `epc-aea90364`, `epc-mld`, `epc-sld`, `epc-titleblock`, `ezdxf`, `matplotlib`, `numpy`, `openpyxl`, `pillow`, `svgelements` | — |
| `dxf` | `ezdxf`, `lxml`, `shapely`, `svgelements`, `vtracer` | `ezdxf`, `lxml`, `shapely`, `svgelements`, `vtracer` | — |
| `feeder_sizing` | — | `epc-calc-common`, `epc-voltage-drop` | — |
| `grounding` | — | `epc-calc-common`, `epc-feeder-sizing` | — |
| `hvac` | — | — | — |
| `lighting` | `engines` | — | `engines` |
| `load_balance` | — | `epc-calc-common` | — |
| `mld` | `lxml` | `epc-aea90364`, `epc-dxf`, `epc-symbols`, `epc-titleblock`, `lxml` | — |
| `plan` | `ezdxf` | `epc-dxf`, `ezdxf` | — |
| `pv` | — | — | — |
| `receptacles` | — | — | — |
| `rfq` | — | — | — |
| `rules` | `engines` | — | `engines` |
| `selectivity` | — | `epc-calc-common`, `epc-grounding`, `epc-load-balance` | — |
| `short_circuit` | — | `epc-calc-common`, `epc-feeder-sizing` | — |
| `sld` | `cairosvg`, `lxml`, `openpyxl` | `cairosvg`, `epc-aea90364`, `epc-dxf`, `epc-symbols`, `epc-titleblock`, `lxml`, `openpyxl` | — |
| `standards` | `engines`, `jsonschema`, `pypdf`, `pypdfium2` | `jsonschema`, `pillow`, `pypdf`, `pypdfium2` | `engines` |
| `symbols` | — | — | — |
| `terminal_blocks` | — | — | — |
| `titleblock` | — | `epc-dxf` | — |
| `transformer_sizing` | — | `epc-short-circuit` | — |
| `voltage_drop` | — | `epc-calc-common` | — |

## Plugins

| Plugin | Empaqueta (motor) | Requiere (plugins) | Lo requieren |
|---|---|---|---|
| `aea-calc` | `aea90364`, `calc_common`, `feeder_sizing`, `grounding`, `load_balance`, `selectivity`, `short_circuit`, `voltage_drop` | — | `board-design`, `mld`, `sld` |
| `board-design` | `aea90364`, `calc_common`, `drawing`, `dxf`, `feeder_sizing`, `grounding`, `load_balance`, `mld`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `voltage_drop` | `aea-calc`, `dxf-output`, `iram-titleblock`, `mld`, `sld` | — |
| `doc-quality` | `documents` | — | `pm2-docs`, `spec-writer` |
| `dxf-output` | `dxf` | — | `board-design`, `iram-titleblock`, `mld`, `plan-drawing`, `sld` |
| `equipment-catalog` | — | — | `procurement` |
| `iec-symbols` | `symbols` | — | `mld`, `sld` |
| `intake-analysis` | — | — | — |
| `iram-titleblock` | `dxf`, `titleblock` | `dxf-output` | `board-design`, `mld`, `sld` |
| `mld` | `aea90364`, `calc_common`, `dxf`, `feeder_sizing`, `grounding`, `load_balance`, `mld`, `selectivity`, `short_circuit`, `symbols`, `titleblock`, `voltage_drop` | `aea-calc`, `dxf-output`, `iec-symbols`, `iram-titleblock` | `board-design` |
| `plan-drawing` | `dxf`, `plan` | `dxf-output` | — |
| `pm2-docs` | `documents` | `doc-quality` | — |
| `procurement` | — | `equipment-catalog` | — |
| `sld` | `aea90364`, `calc_common`, `dxf`, `feeder_sizing`, `grounding`, `load_balance`, `selectivity`, `short_circuit`, `sld`, `symbols`, `titleblock`, `voltage_drop` | `aea-calc`, `dxf-output`, `iec-symbols`, `iram-titleblock` | `board-design` |
| `spec-writer` | `documents` | `doc-quality` | — |
| `standard-ingest` | `rules`, `standards` | — | — |
