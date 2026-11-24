"""Every error of the engine, in English (source) and Spanish. A message is a code with two templates (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_not_records": {
        "en": "records must be a list of records (objects) (got {value!r})",
        "es": "records debe ser una lista de registros (objetos) (recibido {value!r})",
    },
    "err_bad_condition": {
        "en": "condition {index} must be an object with 'field', 'op' and (except for 'exists') 'value' (got {value!r})",
        "es": "la condición {index} debe ser un objeto con 'field', 'op' y (salvo 'exists') 'value' (recibido {value!r})",
    },
    "err_unknown_op": {
        "en": "condition {index} has the unknown operator {op!r}; use one of {allowed}",
        "es": "la condición {index} tiene el operador desconocido {op!r}; use uno de {allowed}",
    },
    "err_bad_match": {
        "en": "match must be 'all' or 'any' (got {value!r})",
        "es": "match debe ser 'all' o 'any' (recibido {value!r})",
    },
    "err_not_count": {
        "en": "max_results must be a whole number of at least 1 (got {value!r})",
        "es": "max_results debe ser un entero de al menos 1 (recibido {value!r})",
    },
    "err_too_many": {
        "en": "{count} records match, more than the limit {limit}",
        "es": "{count} registros coinciden, más que el límite {limit}",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
