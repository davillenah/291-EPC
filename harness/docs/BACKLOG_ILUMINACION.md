# Backlog de iluminación

> **Pendientes:** se trabajan desde el backlog maestro [`harness/docs/BACKLOG.md`](BACKLOG.md) (IDs `ILU-NN`). Este archivo guarda lo hecho y su contexto.

Lo que falta y lo que se puede mejorar del motor `epc_lighting` y de su integración en la plataforma (ADR-0029 y ADR-0030, fases 1 a 7 terminadas el 2026-10-28; mejoras del 2026-10-28 hechas aparte).
Estado: `[ ]` pendiente, `[~]` hecho en parte (se dice qué falta), `[x]` hecho.

## Pendientes (lo que quedó sin hacer o sin verificar)

### Plataforma
- [x] Luminarias de emergencia como nodos del plano (tipo `LE`, familia de circuito `IUE`).
- [x] El diseño automático usa la potencia aparente de cada luminaria (factor de potencia del catálogo; sin dato, los W).
- [x] Al recalcular y volver a aplicar, las luminarias nuevas toman el circuito de la que reemplazan.
- [x] La memoria de cálculo trae el rótulo del proyecto (emisora, cliente, quien dibujó, revisó y aprobó), la tabla de energía y el plano con luminarias y mapa.
- [x] Las pruebas del motor que leen las reglas reales del Decreto ya no dependen de que estén pendientes.

## Mejoras

### Cálculo y verificación
- [x] **Verificar el plano tal como está dibujado**: botón "Verificar el plano dibujado" (calcula con las luminarias que hay, donde estén).
- [x] **Comparar alternativas** por ambiente, con la mejor al principio y "Usar".
- [x] Verificar la eficiencia energética contra un límite de W/m² propio y estimar kWh/año y costo (con horas y tarifa propias).
- [x] Elegir automáticamente la luminaria cuando el ambiente solo tiene actividad (opción de la hoja).

### Pantalla
- [x] Mostrar en el panel el error de guardado del estudio y el de lectura (así se ve cuando el backend es una versión anterior).
- [x] Copiar los parámetros de un ambiente a otros, y plantillas por tipo de ambiente (se guardan con la hoja).
- [x] Proponer la actividad según el nombre del ambiente.
- [x] Rotular cada luminaria con su etiqueta en la vista previa.
- [x] Mapa de iluminancia: curvas de nivel con su valor, el interruptor se recuerda en la hoja y exportación a imagen (PNG).
- [x] Mostrar la fuente de la meta (norma y cláusula, o la actividad) en la tarjeta de cada ambiente.

### Catálogo
- [x] Duplicar, buscar, agrupar e importar desde una planilla (pegar o archivo CSV).
- [x] Marcar favoritas (van primero) y cargar el factor de potencia de cada luminaria.

### Entregables
- [x] Memoria con plano, mapa y tablas por ambiente en una sola emisión.
