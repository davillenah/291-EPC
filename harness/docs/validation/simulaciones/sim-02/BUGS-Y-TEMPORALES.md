# Simulación 02 — Escuela rural Los Aromos: errores del harness y temporales

Proyecto ficticio `2026-ES-AROM-0207` (COOPERADORA_LOS_AROMOS, una planta de 30 x 12 m, 9 ambientes, 6 cargas). Base: rama `claude/project-thread-0bro9w` (commit fedae20, con los arreglos de sim-01). Modo `edit`; firma simulada `ing-simulado`. No se arregló nada del harness. "Verificado" = visto en una salida o archivo de esta corrida; "Supuesto" = interpretación no comprobada.

## A. Temporales (workarounds)

| ID | Qué pasó | Qué hice | Cómo debería ser |
|---|---|---|---|
| T-01 | Sigue sin existir una vía soportada para crear la arquitectura desde cero. | `tools/dibujar_escuela.py` con el modelo Python de `epc_arch` (capas y fuente de `epc_style.json`, hoja IRAM A1). | CLI/MCP o formulario para definir ambientes, muros y aberturas. |
| T-02 | `epc init` rechaza `TN-S`: acepta solo `TT`, `TN`, `IT`. | Cargué `TN`. | Aceptar la variante (TN-S / TN-C-S) o pedirla como subpregunta. |
| T-03 | `epc init` rechaza `--client "COOPERADORA LOS AROMOS"` (exige MAYÚSCULAS_CON_GUION_BAJO); el mensaje lo explica pero el usuario no escribe así. | Usé `COOPERADORA_LOS_AROMOS` y `ESCUELA_RURAL_LOS_AROMOS`. | Normalizar el nombre automáticamente. |
| T-04 | `building.floors[].elevation_m` es obligatorio ("the level of the floor in metres"). | Puse `0.0`. | Valor por defecto 0 para la primera planta. |
| T-05 | `building.luminaires` es obligatorio aunque el usuario no quiera elegir luminarias. | Declaré un panel LED 40 W genérico. | Un catálogo por defecto del harness; no pedirlo. |
| T-06 | "Dirección" y "Biblioteca" no coinciden con ninguna regla de `room_types` y el run se corta con error. | Escribí `activity: task.reading` en `rooms` (r5, r6). | Ampliar reglas (dirección, biblioteca, sala docente, SUM…) o usar una actividad por defecto en vez de cortar. |
| T-07 | Un ambiente descrito solo con `activity` falla con "`height_m` is required"; el autocompletado solo vale si no se describe nada. | Agregué `height_m: 3.0` y `luminaire: LED`. | Completar lo que falte con los valores por defecto. |
| T-08 | Coordenadas del tablero (`board`, `main_board`) escritas a mano en metros. | Calculé el centro de la Sala de tableros (26,95; 3,05). | Indicar el ambiente por id. |
| T-09 | Las cargas y `engine_inputs` siguen sin formulario guiado (JSON a mano). | Los escribí. | Bloque guiado. |

## B. Errores y faltantes

| ID | Hallazgo | Evidencia |
|---|---|---|
| B-01 | El id de ambiente sigue siendo `r1..r9` aunque el plano trae códigos (AU-01..SA-01, ahora sí leídos en `code`). El usuario ve `PB-r1` en el estudio de iluminación. | Verificado. |
| B-02 | "Sala de tableros" se clasifica por la palabra `sala` como estar (`room.living`, 220 lx) en vez de sala técnica. | Verificado en el estudio de iluminación. |
| B-03 | `epc approve` bloquea con 4 hallazgos major (F-0037..F-0040) y dice "fix them and run again", pero con el proyecto `in_review` `epc run` responde `bad_state` (solo corre desde `corrected`, `init`, `intake_done`, `running`). Hay que descubrir `epc review --corrections` (lista JSON libre) para volver a `corrected`. | Verificado. |
| B-04 | Los 4 major son `differential_ok` de E-001..E-004: el harness sabe que falta el diferencial, pero pide que el usuario edite `kind` a `rcbo` y vuelva a correr. Debería proponerlo o aplicarlo solo. Al hacerlo, quedaron 0 major. | Verificado. |
| B-05 | Las lecturas de sim-01 corregidas: manifiesto y transmittal dicen `issued` con firma; rótulo del unifilar con cliente, ubicación y estado (`BORRADOR`); una sola convención `A-*`/`E-*`; Arial; nombres con código. | Verificado (**confirmado como arreglado**). |
| B-06 | El estado `BORRADOR` del rótulo del DXF queda fijo tras `issue`: los DXF no se regeneran, el manifiesto dice `issued`. | Verificado. |
| B-07 | Pedí los estudios `motors`, `reactive`, `raceway_sizing`, tierra (`earthing` con resistividad y jabalina). Salvo raceway (CAL-002), no hay documento ni sección visible para motores (arranque), reactiva (kvar) ni puesta a tierra; solo un hallazgo "assumption" por estudio. El motor `calculation/grounding` figura en el manifiesto. | Verificado (no hay archivo); supuesto: el cálculo existe en `ssot` pero no se documenta. |
| B-08 | No hay datasheets ni lista de HVAC; no pedí HVAC. No hay `datasheets` en el manifiesto (antes figuraba sin archivo). | Verificado. |
| B-09 | Idioma `es`: el estudio de iluminación sale con encabezados y avisos en inglés ("Rooms: 9; luminaires: 42", "give the manufacturer's CU table…"); la Memoria Descriptiva mezcla "lighting: 9; motor: 2; special: 4". `Frecuencia: Pendiente` sigue en la Memoria de Cálculo. | Verificado. |
| B-10 | 10 avisos de iluminación por CU "ilustrativa del artículo UPV" (uno por ambiente); sigue sin ser un dato que el usuario deba dar, pero el aviso queda como pendiente sin dueño. | Verificado. |
| B-11 | Memoria de Cálculo indica "Conductor cobre, aislación PVC" aunque la acometida se declaró XLPE. **Supuesto:** es el criterio base de circuitos y no de la acometida. | Verificado el texto. |
| B-12 | Etapa 4 `not_available` (sin transformador) para una escuela alimentada en BT; no es error, pero cada corrida muestra una etapa "no disponible". | Verificado. |
| B-13 | Vista del plano de iluminación (hoja A1, 70 dpi): el edificio ocupa la mitad de la hoja y queda descentrado; el tablero está sobre el muro este. No se midió. | Observado. |

## C. Lo que funcionó (verificado)
- `epc init` con cliente/descripción, estructura `inputs/`, `deliverables/`, `.epc/`; D24 (tierra + Icc).
- Lector de planos: 9 de 9 ambientes con ventanas en el muro oeste (T-02 de sim-01 resuelto) y códigos leídos.
- Los ambientes no descritos (Aulas, Comedor, Cocina, Sanitarios, Sala) se iluminaron solos; 42 luminarias, 9 circuitos ruteados.
- Corrida `edit`: 12 etapas en 11 s; 38 archivos con nomenclatura `AAAA-PROV-CLIENTE-COD-E-LV-TIPO-NNN`.
- Bloqueo de `approve` con hallazgos major: funciona; tras corregir, `submit` → `approve` → `issue`; manifiesto `issued`, firmante `ing-simulado`, PDF del transmittal `Status issued`.
