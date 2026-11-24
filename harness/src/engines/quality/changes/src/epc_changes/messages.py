"""Every error of the engine, in English (source) and Spanish. A message is a code with two templates (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_not_records": {
        "en": "{name} must be a list of records (objects) (got {value!r})",
        "es": "{name} debe ser una lista de registros (objetos) (recibido {value!r})",
    },
    "err_missing_id": {
        "en": "record {index} of {name} has no usable '{id_field}' (it must be a non-empty text or a number)",
        "es": "el registro {index} de {name} no tiene un '{id_field}' utilizable (debe ser un texto no vacío o un número)",
    },
    "err_duplicate_id": {
        "en": "{name} has the identifier {identifier!r} more than once",
        "es": "{name} tiene el identificador {identifier!r} más de una vez",
    },
    "err_not_text": {
        "en": "{name} must be a non-empty text (got {value!r})",
        "es": "{name} debe ser un texto no vacío (recibido {value!r})",
    },
    "err_not_names": {
        "en": "{name} must be a list of field names (texts) (got {value!r})",
        "es": "{name} debe ser una lista de nombres de campo (textos) (recibido {value!r})",
    },
    "err_not_count": {
        "en": "{name} must be a whole number of at least 1 (got {value!r})",
        "es": "{name} debe ser un entero de al menos 1 (recibido {value!r})",
    },
    "err_too_many": {
        "en": "there are {count} changes, more than the limit {limit}",
        "es": "hay {count} cambios, más que el límite {limit}",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
