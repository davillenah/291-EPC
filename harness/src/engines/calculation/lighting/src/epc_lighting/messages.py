"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_above_maximum": {
        "en": "{path}: must be at most {maximum}, got {value}",
        "es": "{path}: debe ser como máximo {maximum}, recibido {value}",
    },
    "err_axis_invalid": {
        "en": "{path}: '{axis}' is not valid: choose 'k' (room index) or 'rcr' (cavity ratio)",
        "es": "{path}: '{axis}' no es válido: elegir 'k' (índice del local) o 'rcr' (relación de cavidad)",
    },
    "err_axis_zero": {
        "en": "the axis of an escape route has no length: give two different points",
        "es": "el eje de una vía de escape no tiene longitud: dar dos puntos distintos",
    },
    "err_band_negative": {
        "en": "the band left out along the walls cannot be negative",
        "es": "la banda que se deja libre junto a las paredes no puede ser negativa",
    },
    "err_band_too_wide": {
        "en": "the band left out along the walls takes the whole room: make it smaller",
        "es": "la banda que se deja libre junto a las paredes ocupa todo el local: hacerla más chica",
    },
    "err_below_minimum": {
        "en": "{path}: must be at least {minimum}, got {value}",
        "es": "{path}: debe ser al menos {minimum}, recibido {value}",
    },
    "err_choice_invalid": {
        "en": "{path}: '{given}' is not valid: choose one of {allowed}",
        "es": "{path}: '{given}' no es válido: elegir uno de {allowed}",
    },
    "err_cu_table_shape": {
        "en": "{path}: must be an object with axis, axis_values, reflectances and values",
        "es": "{path}: debe ser un objeto con axis, axis_values, reflectances y values",
    },
    "err_document_shape": {
        "en": "the JSON document must be an object with luminaires, rooms and/or areas",
        "es": "el documento JSON debe ser un objeto con luminaires, rooms y/o areas",
    },
    "err_id_repeated": {
        "en": "{path}: id '{i}' appears more than once: ids must be unique",
        "es": "{path}: el id '{i}' aparece más de una vez: los ids deben ser únicos",
    },
    "err_input_empty": {
        "en": "the input is empty",
        "es": "la entrada está vacía",
    },
    "err_input_not_json": {
        "en": "the input is not valid JSON: {exc}",
        "es": "la entrada no es JSON válido: {exc}",
    },
    "err_input_not_utf8": {
        "en": "the input is not UTF-8 text: save the JSON document as UTF-8",
        "es": "la entrada no es texto UTF-8: guardar el documento JSON como UTF-8",
    },
    "err_input_type": {
        "en": "the input must be a JSON document (a dict, a str or bytes)",
        "es": "la entrada debe ser un documento JSON (un dict, un str o bytes)",
    },
    "err_list_too_short": {
        "en": "{path}: must be a list with at least {minimum_len} item(s)",
        "es": "{path}: debe ser una lista con al menos {minimum_len} elemento(s)",
    },
    "err_luminaire_undefined": {
        "en": "{path}: '{ref}' is not defined in 'luminaires': defined ids are {defined}",
        "es": "{path}: '{ref}' no está definido en 'luminaires': los ids definidos son {defined}",
    },
    "err_luminaires_empty": {
        "en": "{path}: must be a non-empty list of luminaires {{x_m, y_m}}",
        "es": "{path}: debe ser una lista no vacía de luminarias {{x_m, y_m}}",
    },
    "err_luminaires_too_many": {
        "en": "{path}: has {count} luminaires: up to 2000",
        "es": "{path}: tiene {count} luminarias: hasta 2000",
    },
    "err_material_invalid": {
        "en": "{path}: material '{name}' is not valid: choose one of {allowed} or give a number between 0 and 1",
        "es": "{path}: el material '{name}' no es válido: elegir uno de {allowed} o dar un número entre 0 y 1",
    },
    "err_method_unavailable": {
        "en": "method '{kind}' is not available: choose one of {names}",
        "es": "el método '{kind}' no está disponible: elegir uno de {names}",
    },
    "err_norm_file_unknown": {
        "en": "unknown norm file {folder}/{name}",
        "es": "archivo de norma desconocido {folder}/{name}",
    },
    "err_normal_shape": {
        "en": "{path}: must be 'horizontal' or a vector [nx, ny, nz]",
        "es": "{path}: debe ser 'horizontal' o un vector [nx, ny, nz]",
    },
    "err_normal_zero": {
        "en": "{path}: the normal vector cannot be [0, 0, 0]",
        "es": "{path}: el vector normal no puede ser [0, 0, 0]",
    },
    "err_not_finite": {
        "en": "a non-finite number was produced: check the dimensions and factors in the input",
        "es": "se produjo un número no finito: revisar las dimensiones y los factores de la entrada",
    },
    "err_not_finite_number": {
        "en": "{path}: must be a finite number",
        "es": "{path}: debe ser un número finito",
    },
    "err_not_increasing": {
        "en": "{path}: values must be strictly increasing",
        "es": "{path}: los valores deben ser estrictamente crecientes",
    },
    "err_not_list": {
        "en": "{path}: must be a list",
        "es": "{path}: debe ser una lista",
    },
    "err_not_number": {
        "en": "{path}: must be a number, got {value!r}",
        "es": "{path}: debe ser un número, recibido {value!r}",
    },
    "err_not_object": {
        "en": "{path}: must be an object",
        "es": "{path}: debe ser un objeto",
    },
    "err_not_positive": {
        "en": "{path}: must be greater than 0, got {value}",
        "es": "{path}: debe ser mayor que 0, recibido {value}",
    },
    "err_not_whole_number": {
        "en": "{path}: must be a whole number, got {lamps}",
        "es": "{path}: debe ser un entero, recibido {lamps}",
    },
    "err_number_required": {
        "en": "{path}: '{key}' is required (a number)",
        "es": "{path}: '{key}' es obligatorio (un número)",
    },
    "err_photometry_shape": {
        "en": "{path}: must be an object with gamma_deg and intensity_cd_per_klm (and c_deg for asymmetric luminaires)",
        "es": "{path}: debe ser un objeto con gamma_deg e intensity_cd_per_klm (y c_deg para luminarias asimétricas)",
    },
    "err_point_shape": {
        "en": "{path}: must be a point [x_m, y_m] in metres from the corner of the room",
        "es": "{path}: debe ser un punto [x_m, y_m] en metros desde la esquina del local",
    },
    "err_point_step": {
        "en": "point step must be greater than 0 m",
        "es": "el paso de los puntos debe ser mayor que 0 m",
    },
    "err_points_not_list": {
        "en": "{path}: must be a list of points",
        "es": "{path}: debe ser una lista de puntos",
    },
    "err_reflectances_shape": {
        "en": "{path}: must be [ceiling, walls, floor]",
        "es": "{path}: debe ser [techo, paredes, piso]",
    },
    "err_routes_not_list": {
        "en": "{path}: must be a list of escape routes",
        "es": "{path}: debe ser una lista de vías de escape",
    },
    "err_rows_per_axis": {
        "en": "{path}: needs one row per axis value ({expected}), got {got}",
        "es": "{path}: necesita una fila por valor del eje ({expected}), recibido {got}",
    },
    "err_rows_per_c_plane": {
        "en": "{path}: needs one row per C plane ({expected}), got {got}",
        "es": "{path}: necesita una fila por plano C ({expected}), recibido {got}",
    },
    "err_rule_in_no_norm": {
        "en": "rule {rule_id} is not in any norm of the engine ({norms})",
        "es": "la regla {rule_id} no está en ninguna norma del motor ({norms})",
    },
    "err_rule_not_approved": {
        "en": "rule {rule_id} of {norm_id} is not approved: approve it in the norms review, or give 'target_lux'",
        "es": "la regla {rule_id} de {norm_id} no está aprobada: aprobarla en la revisión de normas, o dar 'target_lux'",
    },
    "err_rule_not_found": {
        "en": "rule {rule_id} of {norm_id} not found or not approved",
        "es": "la regla {rule_id} de {norm_id} no se encontró o no está aprobada",
    },
    "err_rule_not_lux": {
        "en": "rule {rule_id} of {norm_id} is not an illuminance level in lux: choose a rule that is, or give 'target_lux'",
        "es": "la regla {rule_id} de {norm_id} no es un nivel de iluminancia en lux: elegir una regla que lo sea, o dar 'target_lux'",
    },
    "err_schema_version": {
        "en": "{path}: must be '{schema_version}', got {got!r}",
        "es": "{path}: debe ser '{schema_version}', recibido {got!r}",
    },
    "err_surfaces_unknown": {
        "en": "{path}: unknown surface(s) {unknown}: use {allowed}",
        "es": "{path}: superficie(s) desconocida(s) {unknown}: usar {allowed}",
    },
    "err_suspension_mode": {
        "en": "room '{id}': suspension_mode '{suspension_mode}' is not defined for lighting_system '{system}' (UPV table 2 covers {usable}); give suspension_m instead",
        "es": "local '{id}': suspension_mode '{suspension_mode}' no está definido para lighting_system '{system}' (la tabla 2 de la UPV cubre {usable}); dar suspension_m en su lugar",
    },
    "err_suspension_too_long": {
        "en": "room '{id}': suspension_m ({suspension_m}) leaves no height between the luminaires and the work plane; it must be lower than {limit} m (height_m - work_plane_height_m)",
        "es": "local '{id}': suspension_m ({suspension_m}) no deja altura entre las luminarias y el plano de trabajo; debe ser menor que {limit} m (height_m - work_plane_height_m)",
    },
    "err_target_required": {
        "en": "{path}: 'target_lux', 'activity' or 'target_rule' is required: give the maintained illuminance in lux, one of the activity ids {activities}, or the id of an approved rule of a norm",
        "es": "{path}: se requiere 'target_lux', 'activity' o 'target_rule': dar la iluminancia mantenida en lux, uno de los ids de actividad {activities}, o el id de una regla aprobada de una norma",
    },
    "err_text_empty": {
        "en": "{path}: must be a non-empty text, got {raw!r}",
        "es": "{path}: debe ser un texto no vacío, recibido {raw!r}",
    },
    "err_text_required": {
        "en": "{path}: '{key}' is required (a text)",
        "es": "{path}: '{key}' es obligatorio (un texto)",
    },
    "err_ugr_invalid": {
        "en": "ugr_calculated must be a finite number from 0 up, got {calculated!r}",
        "es": "ugr_calculated debe ser un número finito desde 0, recibido {calculated!r}",
    },
    "err_unit_invalid": {
        "en": "{path}: '{unit}' is not valid: choose 'fraction' or 'percent'",
        "es": "{path}: '{unit}' no es válido: elegir 'fraction' o 'percent'",
    },
    "err_values_per_gamma": {
        "en": "{path}: needs one value per gamma angle ({width}), got {got}",
        "es": "{path}: necesita un valor por ángulo gamma ({width}), recibido {got}",
    },
    "err_values_per_reflectance": {
        "en": "{path}: needs one value per reflectance column ({width}), got {got}",
        "es": "{path}: necesita un valor por columna de reflectancia ({width}), recibido {got}",
    },
    "err_work_plane_height": {
        "en": "room '{id}': work_plane_height_m ({work_plane_m}) must be lower than height_m ({height_m})",
        "es": "local '{id}': work_plane_height_m ({work_plane_m}) debe ser menor que height_m ({height_m})",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
