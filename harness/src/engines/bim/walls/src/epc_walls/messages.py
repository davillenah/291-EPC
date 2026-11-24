"""Every error and every note of the engine, in English (source) and Spanish. A message is a code with two templates (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_duplicate_wall_ids": {
        "en": "duplicate wall id(s): {ids}",
        "es": "identificador(es) de muro duplicado(s): {ids}",
    },
    "err_layer_function": {
        "en": "{where}: function must be one of {allowed} (got {value!r})",
        "es": "{where}: la función debe ser una de {allowed} (recibido {value!r})",
    },
    "err_layer_kind": {
        "en": "{where}: kind must be 'material' or 'cavity' (got {value!r})",
        "es": "{where}: el tipo debe ser 'material' o 'cavity' (recibido {value!r})",
    },
    "err_layer_priority": {
        "en": "{where}: priority must be a whole number from {low} to {high} (got {value!r})",
        "es": "{where}: la prioridad debe ser un entero de {low} a {high} (recibido {value!r})",
    },
    "err_layer_thickness": {
        "en": "{where}: thickness must be a number from 0 to {high} mm (got {value!r})",
        "es": "{where}: el espesor debe ser un número de 0 a {high} mm (recibido {value!r})",
    },
    "err_layer_zero_not_membrane": {
        "en": "{where}: only a material layer with the function 'membrane' may have no thickness",
        "es": "{where}: solo una capa de material con la función 'membrane' puede no tener espesor",
    },
    "err_layers_count": {
        "en": "an assembly needs from 1 to {high} layers (got {count})",
        "es": "un ensamblaje necesita de 1 a {high} capas (recibido {count})",
    },
    "err_layers_no_thickness": {
        "en": "the layers add up to no thickness: give at least one layer with a thickness",
        "es": "las capas suman espesor cero: indicar al menos una capa con espesor",
    },
    "err_not_object": {
        "en": "{where} must be an object (got {got})",
        "es": "{where} debe ser un objeto (recibido {got})",
    },
    "err_not_point": {
        "en": "{where} must be a point [x, y] of two finite numbers (got {value!r})",
        "es": "{where} debe ser un punto [x, y] de dos números finitos (recibido {value!r})",
    },
    "err_not_positive_number": {
        "en": "{name} must be a positive finite number (got {value!r})",
        "es": "{name} debe ser un número finito positivo (recibido {value!r})",
    },
    "err_not_text": {
        "en": "{name} must be a non-empty string (got {value!r})",
        "es": "{name} debe ser un texto no vacío (recibido {value!r})",
    },
    "err_style_invalid": {
        "en": "join {key}: style must be 'mitre', 'butt' or 'square', and 'through' one of the two walls of an L join (got {value!r})",
        "es": "unión {key}: el estilo debe ser 'mitre', 'butt' o 'square', y 'through' uno de los dos muros de una unión L (recibido {value!r})",
    },
    "err_unknown_keys": {
        "en": "{where}: unknown key(s) {keys}",
        "es": "{where}: clave(s) desconocida(s) {keys}",
    },
    "err_wall_both_thickness": {
        "en": "{where}: give either 't' or 'layers', not both: the thickness of a layered wall is the sum of its layers (one source)",
        "es": "{where}: indicar 't' o 'layers', no ambos: el espesor de un muro por capas es la suma de sus capas (una sola fuente)",
    },
    "err_wall_no_thickness": {
        "en": "{where}: give a thickness 't' or a list of 'layers'",
        "es": "{where}: indicar un espesor 't' o una lista de 'layers'",
    },
    "err_wall_zero_length": {
        "en": "{where}: the two ends of the wall are the same point",
        "es": "{where}: los dos extremos del muro son el mismo punto",
    },
    "err_walls_empty": {
        "en": "walls must be a non-empty list of wall objects",
        "es": "walls debe ser una lista no vacía de objetos de muro",
    },
}

#: Notes that come with a result (issues): a code and both texts. Never an error: the geometry was made.
NOTES: Dict[str, Dict[str, str]] = {
    "note_corner_square": {
        "en": "Join {key}: the walls are in one line or the corner is too sharp for a mitre (limit {limit:g}): both ends stay square",
        "es": "Unión {key}: los muros están en línea o el ángulo es demasiado agudo para un inglete (límite {limit:g}): ambos extremos quedan a escuadra",
    },
    "note_node_complex": {
        "en": "Node near {at}: {count} wall ends meet there; the engine joins two walls only, so those ends stay square",
        "es": "Nodo cerca de {at}: confluyen {count} extremos de muro; el motor une solo dos muros, así que esos extremos quedan a escuadra",
    },
    "note_t_not_through": {
        "en": "Join {key}: the stem does not reach the side of the other wall; it is left as drawn",
        "es": "Unión {key}: el muro no llega al lado del otro muro; se deja como está dibujado",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` (error or note) in both languages with its parameters filled in."""
    entry = MESSAGES.get(code) or NOTES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
