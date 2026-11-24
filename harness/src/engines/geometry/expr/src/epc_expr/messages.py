"""Every error of the engine, in English (source) and Spanish. A message is a code with two templates (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_not_text": {
        "en": "the expression must be a non-empty string (got {value!r})",
        "es": "la expresión debe ser un texto no vacío (recibido {value!r})",
    },
    "err_too_long": {
        "en": "the expression is longer than {limit} characters",
        "es": "la expresión tiene más de {limit} caracteres",
    },
    "err_too_deep": {
        "en": "the expression nests more than {limit} levels",
        "es": "la expresión anida más de {limit} niveles",
    },
    "err_syntax": {
        "en": "syntax error at character {at}: {what}",
        "es": "error de sintaxis en el carácter {at}: {what}",
    },
    "err_unknown_name": {
        "en": "unknown name {name!r}: give it in `variables` or use pi",
        "es": "nombre desconocido {name!r}: indicarlo en `variables` o usar pi",
    },
    "err_unknown_function": {
        "en": "unknown function {name!r} (known: {known})",
        "es": "función desconocida {name!r} (conocidas: {known})",
    },
    "err_arity": {
        "en": "{name} takes {expected} argument(s), got {got}",
        "es": "{name} recibe {expected} argumento(s), recibió {got}",
    },
    "err_division_by_zero": {
        "en": "division by zero",
        "es": "división por cero",
    },
    "err_math_domain": {
        "en": "{name} is not defined for this value ({value:g})",
        "es": "{name} no está definida para este valor ({value:g})",
    },
    "err_not_finite": {
        "en": "the result is not a finite number",
        "es": "el resultado no es un número finito",
    },
    "err_bad_variable": {
        "en": "variable {name!r} must have a name made of letters, digits and _ and a finite number as value (got {value!r})",
        "es": "la variable {name!r} debe tener un nombre de letras, dígitos y _ y un número finito como valor (recibido {value!r})",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
