"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_boq_invalid": {
        "en": "boq must be a dict with a non-empty list `items`",
        "es": "boq debe ser un dict con una lista no vacía `items`",
    },
    "err_boq_item_not_object": {
        "en": "BOQ item {n}: must be an object (got {got})",
        "es": "ítem {n} del cómputo: debe ser un objeto (recibido {got})",
    },
    "err_candidate_not_object": {
        "en": "{where}: a candidate must be an object",
        "es": "{where}: un candidato debe ser un objeto",
    },
    "err_categories_invalid": {
        "en": "requestable_categories must be a non-empty list of category names or null",
        "es": "requestable_categories debe ser una lista no vacía de nombres de categoría o null",
    },
    "err_datasheet_not_object": {
        "en": "datasheet {n}: must be an object (got {got})",
        "es": "hoja de datos {n}: debe ser un objeto (recibido {got})",
    },
    "err_datasheets_invalid": {
        "en": "datasheets must be a dict with a list `datasheets`",
        "es": "datasheets debe ser un dict con una lista `datasheets`",
    },
    "err_duplicate_boq_ids": {
        "en": "duplicate BOQ item_id(s): {ids}",
        "es": "item_id duplicado(s) en el cómputo: {ids}",
    },
    "err_duplicate_suppliers": {
        "en": "duplicate supplier name(s): {names}",
        "es": "nombre(s) de proveedor duplicado(s): {names}",
    },
    "err_kind_invalid": {
        "en": "{where}: kind must be one of {allowed} (got {got!r})",
        "es": "{where}: kind debe ser uno de {allowed} (recibido {got!r})",
    },
    "err_missing_commercial_fields": {
        "en": "missing required commercial field(s): {fields}",
        "es": "faltan campos comerciales obligatorios: {fields}",
    },
    "err_no_requestable_line": {
        "en": "no bill-of-quantities line is requestable with the given categories",
        "es": "ninguna línea del cómputo es cotizable con las categorías indicadas",
    },
    "err_not_calendar_date": {
        "en": "{name} is not a valid calendar date (got {value!r})",
        "es": "{name} no es una fecha de calendario válida (recibido {value!r})",
    },
    "err_not_iso_date": {
        "en": "{name} must be an ISO date YYYY-MM-DD (got {value!r})",
        "es": "{name} debe ser una fecha ISO AAAA-MM-DD (recibido {value!r})",
    },
    "err_not_list_of_text": {
        "en": "{where}: {what} must be a list of text",
        "es": "{where}: {what} debe ser una lista de textos",
    },
    "err_not_positive_integer": {
        "en": "{name} must be a positive whole number (got {value!r})",
        "es": "{name} debe ser un entero positivo (recibido {value!r})",
    },
    "err_not_positive_number_or_null": {
        "en": "{name} must be a positive finite number or null (got {value!r})",
        "es": "{name} debe ser un número finito positivo o null (recibido {value!r})",
    },
    "err_not_text": {
        "en": "{name} must be a non-empty string (got {value!r})",
        "es": "{name} debe ser un texto no vacío (recibido {value!r})",
    },
    "err_requirement_invalid": {
        "en": "{where}: requirement must be an object and candidates a list",
        "es": "{where}: el requisito debe ser un objeto y los candidatos una lista",
    },
    "err_spec_not_object": {
        "en": "{where}: spec must be an object",
        "es": "{where}: spec debe ser un objeto",
    },
    "err_supplier_not_object": {
        "en": "supplier {n}: must be an object (got {got})",
        "es": "proveedor {n}: debe ser un objeto (recibido {got})",
    },
    "err_supplier_unknown_keys": {
        "en": "supplier {n}: unknown key(s) {keys}",
        "es": "proveedor {n}: clave(s) desconocida(s) {keys}",
    },
    "err_suppliers_empty": {
        "en": "suppliers must be a non-empty list of supplier objects",
        "es": "suppliers debe ser una lista no vacía de objetos de proveedor",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
