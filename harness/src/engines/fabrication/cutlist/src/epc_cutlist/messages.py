"""Every error and every user-visible note of the engine, in English (source) and Spanish. A message is a code with two templates (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_angle_invalid": {
        "en": "{where}: {name} must be a number from -90 to 90 degrees, 0 being a square cut (got {value!r})",
        "es": "{where}: {name} debe ser un número de -90 a 90 grados, siendo 0 un corte a escuadra (recibido {value!r})",
    },
    "err_angle_source_invalid": {
        "en": "{where}: angle_source must be 'given', 'derived' or 'unknown' (got {value!r})",
        "es": "{where}: angle_source debe ser 'given', 'derived' o 'unknown' (recibido {value!r})",
    },
    "err_duplicate_part_ids": {
        "en": "duplicate part id(s): {ids}",
        "es": "identificador(es) de pieza duplicado(s): {ids}",
    },
    "err_kerf_invalid": {
        "en": "kerf_mm must be a finite number >= 0 (got {value!r})",
        "es": "kerf_mm debe ser un número finito mayor o igual que 0 (recibido {value!r})",
    },
    "err_kerf_required": {
        "en": "kerf_mm is required: give the saw kerf (cut width) in mm explicitly (0 is allowed, e.g. for cutting cable)",
        "es": "falta kerf_mm: indicar explícitamente el ancho de corte de la sierra en mm (0 es válido, por ejemplo al cortar cable)",
    },
    "err_not_integer": {
        "en": "{name} must be a whole number >= 1 (got {value!r})",
        "es": "{name} debe ser un entero mayor o igual que 1 (recibido {value!r})",
    },
    "err_not_object": {
        "en": "{where} must be an object (got {got})",
        "es": "{where} debe ser un objeto (recibido {got})",
    },
    "err_not_positive_number": {
        "en": "{name} must be a positive finite number (got {value!r})",
        "es": "{name} debe ser un número finito positivo (recibido {value!r})",
    },
    "err_not_text": {
        "en": "{name} must be a non-empty string (got {value!r})",
        "es": "{name} debe ser un texto no vacío (recibido {value!r})",
    },
    "err_parts_empty": {
        "en": "parts must be a non-empty list of part objects",
        "es": "parts debe ser una lista no vacía de objetos de pieza",
    },
    "err_part_too_long": {
        "en": "part {part}: length {length} mm plus kerf ({cut} mm) does not fit in the longest stock of {material} ({longest} mm); add a longer stock or shorten the part",
        "es": "pieza {part}: el largo {length} mm más el corte ({cut} mm) no entra en el stock más largo de {material} ({longest} mm); agregar un stock más largo o acortar la pieza",
    },
    "err_stock_empty": {
        "en": "stock must be a non-empty object: {{material: [stock length, ...]}}",
        "es": "stock debe ser un objeto no vacío: {{material: [largo de stock, ...]}}",
    },
    "err_stock_exhausted": {
        "en": "part {part}: the {material} stock available (counts given) is used up before this part is placed",
        "es": "pieza {part}: el stock disponible de {material} (según las cantidades indicadas) se agota antes de ubicar esta pieza",
    },
    "err_stock_missing_material": {
        "en": "part {part}: there is no stock for material {material!r}",
        "es": "pieza {part}: no hay stock para el material {material!r}",
    },
    "err_unknown_keys": {
        "en": "{where}: unknown key(s) {keys}",
        "es": "{where}: clave(s) desconocida(s) {keys}",
    },
}

#: The legend of the cut-angle marks, shown with the cut list. Both languages are always present.
MARKS_LEGEND: Dict[str, Dict[str, str]] = {
    "-": {
        "en": "Both ends are cut in the same direction (no need to turn the bar over when cutting)",
        "es": "Ambos extremos se cortan en la misma dirección (no hace falta dar vuelta la barra al cortar)",
    },
    "~": {
        "en": "An angle was derived from another part: check length, angles and cut direction",
        "es": "Un ángulo se dedujo a partir de otra pieza: verificar largo, ángulos y dirección del corte",
    },
    "?": {
        "en": "The angle could not be determined: define it before cutting",
        "es": "No se pudo determinar el ángulo: definirlo antes de cortar",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}

#: The assumptions stated with every result, in both languages.
ASSUMPTIONS = (
    {"en": "one-dimensional cutting plan by best fit decreasing: parts from the longest to the shortest, each into the open bar that leaves the least waste, else a new bar of the shortest stock that holds it; a heuristic, not a proven optimum",
     "es": "plan de corte unidimensional por mejor ajuste decreciente: piezas de la más larga a la más corta, cada una en la barra abierta que deja menos sobrante, o en una barra nueva del stock más corto que la contiene; es una heurística, no un óptimo demostrado"},
    {"en": "every cut consumes the kerf, including the last one of a bar (conservative)",
     "es": "cada corte consume el ancho de corte, incluido el último de cada barra (criterio conservador)"},
    {"en": "lengths are the net lengths given by the caller; the engine adds no allowance, no trim and no end loss",
     "es": "los largos son los netos indicados por quien llama; el motor no agrega reserva, descarte ni pérdida de extremo"},
    {"en": "angles are measured from a square cut, signed, and are inputs: the engine never calculates a cut angle",
     "es": "los ángulos se miden desde un corte a escuadra, con signo, y son datos de entrada: el motor nunca calcula un ángulo de corte"},
    {"en": "the plan is a draft (D21) until the person checks it",
     "es": "el plan es un borrador (D21) hasta que la persona lo verifique"},
)
