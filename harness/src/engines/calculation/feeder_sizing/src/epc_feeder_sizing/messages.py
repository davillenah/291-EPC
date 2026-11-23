"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_class_or_counts": {
        "en": "CLASE must be 2 or 5; N_TERNAS and AGRUP_CIRCUITOS must be >= 1",
        "es": "CLASE debe ser 2 o 5; N_TERNAS y AGRUP_CIRCUITOS ≥ 1",
    },
    "err_conductor_field": {
        "en": "conductores[{k}]: '{campo}' is missing",
        "es": "conductores[{k}]: falta '{campo}'",
    },
    "err_conductor_not_object": {
        "en": "conductores[{k}] must be an object",
        "es": "conductores[{k}] debe ser un objeto",
    },
    "err_insulation_invalid": {
        "en": "AISLACION {p!r} is not valid: {aislaciones}",
        "es": "AISLACION {p!r} inválida: {aislaciones}",
    },
    "err_loaded_conductors": {
        "en": "cargados must be 2 or 3",
        "es": "cargados debe ser 2 o 3",
    },
    "err_material_invalid": {
        "en": "MATERIAL {p!r} is not valid: {materiales}",
        "es": "MATERIAL {p!r} inválido: {materiales}",
    },
    "err_method_invalid": {
        "en": "METODO {v!r} is not valid: use one of {opciones}",
        "es": "METODO {v!r} inválido: use uno de {opciones}",
    },
    "err_no_fundamental": {
        "en": "the fundamental is missing (n=1)",
        "es": "falta la fundamental (n=1)",
    },
    "err_no_k_value": {
        "en": "no k value for {clave}",
        "es": "sin valor k para {clave}",
    },
    "err_no_predefined_k": {
        "en": "Combination ({material!r}, {aislacion!r}) has no predefined k; available: {disponibles}. Enter k explicitly.",
        "es": "Combinación ({material!r}, {aislacion!r}) sin k predefinido; disponibles: {disponibles}. Ingresar k explícito.",
    },
    "err_no_resistance": {
        "en": "section {seccion_mm2} has no tabulated resistance",
        "es": "sección {seccion_mm2} sin resistencia tabulada",
    },
    "err_no_resistance_al": {
        "en": "section {s} has no tabulated resistance for Al",
        "es": "sección {s} sin resistencia tabulada para Al",
    },
    "err_no_section_available": {
        "en": "No available section >= {s_min_mm2:.2f} mm²",
        "es": "Ninguna sección disponible ≥ {s_min_mm2:.2f} mm²",
    },
    "err_not_finite_number": {
        "en": "{nombre} must be a finite number (got: {v!r})",
        "es": "{nombre} debe ser un número finito (recibido: {v!r})",
    },
    "err_not_fraction": {
        "en": "{nombre} must be in (0, 1] (got: {v})",
        "es": "{nombre} debe estar en (0, 1] (recibido: {v})",
    },
    "err_number_invalid": {
        "en": "invalid numeric value: {v!r}",
        "es": "valor numérico inválido: {v!r}",
    },
    "err_out_of_range": {
        "en": "{nombre} must be {relacion} 0 (got: {v})",
        "es": "{nombre} debe ser {relacion} 0 (recibido: {v})",
    },
    "err_section_outside_table": {
        "en": "section {seccion_mm2} is outside Table 771.16.I: {opciones}",
        "es": "sección {seccion_mm2} fuera de la Tabla 771.16.I: {opciones}",
    },
    "err_sections_empty": {
        "en": "the list of available sections is empty",
        "es": "La lista de secciones disponibles está vacía",
    },
    "err_sections_repeated": {
        "en": "the table has repeated sections",
        "es": "La tabla tiene secciones repetidas",
    },
    "err_series_invalid": {
        "en": "serie_in must be a non-empty list of rated currents [A]",
        "es": "serie_in debe ser una lista no vacía de corrientes asignadas [A]",
    },
    "err_table_json": {
        "en": "invalid JSON in the table: {e}",
        "es": "JSON inválido en la tabla: {e}",
    },
    "err_table_shape": {
        "en": "the table must be an object with a non-empty list 'conductores'",
        "es": "La tabla debe ser un objeto con la lista no vacía 'conductores'",
    },
    "err_thd_range": {
        "en": "THD must be < 1 p.u.",
        "es": "THD debe ser < 1 p.u.",
    },
    "err_type_invalid": {
        "en": "tipo must be one of {opciones}",
        "es": "tipo debe ser uno de {opciones}",
    },
    "err_xlpe_method": {
        "en": "{metodo} with XLPE has no table in {spec}: use B2 or C",
        "es": "{metodo} con XLPE no tiene tabla en {spec}: use B2 o C",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
