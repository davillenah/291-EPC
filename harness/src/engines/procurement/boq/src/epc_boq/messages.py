"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_allowance_invalid": {
        "en": "allowance_pct must be a finite number >= 0 (got {value!r})",
        "es": "allowance_pct debe ser un número finito mayor o igual que 0 (recibido {value!r})",
    },
    "err_allowance_required": {
        "en": "allowance_pct is required: give the wastage/allowance percentage of the cable lengths explicitly (0 is allowed)",
        "es": "falta allowance_pct: indicar explícitamente el porcentaje de desperdicio o reserva de las longitudes de cable (0 es válido)",
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
    "err_duplicate_tags": {
        "en": "duplicate circuit tag(s): {tags}",
        "es": "etiqueta(s) de circuito duplicada(s): {tags}",
    },
    "err_equipment_line": {
        "en": "equipment line needs a description and a quantity of zero or more (got {e!r})",
        "es": "una línea de equipo necesita una descripción y una cantidad de cero o más (recibido {e!r})",
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
    "err_round_up_not_boolean": {
        "en": "round_up_m must be true or false (got {round_up_m!r})",
        "es": "round_up_m debe ser verdadero o falso (recibido {round_up_m!r})",
    },
    "err_terminal_count_invalid": {
        "en": "terminal_totals: the count of size {size} must be an integer >= 0 (got {count!r})",
        "es": "terminal_totals: la cantidad del tamaño {size} debe ser un entero mayor o igual que 0 (recibido {count!r})",
    },
    "err_terminal_size_invalid": {
        "en": "terminal_totals: size {size!r} is not a number of mm2 or 'none'",
        "es": "terminal_totals: el tamaño {size!r} no es un número de mm2 ni 'none'",
    },
    "err_terminal_totals_no_sizes": {
        "en": "terminal_totals must have a by_terminal_size object ({{size_mm2: count}})",
        "es": "terminal_totals debe tener un objeto by_terminal_size ({{size_mm2: cantidad}})",
    },
    "err_terminal_totals_not_object": {
        "en": "terminal_totals must be an object (got {got})",
        "es": "terminal_totals debe ser un objeto (recibido {got})",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
