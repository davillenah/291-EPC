# Simulación 04 — Taller industrial: errores del harness y temporales

Proyecto ficticio `2026-ES-TAIN-0311` (TALLERES_INDUSTRIALES_DEL_SUR). Base: rama `claude/project-thread-birb0y` (commit e944ff6). Modo `edit`; firma simulada `ing-simulado`. No se arregló nada del harness. "Verificado" = visto en una salida o archivo de esta corrida; "Supuesto" = interpretación no comprobada.

## A. Temporales (workarounds)

| ID | Qué pasó | Qué hice | Cómo debería ser |
|---|---|---|---|
| T-01 | Sigue sin existir vía soportada para crear la arquitectura. | `dibujar_taller.py` con el modelo Python de `epc_arch` (hoja A1). | CLI/MCP o formulario para ambientes, muros y aberturas. |
| T-02 | `epc init` rechaza `TN-S` (acepta TT, TN, IT). Igual que sim-02. | Cargué `TN`; lo dejé escrito en el acta. | Aceptar la variante o pedirla como subpregunta. |
| T-03 | `epc init` rechaza el cliente con espacios (`TALLERES INDUSTRIALES DEL SUR`). Igual que sim-02. | Usé guiones bajos. | Normalizar el nombre. |
| T-04 | La nave de producción (353 m²) no se reconoce con portón de 4 m en el muro sur más 7 ventanas: el lector devuelve 7 de 8 ambientes. Sin portón da 8; sin ventanas da 8. **Verificado** con 3 variantes. Además los ids se corren (la nave pasa de r2 a otro número según el dibujo). | Quité las ventanas del dibujo. | Reconocer todos los ambientes con aberturas anchas; ids estables. |
| T-05 | Sin `engine_inputs.building` la corrida termina "ok" con 2 archivos (unifilar) y sin documentos ni aviso. Con `building` pide `luminaires` y `floors[].length`; al agregar `main_board`, prohíbe `length` y exige `elevation_m`. | Declaré una campana LED, `length`, luego `main_board`, sin `length`, con `elevation_m: 0`. | Valores por defecto (catálogo, elevación 0) y un solo mensaje con todo lo faltante. |
| T-06 | "Nave de produccion" no coincide con ningún tipo de ambiente; las actividades del catálogo son solo educación, `task.*`, `room.living`, `room.storage`, `circulation.indoor`: no hay industrial. | `activity: task.fine`, `height_m: 8`, `luminaire: LED` (da 750 lx). | Actividades industriales o un valor por defecto en vez de cortar. |
| T-07 | Coordenadas del tablero a mano. El plano de salida está espejado respecto de mi modelo (el eje Y baja), así que no sé si (31,0; 10,5) cayó en el centro de la Sala de tableros; en el render el tablero queda en esa sala, cerca del muro. **Verificado** por imagen, no medido. | Usé el centro de la sala en el modelo. | Indicar el ambiente por id. |
| T-08 | Cambié `inputs/plans/PB.dxf` después de la primera corrida: la etapa 2 se bloquea con "1 input file(s) changed since intake", el proyecto queda en `running` y no hay comando para aceptar la entrada nueva (ni re-intake ni revisión de entradas). **Verificado.** | Aparté el proyecto (`attempt1/`) y lo creé de nuevo con el plano bueno. | Una vía soportada para reemplazar una entrada con registro (nueva revisión del intake). |
| T-09 | Para volver a correr hace falta `epc review --corrections` con una lista JSON libre y el rol `engineer_of_record`; pero `run` rechaza ese rol y hay que cambiar a `orchestrator`. El mensaje de `approve` dice "run again" sin decir cómo. | Inventé etiquetas de "hallazgo" para el JSON; alterné roles. | Mensaje con el comando exacto; no exigir un hallazgo para corregir. |
| T-10 | Los 3 hallazgos major `differential_ok` (E-001..E-003) piden editar `kind` a `rcbo` y volver a correr. Igual que sim-02. | Lo hice; quedaron 0 major. | Proponerlo o aplicarlo solo. |
| T-11 | Las cargas y `engine_inputs` siguen sin formulario guiado (JSON a mano, incluidos estudios, reactiva y tierra). | Los escribí. | Bloque guiado. |

## B. Errores y faltantes

