"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_breaking_capacity_entry": {
        "en": "{where}: breaking_capacity entry {n} needs voltage_v and icu_ka",
        "es": "{where}: la entrada {n} de breaking_capacity necesita voltage_v e icu_ka",
    },
    "err_breaking_capacity_not_list": {
        "en": "{where}: breaking_capacity must be a list",
        "es": "{where}: breaking_capacity debe ser una lista",
    },
    "err_cannot_read": {
        "en": "cannot read {path}: {exc}",
        "es": "no se puede leer {path}: {exc}",
    },
    "err_catalog_folder_empty": {
        "en": "catalog folder {root} has no manufacturer folder",
        "es": "la carpeta del catálogo {root} no tiene ninguna carpeta de fabricante",
    },
    "err_catalog_folder_missing": {
        "en": "catalog folder not found: {root}",
        "es": "no se encontró la carpeta del catálogo: {root}",
    },
    "err_catalog_invalid": {
        "en": "catalog must be a list of manufacturer product documents",
        "es": "catalog debe ser una lista de documentos de productos de fabricante",
    },
    "err_categories_empty": {
        "en": "{where}: categories must be a non-empty list",
        "es": "{where}: categories debe ser una lista no vacía",
    },
    "err_circuit_not_object": {
        "en": "circuit {n}: must be an object (got {got})",
        "es": "circuito {n}: debe ser un objeto (recibido {got})",
    },
    "err_circuit_unknown_keys": {
        "en": "circuit {n}: unknown key(s) {keys}",
        "es": "circuito {n}: clave(s) desconocida(s) {keys}",
    },
    "err_circuits_empty": {
        "en": "circuits must be a non-empty list of circuit objects",
        "es": "circuits debe ser una lista no vacía de objetos de circuito",
    },
    "err_circuits_not_tags": {
        "en": "{where}: circuits must be a list of circuit tags",
        "es": "{where}: circuits debe ser una lista de etiquetas de circuito",
    },
    "err_duplicate_product": {
        "en": "duplicate product id {product_id!r} in the catalog",
        "es": "id de producto duplicado {product_id!r} en el catálogo",
    },
    "err_duplicate_requirement_ids": {
        "en": "duplicate requirement item_id(s): {ids}",
        "es": "item_id de requisito duplicado(s): {ids}",
    },
    "err_duplicate_tags": {
        "en": "duplicate circuit tag(s): {tags}",
        "es": "etiqueta(s) de circuito duplicada(s): {tags}",
    },
    "err_invalid_json": {
        "en": "{path} is not valid JSON: {exc}",
        "es": "{path} no es JSON válido: {exc}",
    },
    "err_manufacturer_mismatch": {
        "en": "{path}: manufacturer must be {info!r}",
        "es": "{path}: manufacturer debe ser {info!r}",
    },
    "err_missing_key": {
        "en": "{where}: missing or empty required key {key}",
        "es": "{where}: falta o está vacía la clave obligatoria {key}",
    },
    "err_missing_keys": {
        "en": "{where}: missing or empty required key(s) {keys}",
        "es": "{where}: faltan o están vacías las claves obligatorias {keys}",
    },
    "err_no_manufacturer_json": {
        "en": "{folder}: manufacturer.json not found",
        "es": "{folder}: no se encontró manufacturer.json",
    },
    "err_no_product_file": {
        "en": "{folder}: no product file ({names}) found",
        "es": "{folder}: no se encontró ningún archivo de productos ({names})",
    },
    "err_not_finite_number": {
        "en": "{where} must be a finite number >= {minimum} (got {value!r})",
        "es": "{where} debe ser un número finito mayor o igual que {minimum} (recibido {value!r})",
    },
    "err_not_object": {
        "en": "{where}: must be an object",
        "es": "{where}: debe ser un objeto",
    },
    "err_not_positive_number": {
        "en": "{name} must be a positive finite number (got {value!r})",
        "es": "{name} debe ser un número finito positivo (recibido {value!r})",
    },
    "err_not_text": {
        "en": "{name} must be a non-empty string (got {value!r})",
        "es": "{name} debe ser un texto no vacío (recibido {value!r})",
    },
    "err_phases_not_1_or_3": {
        "en": "{where}: phases must be 1 or 3 (got {value!r})",
        "es": "{where}: las fases deben ser 1 o 3 (recibido {value!r})",
    },
    "err_poles_invalid": {
        "en": "{where}: poles must be 1, 2, 3 or 4 (got {value!r})",
        "es": "{where}: los polos deben ser 1, 2, 3 o 4 (recibido {value!r})",
    },
    "err_poles_list": {
        "en": "{where}: poles must be a list of integers from 1 to 4",
        "es": "{where}: poles debe ser una lista de enteros de 1 a 4",
    },
    "err_product_not_object": {
        "en": "{where}: a product must be an object",
        "es": "{where}: un producto debe ser un objeto",
    },
    "err_products_not_list": {
        "en": "{where}: products must be a list",
        "es": "{where}: products debe ser una lista",
    },
    "err_rated_current_range": {
        "en": "{where}: rated_current_a min is greater than max",
        "es": "{where}: el mínimo de rated_current_a es mayor que el máximo",
    },
    "err_rated_current_shape": {
        "en": "{where}: rated_current_a must be an object {{min?, max?}} or a list of numbers",
        "es": "{where}: rated_current_a debe ser un objeto {{min?, max?}} o una lista de números",
    },
    "err_rated_current_unknown_keys": {
        "en": "{where}: rated_current_a has unknown key(s) {keys}",
        "es": "{where}: rated_current_a tiene clave(s) desconocida(s) {keys}",
    },
    "err_requirement_kind": {
        "en": "requirement {n}: kind must be '{device_kind}' or '{cable_kind}' (got {kind!r})",
        "es": "requisito {n}: kind debe ser '{device_kind}' o '{cable_kind}' (recibido {kind!r})",
    },
    "err_requirement_not_object": {
        "en": "requirement {n}: must be an object (got {got})",
        "es": "requisito {n}: debe ser un objeto (recibido {got})",
    },
    "err_requirement_unknown_keys": {
        "en": "requirement {n}: unknown key(s) {keys}",
        "es": "requisito {n}: clave(s) desconocida(s) {keys}",
    },
    "err_requirements_invalid": {
        "en": "requirements must be a list of requirement objects",
        "es": "requirements debe ser una lista de objetos de requisito",
    },
    "err_status_invalid": {
        "en": "{where}: status must be one of {allowed} (got {got!r})",
        "es": "{where}: status debe ser uno de {allowed} (recibido {got!r})",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
