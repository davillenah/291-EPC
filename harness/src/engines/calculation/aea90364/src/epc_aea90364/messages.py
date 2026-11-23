"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_calculation_invalid": {
        "en": "invalid calculation: {errors}",
        "es": "cálculo inválido: {errors}",
    },
    "err_circuit_failed": {
        "en": "{c}: {e}",
        "es": "{c}: {e}",
    },
    "err_duplicate_tags": {
        "en": "duplicate TAG in CIRCUITOS",
        "es": "TAG duplicados en CIRCUITOS",
    },
    "err_dz_invalid": {
        "en": "dz_m must be a finite number (got: {dz_m!r})",
        "es": "dz_m debe ser un número finito (recibido: {dz_m!r})",
    },
    "err_environment_unknown": {
        "en": "environment {entorno!r} does not exist: {opciones}",
        "es": "entorno {entorno!r} inexistente: {opciones}",
    },
    "err_export_json_only": {
        "en": "the calculation is exported only as .json (no PDF)",
        "es": "el cálculo se exporta solo como .json (sin PDF)",
    },
    "err_feeder_unknown": {
        "en": "feeder {tag!r} does not exist in CIRCUITOS",
        "es": "alimentador {tag!r} no existe en CIRCUITOS",
    },
    "err_fp_range": {
        "en": "fp between 0 and 1",
        "es": "fp entre 0 y 1",
    },
    "err_fraction_range": {
        "en": "{n} between 0 and 1",
        "es": "{n} entre 0 y 1",
    },
    "err_grade_invalid": {
        "en": "electrification_grade must be one of {allowed}, got {got!r}",
        "es": "electrification_grade debe ser uno de {allowed}, recibido {got!r}",
    },
    "err_group_unknown": {
        "en": "group {g!r} does not exist: {grupos}",
        "es": "grupo {g!r} inexistente: {grupos}",
    },
    "err_insulation_invalid": {
        "en": "insulation {aislacion!r} is not valid: {aislaciones}",
        "es": "insulation {aislacion!r} inválida: {aislaciones}",
    },
    "err_key_unknown": {
        "en": "{tabla}: {clave!r} does not exist: {opciones}",
        "es": "{tabla}: {clave!r} inexistente: {opciones}",
    },
    "err_level_unknown": {
        "en": "level {nivel!r} does not exist: {opciones}",
        "es": "nivel {nivel!r} inexistente: {opciones}",
    },
    "err_load_negative": {
        "en": "carga must be a number >= 0 (got: {carga!r})",
        "es": "carga debe ser un número ≥ 0 (recibido: {carga!r})",
    },
    "err_load_uninterpretable": {
        "en": "load cannot be interpreted: {carga!r}",
        "es": "carga no interpretable: {carga!r}",
    },
    "err_no_load_no_children": {
        "en": "{tag}: no CARGA and no children",
        "es": "{tag}: sin CARGA y sin hijos",
    },
    "err_no_main_feeder": {
        "en": "there is no main feeder: one circuit without PARENT_TAG and with KIND 'mccb' is required",
        "es": "no hay alimentador principal: se requiere un circuito sin PARENT_TAG y con KIND 'mccb'",
    },
    "err_no_solution_matches": {
        "en": "no standard solution matches circuit {f}: the document needs one with an empty 'when' as the last resort",
        "es": "ninguna solución estándar coincide con el circuito {f}: el documento necesita una con 'when' vacío como último recurso",
    },
    "err_parameter_unknown": {
        "en": "{id} has no parameter {parametro!r}: {opciones}",
        "es": "{id} no tiene el parámetro {parametro!r}: {opciones}",
    },
    "err_parent_cycle": {
        "en": "cycle in PARENT_TAG at {tag}",
        "es": "ciclo en PARENT_TAG en {tag}",
    },
    "err_parent_unknown": {
        "en": "{c}: PARENT_TAG {p!r} does not exist",
        "es": "{c}: PARENT_TAG {p!r} no existe",
    },
    "err_rated_over_100": {
        "en": "In > 100 A is outside Table 770-B.X",
        "es": "In > 100 A fuera de la Tabla 770-B.X",
    },
    "err_rated_over_125": {
        "en": "In > 125 A: use the manufacturer's data",
        "es": "In > 125 A: usar dato del fabricante",
    },
    "err_rule_unknown": {
        "en": "rule {id!r} does not exist",
        "es": "regla {id!r} inexistente",
    },
    "err_sheet_missing": {
        "en": "sheet {n} is missing in {ruta}",
        "es": "falta la hoja {n} en {ruta}",
    },
    "err_simultaneity_range": {
        "en": "simultaneity_factor must be in (0, 1], got {value!r}",
        "es": "el factor de simultaneidad debe estar en (0, 1], recibido {value!r}",
    },
    "err_unit_missing": {
        "en": "UNIDAD_CARGA is missing (A, W, kW, MW, VA, kVA, MVA, HP)",
        "es": "falta UNIDAD_CARGA (A, W, kW, MW, VA, kVA, MVA, HP)",
    },
    "err_unit_unknown": {
        "en": "load unit not recognized: {unidad!r} (use A, W, kW, MW, VA, kVA, MVA, HP)",
        "es": "unidad de carga no reconocida: {unidad!r} (use A, W, kW, MW, VA, kVA, MVA, HP)",
    },
    "err_expression_not_allowed": {
        "en": "only numbers, the facts of the circuit, + - * / // % and ceil, floor, max, min, round are allowed",
        "es": "solo se permiten números, los datos del circuito, + - * / // % y ceil, floor, max, min, round",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
