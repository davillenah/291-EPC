# Backlog de tomacorrientes

> **Pendientes:** se trabajan desde el backlog maestro [`harness/docs/BACKLOG.md`](BACKLOG.md) (IDs `TOM-NN`). Este archivo guarda lo hecho y su contexto.

Lo que hay y lo que falta del motor `epc_receptacles` y de su integración en la plataforma (ADR-0031, hecho el 2026-11-02).
Estado: `[ ]` pendiente, `[~]` hecho en parte (se dice qué falta), `[x]` hecho.

## Hecho
- [x] Motor `epc_receptacles`: cantidad por uso del ambiente (por área, por perímetro o fija), reparto a lo largo de las paredes lejos de las esquinas, verificación de la altura de montaje (AEA 90364-7-771 y 770, ambientes con agua), carga y circuitos mínimos; cada estimación dice por qué y con qué confianza.
- [x] Catálogo de tomacorrientes en tres niveles (fábrica, empresa, proyecto), con su editor en Datos y en Ingeniería → Catálogos del proyecto.
- [x] Panel «Tomacorrientes» en el editor de planos: uso del ambiente, tomacorriente, cantidad, altura y sección de la norma; calcula, verifica lo dibujado y pone los nodos `TG`/`TE` en el plano (reemplaza los que puso un cálculo anterior y conserva el circuito del más cercano).
- [x] El diseño automático de circuitos usa la potencia de cada tomacorriente colocado.
- [x] Los valores típicos (cantidad por uso, alturas, tomacorrientes por circuito) están en la página global de normas, para confirmarlos una sola vez.
- [x] Estudio guardado con la hoja, memoria en Markdown entre los documentos del proyecto, PDF al emitir y botón en Memorias.
