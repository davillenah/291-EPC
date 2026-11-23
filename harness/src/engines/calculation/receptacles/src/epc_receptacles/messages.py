"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_count_invalid": {
        "en": "{where}.count: a whole number from 0 to {max_outlets}",
        "es": "{where}.count: un entero de 0 a {max_outlets}",
    },
    "err_document_not_json": {
        "en": "the document is not valid JSON: {exc}",
        "es": "el documento no es JSON válido: {exc}",
    },
    "err_document_shape": {
        "en": "the document must be a JSON object with `receptacles` and `rooms`",
        "es": "el documento debe ser un objeto JSON con `receptacles` y `rooms`",
    },
    "err_narrow_invalid": {
        "en": "{where}.narrow: true or false",
        "es": "{where}.narrow: verdadero o falso",
    },
    "err_norm_invalid": {
        "en": "{where}.norm: one of {allowed}",
        "es": "{where}.norm: una de {allowed}",
    },
    "err_number_range": {
        "en": "{where}: a number above {low} and up to {high}",
        "es": "{where}: un número mayor que {low} y hasta {high}",
    },
    "err_outlet_id_repeated": {
        "en": "receptacles[{i}]: the id '{o}' is repeated",
        "es": "receptacles[{i}]: el id '{o}' está repetido",
    },
    "err_outlet_kind": {
        "en": "{where}.kind: `general` or `special`",
        "es": "{where}.kind: `general` o `special`",
    },
    "err_outlet_needs_id": {
        "en": "{where}: each outlet needs an `id`",
        "es": "{where}: cada tomacorriente necesita un `id`",
    },
    "err_outlet_not_found": {
        "en": "{where}.receptacle: '{outlet}' is not among the outlets of the document",
        "es": "{where}.receptacle: '{outlet}' no está entre los tomacorrientes del documento",
    },
    "err_position_needs_xy": {
        "en": "{where}.positions[{i}]: needs `x_m` and `y_m` in metres",
        "es": "{where}.positions[{i}]: necesita `x_m` e `y_m` en metros",
    },
    "err_positions_list": {
        "en": "{where}.positions: a list of up to {max_outlets} points",
        "es": "{where}.positions: una lista de hasta {max_outlets} puntos",
    },
    "err_receptacles_not_list": {
        "en": "`receptacles` must be a list",
        "es": "`receptacles` debe ser una lista",
    },
    "err_room_id_repeated": {
        "en": "rooms[{i}]: the id '{room}' is repeated",
        "es": "rooms[{i}]: el id '{room}' está repetido",
    },
    "err_room_needs_id": {
        "en": "{where}: each room needs an `id`",
        "es": "{where}: cada local necesita un `id`",
    },
    "err_rooms_list": {
        "en": "`rooms` must be a list of up to {max_rooms} rooms",
        "es": "`rooms` debe ser una lista de hasta {max_rooms} locales",
    },
    "err_use_unknown": {
        "en": "{where}.use: '{use}' is not a known use ({known})",
        "es": "{where}.use: '{use}' no es un uso conocido ({known})",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
