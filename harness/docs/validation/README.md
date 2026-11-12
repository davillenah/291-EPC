# `validation`

Status: **in development**

Plantillas para las tareas del dueño de la etapa 4 de la migración. Las genera una herramienta; no se editan a mano y no traen ningún valor completado.

| Libro | Para qué sirve | Tarea |
| --- | --- | --- |
| `norm_verification_worksheet.xlsx` | Planilla de verificación de valores de norma: una fila por cada valor del registro de normas, en el orden del plan (conflictos o duplicados, sin cláusula, Parte 771, Partes 770/701/722, Partes 4 y 5 escaneadas). | MIG-40 |
| `spike_309kva_input_template.xlsx` | Plantilla de datos del proyecto `309kva_logistics_center`: perfil, áreas, cargas, requisitos, valores de referencia calculados de forma independiente y tolerancias. | MIG-42 |

La tarea MIG-43 (regeneración oficial de los resultados de referencia) sigue después, cuando ambos libros estén completos.

## Cómo se usan

1. Abra el libro y lea la hoja `Instrucciones`.
2. Complete solo las columnas amarillas. Las grises vienen del registro y no se tocan.
3. En la planilla de normas, cada fila termina con un veredicto (Verificado, Corregir, Rechazar, Pendiente); la hoja `Resumen` cuenta sola. Las filas marcadas `Sí (D15)` o `Sí (D26)` están congeladas: se dejan en blanco.
4. En la plantilla del proyecto, los valores de referencia se calculan sin usar el sistema, y las dos tolerancias (criterios 2 y 4 del spike) se anotan en la hoja `Tolerancias`.

Nada queda aprobado hasta que usted completa el veredicto; los libros no modifican el registro de normas.

## Regenerar y comprobar

```
python harness/tools/build/validation_templates.py           # escribe los dos libros
python harness/tools/build/validation_templates.py --check   # falla si están desactualizados respecto del registro
```

El `--check` también corre en las pruebas (`harness/tests/unit/test_validation_templates_fresh.py`). Si cambia el registro de normas, hay que regenerar los libros antes de que el usuario los complete.
