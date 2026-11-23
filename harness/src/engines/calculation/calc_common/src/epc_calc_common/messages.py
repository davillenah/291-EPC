"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_column_unknown": {
        "en": "column {columna} does not exist; use one of {claves}",
        "es": "columna {columna} inexistente; use una de {claves}",
    },
    "err_constant_unknown": {
        "en": "constant {nombre} does not exist: {constantes}",
        "es": "constante {nombre} inexistente: {constantes}",
    },
    "err_grouping_buried": {
        "en": "buried grouping of {n_circuitos} circuits is outside Table 771.16.VII.{tabla}: the table has only {ns} circuits; there is no silent cap and the last factor is not repeated. Give in AGRUP_CIRCUITOS one of those numbers (regroup the circuits or separate the raceways)",
        "es": "agrupamiento enterrado de {n_circuitos} circuitos fuera de la Tabla 771.16.VII.{tabla}: la tabla trae solo {ns} circuitos; no hay tope silencioso ni se repite el último factor. Indique en AGRUP_CIRCUITOS uno de esos números (reagrupe los circuitos o separe las canalizaciones)",
    },
    "err_grouping_conduit": {
        "en": "grouping of {circuitos} circuits in the same conduit is outside Table 771.16.II.b (only 2 or 3 circuits): give in AGRUP_CIRCUITOS a number the table covers, or regroup the circuits",
        "es": "agrupamiento de {circuitos} circuitos en un mismo caño fuera de la Tabla 771.16.II.b (solo 2 o 3 circuitos): indique en AGRUP_CIRCUITOS un número cubierto por la tabla o reagrupe los circuitos",
    },
    "err_grouping_table_iv": {
        "en": "grouping of {n_circuitos} circuits is outside Table 771.16.IV (item {item}): the table has only {ns} circuits; it neither interpolates nor repeats the last factor. Give in AGRUP_CIRCUITOS one of those numbers (regroup the circuits or separate the raceways)",
        "es": "agrupamiento de {n_circuitos} circuitos fuera de la Tabla 771.16.IV (ítem {item}): la tabla trae solo {ns} circuitos; no se interpola ni se repite el último factor. Indique en AGRUP_CIRCUITOS uno de esos números (reagrupe los circuitos o separe las canalizaciones)",
    },
    "err_item_unknown": {
        "en": "item {item} does not exist in Table 771.16.IV",
        "es": "item {item} inexistente en Tabla 771.16.IV",
    },
    "err_negative": {
        "en": "{nombre} must be >= 0 (got: {valor})",
        "es": "{nombre} debe ser ≥ 0 (recibido: {valor})",
    },
    "err_no_factor_data": {
        "en": "no factor data for {x}",
        "es": "sin dato de factor para {x}",
    },
    "err_no_value_for_section": {
        "en": "no value for {seccion_mm2} mm² in column {columna}",
        "es": "sin valor para {seccion_mm2} mm² en columna {columna}",
    },
    "err_not_finite_number": {
        "en": "{nombre} must be a finite number (got: {v!r})",
        "es": "{nombre} debe ser un número finito (recibido: {v!r})",
    },
    "err_not_finite_number_value": {
        "en": "{nombre} must be a finite number (got: {valor!r})",
        "es": "{nombre} debe ser un número finito (recibido: {valor!r})",
    },
    "err_not_fraction": {
        "en": "{nombre} must be in (0, 1] (got: {valor})",
        "es": "{nombre} debe estar en (0, 1] (recibido: {valor})",
    },
    "err_not_positive": {
        "en": "{nombre} must be > 0 (got: {valor})",
        "es": "{nombre} debe ser > 0 (recibido: {valor})",
    },
    "err_out_of_range": {
        "en": "{nombre} must be {relacion} {minimo} (got: {v})",
        "es": "{nombre} debe ser {relacion} {minimo} (recibido: {v})",
    },
    "err_section_outside_table": {
        "en": "section {seccion_mm2} mm² is outside {tabla}/{aislacion}/{material}",
        "es": "sección {seccion_mm2} mm² fuera de {tabla}/{aislacion}/{material}",
    },
    "err_spacing_missing": {
        "en": "the spacing between cables (SEPARACION_CABLES) of Table 771.16.VII.{tabla} is missing: give one of {opciones}; there is no default column",
        "es": "falta la separación entre cables (SEPARACION_CABLES) de la Tabla 771.16.VII.{tabla}: indique una de {opciones}; no hay columna por defecto",
    },
    "err_table_block_missing": {
        "en": "no block {aislacion}/{grupo} in {tabla}",
        "es": "sin bloque {aislacion}/{grupo} en {tabla}",
    },
    "err_table_unknown": {
        "en": "table {tabla} does not exist: {tablas}",
        "es": "tabla {tabla} inexistente: {tablas}",
    },
    "err_value_outside_range": {
        "en": "value {x} is outside the range of the table [{xs}, {xs2}]",
        "es": "valor {x} fuera del rango de la tabla [{xs}, {xs2}]",
    },
    "err_value_outside_table": {
        "en": "value {x} is outside the table",
        "es": "valor {x} fuera de tabla",
    },
    "err_d2_column_missing": {
        "en": "method {metodo} (directly buried) with {cargados} loaded conductors: COLUMNA_D2 is missing or does not apply ({columna!r}); give the column of Table {tabla} that fits the installation: {detalle}. There is no default column",
        "es": "método {metodo} (directamente enterrado) con {cargados} conductores cargados: falta o no corresponde COLUMNA_D2 ({columna!r}); indique la columna de la Tabla {tabla} según la instalación: {detalle}. No hay columna por defecto",
    },
    "err_prefixed": {
        "en": "{prefix}: {detail}",
        "es": "{prefix}: {detail}",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
