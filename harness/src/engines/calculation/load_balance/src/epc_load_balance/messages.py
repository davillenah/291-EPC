"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_circuit_shape": {
        "en": "circuit #{k} must be a tuple (name, current_A)",
        "es": "El circuito #{k} debe ser una tupla (nombre, corriente_A)",
    },
    "err_circuits_empty": {
        "en": "the circuit list is empty",
        "es": "La lista de circuitos está vacía",
    },
    "err_currents_too_few": {
        "en": "at least 2 currents are required",
        "es": "se requieren al menos 2 corrientes",
    },
    "err_grade_invalid": {
        "en": "grado must be one of {opciones}",
        "es": "grado debe ser uno de {opciones}",
    },
    "err_load_failed": {
        "en": "Load '{nombre}': {e}",
        "es": "Carga '{nombre}': {e}",
    },
    "err_load_shape": {
        "en": "load #{k} must be a dict with the key 'p_w'",
        "es": "La carga #{k} debe ser un dict con la clave 'p_w'",
    },
    "err_loads_empty": {
        "en": "the load list is empty",
        "es": "La lista de cargas está vacía",
    },
    "err_motors_empty": {
        "en": "in_motores_a is empty",
        "es": "in_motores_a vacío",
    },
    "err_phase_count": {
        "en": "n_fases must be an integer >= 1 (got: {n_fases!r})",
        "es": "n_fases debe ser entero ≥ 1 (recibido: {n_fases!r})",
    },
    "err_phases_invalid": {
        "en": "fases must be 1 or 3",
        "es": "fases debe ser 1 o 3",
    },
    "err_standard_invalid": {
        "en": "norma must be '771' or '770'",
        "es": "norma debe ser '771' o '770'",
    },
    "err_type_invalid": {
        "en": "tipo must be one of {opciones} (got: {tipo!r})",
        "es": "tipo debe ser uno de {opciones} (recibido: {tipo!r})",
    },
    "err_voltage_system": {
        "en": "un_v {un_v!r} is not a project system; expected one of {systems} V (230/400 or 220/380)",
        "es": "un_v {un_v!r} no es un sistema del proyecto; se esperaba uno de {systems} V (230/400 o 220/380)",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
