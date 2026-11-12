# Backlog de pliegos técnicos

> **Pendientes:** se trabajan desde el backlog maestro [`harness/docs/BACKLOG.md`](BACKLOG.md) (IDs `PLG-NN`). Este archivo guarda lo hecho y su contexto.

Pendientes de la redacción de pliegos (agente `Document Writer`, skill `generate-specification`, plugin `spec-writer` y verificador `epc_documents.specification_verifier`).
Estado: `[ ]` pendiente, `[~]` hecho en parte, `[x]` hecho.

## Hecho
- [x] **Agente `Document Writer` con el prompt generador de pliegos** (2026-11-01). Autor técnico de Especificaciones Técnicas Particulares: analiza el proyecto, propone la estructura y espera validación, lista los vacíos y redacta el pliego completo en Markdown (estructura objetivo de 16 secciones). Guarda el pliego como un solo archivo en `02-engineering/TECHNICAL_SPECS/` (tiene la herramienta `Write`). Conserva las reglas del proyecto: sin precios (RG-21), normas con su edición, marcas `[DEFINIR]`, `[VERIFICAR]` y `[SUPUESTO SUP-nnn]`, formato Pandoc y modo revisión.
