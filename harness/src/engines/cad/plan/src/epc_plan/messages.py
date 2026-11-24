"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_detail_number": {
        "en": "detail: {key} must be a number above 0",
        "es": "detalle: {key} debe ser un número mayor que 0",
    },
    "err_discipline_invalid": {
        "en": "discipline {profile_id!r} is not valid",
        "es": "la disciplina {profile_id!r} no es válida",
    },
    "err_discipline_unknown": {
        "en": "unknown discipline {profile_id!r}: profiles are {profiles}",
        "es": "disciplina desconocida {profile_id!r}: los perfiles son {profiles}",
    },
    "err_drawing_shape": {
        "en": "the drawing must be an object with schema_version 1.0",
        "es": "el dibujo debe ser un objeto con schema_version 1.0",
    },
    "err_drawing_too_big": {
        "en": "the drawing is too big: up to {max_lines} lines and {max_nodes} nodes",
        "es": "el dibujo es demasiado grande: hasta {max_lines} líneas y {max_nodes} nodos",
    },
    "err_dxf_unreadable": {
        "en": "the DXF cannot be read: it is not a valid DXF file",
        "es": "no se puede leer el DXF: no es un archivo DXF válido",
    },
    "err_dxf_version": {
        "en": "DXF version {version!r} is not available: choose one of {versions}",
        "es": "la versión DXF {version!r} no está disponible: elegir una de {versions}",
    },
    "err_face_vertex": {
        "en": "solid {solid!r}: a face names a vertex that does not exist",
        "es": "sólido {solid!r}: una cara nombra un vértice que no existe",
    },
    "err_id_duplicate": {
        "en": "the id {dup!r} is used twice: ids must be unique",
        "es": "el id {dup!r} se usa dos veces: los ids deben ser únicos",
    },
    "err_level_invalid": {
        "en": "level {level!r} is not valid: use L0 for the ground level, L1, L2... upwards and L-1, L-2... downwards",
        "es": "el nivel {level!r} no es válido: usar L0 para la planta baja, L1, L2... hacia arriba y L-1, L-2... hacia abajo",
    },
    "err_line_kind_unknown": {
        "en": "line {line}: kind {kind!r} does not exist in the discipline {profile_id}",
        "es": "línea {line}: el tipo {kind!r} no existe en la disciplina {profile_id}",
    },
    "err_line_too_long": {
        "en": "line {line} has too many points (up to {max_points})",
        "es": "la línea {line} tiene demasiados puntos (hasta {max_points})",
    },
    "err_line_too_short": {
        "en": "line {line} needs at least two points",
        "es": "la línea {line} necesita al menos dos puntos",
    },
    "err_node_kind_unknown": {
        "en": "node {node}: kind {kind!r} does not exist in the discipline {profile_id}",
        "es": "nodo {node}: el tipo {kind!r} no existe en la disciplina {profile_id}",
    },
    "err_outlet_not_node": {
        "en": "the outlet {outlet!r} is not a node of the drawing",
        "es": "la salida {outlet!r} no es un nodo del dibujo",
    },
    "err_scale_distance": {
        "en": "the real distance of the scale must be greater than zero",
        "es": "la distancia real de la escala debe ser mayor que cero",
    },
    "err_scale_incomplete": {
        "en": "the scale needs two points (p1, p2) and the real distance between them (distance_m)",
        "es": "la escala necesita dos puntos (p1, p2) y la distancia real entre ellos (distance_m)",
    },
    "err_scale_same_point": {
        "en": "the two calibration points are the same point",
        "es": "los dos puntos de calibración son el mismo punto",
    },
    "err_scene_shape": {
        "en": "a scene is an object with schema_version 1.0 and its solids",
        "es": "una escena es un objeto con schema_version 1.0 y sus sólidos",
    },
    "err_section_not_cut": {
        "en": "a section is what `cut` gives",
        "es": "un corte es lo que devuelve `cut`",
    },
    "err_section_plane": {
        "en": "a section is cut by a plane x or y, seen towards + or - of that axis",
        "es": "un corte se hace con un plano x o y, visto hacia + o - de ese eje",
    },
    "err_section_position": {
        "en": "the place of the section plane is a number of metres",
        "es": "la posición del plano de corte es un número de metros",
    },
    "err_solid_no_mesh": {
        "en": "every solid of a scene has a mesh with vertices and faces",
        "es": "cada sólido de una escena tiene una malla con vértices y caras",
    },
    "err_too_many_elements": {
        "en": "too many elements to compare ({count}): the limit is {limit}",
        "es": "demasiados elementos para comparar ({count}): el límite es {limit}",
    },
    "err_supports_spec_invalid": {
        "en": "the supports are not valid: {details}",
        "es": "los soportes no son válidos: {details}",
    },
    "err_tray_kind": {
        "en": "unknown tray kind {kind!r}: the kinds are {kinds}",
        "es": "tipo de bandeja desconocido {kind!r}: los tipos son {kinds}",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