| ID | Hallazgo | Evidencia |
|---|---|---|
| B-01 | **Estudios de motores, reactiva y tierra: se calculan y no se documentan.** En `ssot/stage_06` hay arranque (M-001 152,8 A, 3,27 %), protecciones, 37,5 kvar a compensar con banco de 40 kvar (8 x 5), y Ra = 30,1 ohm con una jabalina; nada de eso está en los 12 PDF, el XLSX, el unifilar ni los planos. Solo queda una nota "assumption" por estudio. La temperatura del tablero (`panel_thermal`) tampoco se documenta. Confirma sim-02 B-07. | Verificado (búsqueda de kvar, jabalina, resistividad, arranque en todos los PDF y el XLSX). |
| B-02 | Las funciones `ra_maxima` y `verifica_ra` se ejecutan, pero la salida de tierra solo trae `resistance_ohm`; no hay veredicto contra el máximo. En esquema TN el encabezado de la tabla del diferencial muestra "Ra máx TT". | Verificado en `ssot` y en el PDF de la memoria. **Supuesto:** el veredicto se calcula y se descarta. |
| B-03 | Sin `main_board` (corrida sin ruteo) los documentos no se escriben (`formats_of` devuelve vacío) y el manifiesto lista `calculation_memo`, `design_basis`, etc. con `path: null`, sin mensaje ni hallazgo. | Verificado (1ª corrida: 7 entradas, 2 archivos). |
| B-04 | El plano eléctrico solo trae luminarias y circuitos de iluminación. Los 6 motores, el horno, las soldadoras y el clima no tienen posición ni se piden; el plano no avisa. Sin tomas declaradas, tampoco hay tomas ni aviso. | Verificado por imagen y por la lista de circuitos ruteados (9, todos de iluminación). |
| B-05 | Idioma `es`: el estudio de cortocircuito sale en inglés ("Summary", "Detail", "Assumptions"), el de iluminación con encabezado y avisos en inglés ("Rooms: 8; luminaires: 40", "give the manufacturer's CU table…"), la base de diseño en inglés con claves internas. | Verificado en los PDF. |
| B-06 | Encabezados de tabla rotos en el estudio de cortocircuito: "breaking capaIccicty m oikn" (columnas superpuestas); base de diseño: texto superpuesto ("motor_arranque oltage_drop.limite_cai"). La tabla del estudio de iluminación corta el nombre del ambiente en tres líneas. | Verificado (texto extraído de los PDF). |
| B-07 | La memoria de cálculo muestra "Frecuencia: Pendiente" y "Conductor cobre, aislación PVC" aunque la acometida se declaró XLPE. | Verificado (bloque del documento en `ssot/stage_11`). **Supuesto:** el segundo es el criterio base de circuitos. |
| B-08 | El rótulo del unifilar dice `BORRADOR` después de `issue` (los DXF no se regeneran). Igual que sim-02 B-06. | Verificado. |
| B-09 | El transformador de 630 kVA que el usuario declaró en el intake solo figura como texto; la etapa 4 dice "no hay entradas `transformer`" y no lo pregunta. No se usa en el cálculo de Icc (se tomó el dato declarado de 18 kA). | Verificado el mensaje. **Supuesto:** debería pedirlo o derivarlo. |
| B-10 | Iluminación: 11 avisos (CU ilustrativa del artículo UPV por luminaria sin tabla; separación mayor al máximo en 3 ambientes) quedan como notas sin dueño. La salida mezcla piso y ambiente en el nombre ("Planta Baja Sala de compresores"). | Verificado en `ssot` y PDF. |
| B-11 | Tras reemplazar la revisión R0 por R1, TR-001 queda `for_review` en el manifiesto (y su carpeta sigue en `deliverables/`), con `superseded_by: TR-002/R1`. | Verificado. **Supuesto:** el estado no debería ser `for_review` si está reemplazado. |
| B-12 | Etapa 4 `not_available` en toda corrida con red BT; no es error pero ocupa una fila. | Verificado. |

## C. Lo que funcionó (verificado)
- `epc init` con cliente y descripción; estructura `inputs/`, `deliverables/`, `.epc/`; D24 (tierra + Icc).
- Todo el flujo: run, `submit`, bloqueo de `approve` con 3 major (y la opción `--accept-major` en el mensaje), `review`, nueva corrida R1 sin major, `submit`, `approve`, `issue`; cadena de auditoría íntegra (33 eventos).
- Hash de entradas: reemplazar un archivo de `inputs/` bloquea la etapa 2 (respuesta a sim-01 B-15).
- Iluminación: 40 luminarias, 9 circuitos ruteados; planos con lámina y capas `A-*` / `E-*`; nomenclatura con código en todos los entregables; 34 archivos en 11,6 s.
- Todo marcado "EDIT MODE: norm values not verified, not for production" (399 de 414 registros sin verificar).
