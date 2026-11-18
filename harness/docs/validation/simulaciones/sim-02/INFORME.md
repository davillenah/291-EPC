# Simulación 02 — Escuela rural Los Aromos (ficticia)

Segundo proyecto de simulación, distinto de sim-01 (Mirador). Una planta de 30 x 12 m, 9 ambientes, TN, 6 kA, 400 V, 6 cargas (2 bombas, cocina, cámara, A/A, comunicaciones). Hecho con `epc` (init, run, submit, review, approve, issue) en modo edit, con datos ficticios fuera del repo. No arreglé nada del harness; todo lo encontrado está en `BUGS-Y-TEMPORALES.md`.

## Resultado (verificado)
- 12 etapas ok en 11 s; 38 archivos; transmittal TR-001 `issued`, firma simulada `ing-simulado`.
- Salidas: unifilar, tablero, planos y planos de iluminación (DXF), 15 documentos en PDF y DOCX, XLSX, transmittal.
- Los arreglos de sim-01 se confirmaron: ventanas del muro oeste, códigos de ambiente, estado y firma en el manifiesto, rótulo con cliente, capas únicas, bloqueo por hallazgos major.

## Lo que pidió de más el harness (pedido del usuario: que no pregunte)
1. Una luminaria declarada (`luminaires` obligatorio).
2. `elevation_m` de la planta.
3. Actividad, altura y luminaria para "Dirección" y "Biblioteca" (nombres no reconocidos).
4. Cambiar `kind` a `rcbo` en 4 circuitos para quitar los hallazgos de diferencial.
5. Coordenadas del tablero a mano. El coeficiente de utilización no se pidió: se usó el valor ilustrativo con aviso.

## Lo más importante que falló
- Para corregir un hallazgo major tras `submit`, el mensaje dice "run again" pero `epc run` rechaza el estado `in_review`; hay que usar `epc review`.
- Los estudios de motores, reactiva y puesta a tierra no producen documento.
- Textos en inglés dentro de documentos en español; "Frecuencia: Pendiente".
- Sin vía soportada para crear la arquitectura (sigue el temporal T-01).

## Supuestos
Que `TN-S` debería aceptarse; que los estudios sí se calculan pero no se documentan. Tiempos de un contenedor de Claude.
