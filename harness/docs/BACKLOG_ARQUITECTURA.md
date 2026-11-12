# Backlog del motor de arquitectura (`epc_arch`)

> **Pendientes:** se trabajan desde el backlog maestro [`harness/docs/BACKLOG.md`](BACKLOG.md) (IDs `ARQ-NN`). Este archivo guarda lo hecho y su contexto.

Lo que queda por hacer después de la línea de trabajo "paridad entre formatos" (PRD `epc-arch Cross-Format Parity`, 3 nov 2026). Estado: `[ ]` pendiente, `[~]` hecho en parte (se dice qué falta), `[x]` hecho.
Cómo medir: `engine/arch/scripts/parity_check.py` (cantidades y métricas por posición contra los planos de prueba de `scripts/planta_prueba.py`) y `scripts/profile_engine.py` (tiempos).

## Hallazgos del proyecto 13 (hospital de tres niveles, `engine/arch/scripts/proyecto_13.py`)
Plano de autoría propia (L de 36 × 24 m, 50 locales en 3 niveles, muros de 30/15/12 cm, puertas de 0,80 a 1,40 m, ejes, cotas y rótulos); el script dibuja DXF y PNG, los pasa por el motor y compara con lo dibujado.
Resultado con el motor actual (reconocido/dibujado): DXF puertas 43/48, ventanas 39/35, ambientes 57/50; PNG puertas 48/48, ventanas 16/35.

## Más adelante (decidido el 5 nov 2026)
Lo que el dueño del proyecto anotó para después; nada de esto se hace ahora.
- **DWG: no se necesita** (decisión del dueño). Si algún día hiciera falta, no existe un lector abierto de licencia permisiva: se convertiría a DXF con un programa externo que instala el usuario (ODA File Converter, o LibreDWG, que es GPL), nunca empaquetado ni enlazado.
- Evitar: PyMuPDF (AGPL), potrace (GPL) y cualquier librería GPL enlazada al motor.

### Modelo único 2D/3D con exportación a IFC (propuesta: [ADR-0032](architecture/decisions/ADR-0032-single-2d-3d-model.md))
La idea: el motor lee la arquitectura que llega, se muestra en el navegador y se trabaja siempre en 2D (plantas, vistas, cortes y secciones); el 3D se puede ver en cualquier momento. Sobre ese modelo se incrustan canalizaciones, bandejas, cables y motores, y al exportar sale un IFC final.
- **La fuente es el modelo propio, en texto, versionado en git** (un JSON por nivel, claves ordenadas, identificadores estables). El IFC es una salida generada, no la fuente: un IFC regenerado cambia sus números internos y llenaría git de ruido. Los GlobalId del IFC se derivan de forma determinista de los identificadores estables del modelo, para que dos exportaciones iguales den el mismo archivo.
- **El 3D no necesita IFC para verse:** Three.js (MIT) o R3F (MIT) leen el mismo modelo y extruyen muros, losas y locales. web-ifc (MPL-2.0) solo haría falta para abrir IFC de terceros.
- **Alturas:** un plano 2D no trae cotas; el modelo pide la cota de cada nivel, la altura de muros y las alturas de aberturas (con valores por defecto editables), y lo eléctrico usa las alturas de montaje de los criterios de diseño.
- Fases: (1) modelo de arquitectura v1 en texto, con identificadores estables y aceptación de lo reconocido antes de guardarlo; (2) visor 3D en el navegador; (3) elementos eléctricos con su cota (bandejas, canalizaciones, cables, tableros, motores); (4) cortes, secciones y elevaciones obtenidos del modelo; (5) exportación IFC4 con IfcOpenShell (LGPL, en el servidor), con IfcCableCarrierSegment, IfcElectricDistributionBoard, IfcLightFixture, IfcMotor y sus conjuntos de propiedades.
- Decisiones del dueño: las alturas (cota de cada nivel, altura de muros y de aberturas) las establece él; las secciones y los cortes se dibujan a escala sobre la lámina de la organización (no se trabaja un modelo a tamaño real en pantalla); en git se ve el modelo en JSON y una vista previa SVG generada de cada nivel. No se agrega ninguna dependencia hasta que su fase la necesite.
