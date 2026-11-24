"""Every error and every note of the engine, in English (source) and Spanish. A message is a code with two templates (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_not_positive_number": {
        "en": "{name} must be a positive finite number (got {value!r})",
        "es": "{name} debe ser un número finito positivo (recibido {value!r})",
    },
    "err_not_point": {
        "en": "{where} must be a point [x, y] of two finite numbers (got {value!r})",
        "es": "{where} debe ser un punto [x, y] de dos números finitos (recibido {value!r})",
    },
    "err_not_object": {
        "en": "{where} must be an object (got {got})",
        "es": "{where} debe ser un objeto (recibido {got})",
    },
    "err_not_text": {
        "en": "{name} must be a non-empty string (got {value!r})",
        "es": "{name} debe ser un texto no vacío (recibido {value!r})",
    },
    "err_unknown_keys": {
        "en": "{where}: unknown key(s) {keys}",
        "es": "{where}: clave(s) desconocida(s) {keys}",
    },
    "err_walls_empty": {
        "en": "walls must be a non-empty list of wall objects",
        "es": "walls debe ser una lista no vacía de objetos de muro",
    },
    "err_duplicate_ids": {
        "en": "duplicate {what} id(s): {ids}",
        "es": "identificador(es) de {what} duplicado(s): {ids}",
    },
    "err_opening_wall": {
        "en": "opening {id}: there is no wall {wall}",
        "es": "abertura {id}: no existe el muro {wall}",
    },
    "err_opening_range": {
        "en": "opening {id}: it must lie inside its wall (the wall is {length:g} long; from {start:g} to {end:g})",
        "es": "abertura {id}: debe quedar dentro de su muro (el muro mide {length:g}; va de {start:g} a {end:g})",
    },
    "err_ext_side": {
        "en": "{where}: ext_side must be 'left' or 'right' (got {value!r})",
        "es": "{where}: ext_side debe ser 'left' o 'right' (recibido {value!r})",
    },
}

NOTES: Dict[str, Dict[str, str]] = {
    "note_wall_skipped_short": {
        "en": "Wall {id} is not longer than the minimum ({min:g}): it is left out of the dimensions",
        "es": "El muro {id} no es más largo que el mínimo ({min:g}): queda fuera de las cotas",
    },
    "note_wall_skipped_oblique": {
        "en": "Wall {id} is not parallel to an axis: it is left out of the dimensions (only walls along X or Y are dimensioned)",
        "es": "El muro {id} no es paralelo a un eje: queda fuera de las cotas (solo se acotan muros según X o Y)",
    },
    "note_not_done": {
        "en": "Not dimensioned by this engine: interior rooms, grid axes, installation heights and text collisions",
        "es": "Este motor no acota: locales interiores, ejes de cuadrícula, alturas de instalaciones ni colisiones de textos",
    },
    "note_no_walls": {
        "en": "No wall is left to dimension",
        "es": "No queda ningún muro para acotar",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` (error or note) in both languages with its parameters filled in."""
    entry = MESSAGES.get(code) or NOTES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
