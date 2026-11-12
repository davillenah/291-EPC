# EPC-291

**Un harness nativo de Claude para ingeniería multidisciplinaria.**
Motores deterministas calculan y dibujan, agentes de Claude orquestan, un verificador independiente controla y el ingeniero responsable revisa y firma.

[Contribuir](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Licencia](LICENSE) · [English](README.md) · [Arquitectura](harness/docs/architecture/README.md) · [Documentación](harness/docs/README.md)

## Idea

Los agentes nunca escriben un número. Cada valor sale de un motor (por el servidor MCP `epc` o la CLI `epc`) y es trazable a sus entradas, la versión del motor y el registro de norma. La estructura sigue las bases de Anthropic: `CLAUDE.md` con reglas fijas, subagentes con sus herramientas, skills, hooks que hacen cumplir las reglas en código y MCP.

- `harness/.claude/`: agentes (orquestadores y líder por disciplina), skills, plugins y hooks.
- `harness/src/engines/`: motores de cálculo, CAD, validación, calidad y compras.
- `harness/src/disciplines/`: una carpeta por disciplina (`electrical_lv` en desarrollo; civil, mecánica, HVAC, piping, incendio, instrumentación y telecomunicaciones planificadas).
- `harness/src/platform/`: almacén de la fuente única de verdad, bitácora encadenada por hash, manifiestos, MCP y CLI.
- `projects/`: datos de proyectos (nunca versionados; solo `_template`).

## Estado

Eléctrica de baja tensión (AEA 90364, Argentina): en desarrollo. Los valores de norma quedan «pendientes de revisión» hasta que una persona los aprueba.

## Inicio rápido

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python harness/tools/ci/run_gate.py
```

## Legal

- Las normas, libros y material con derechos de autor no se versionan (`*.pdf` está ignorado). Cada persona usa sus copias con licencia.
- Licencia [MIT](LICENSE). **Toda copia, fork u obra derivada debe conservar el nombre del autor, Daniel A. Villena H., como dueño del repositorio original.**
- Los resultados son una ayuda para un ingeniero calificado y no son válidos para construcción hasta que el ingeniero responsable los revise y firme.

© 2026 Daniel A. Villena H.
