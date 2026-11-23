"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_description_not_drawable": {
        "en": "the description of the floor cannot be drawn: {reason}",
        "es": "no se puede dibujar la descripción de la planta: {reason}",
    },
    "err_dxf_unreadable": {
        "en": "the DXF cannot be read: it is not a valid DXF file",
        "es": "no se puede leer el DXF: no es un archivo DXF válido",
    },
    "err_elevation_side": {
        "en": "the side of an elevation is one of N, S, E, W",
        "es": "el lado de una elevación es uno de N, S, E, O (W)",
    },
    "err_file_kind": {
        "en": "the file is not a DXF, a PDF or an image",
        "es": "el archivo no es un DXF, un PDF ni una imagen",
    },
    "err_image_not_drawing": {
        "en": "the picture is a render or a photo, not a drawing in lines: send the plan as a line drawing, a vector PDF or a DXF",
        "es": "la imagen es un render o una foto, no un dibujo de líneas: enviar el plano como dibujo de líneas, PDF vectorial o DXF",
    },
    "err_image_too_many_strokes": {
        "en": "the image has too many strokes to read: send a cleaner or smaller one",
        "es": "la imagen tiene demasiados trazos para leer: enviar una más limpia o más chica",
    },
    "err_image_unreadable": {
        "en": "the image cannot be read",
        "es": "no se puede leer la imagen",
    },
    "err_no_floors": {
        "en": "no floors to draw",
        "es": "no hay plantas para dibujar",
    },
    "err_no_reader": {
        "en": "no reader for {kind!r}: the kinds are {kinds}",
        "es": "no hay lector para {kind!r}: los tipos son {kinds}",
    },
    "err_no_views": {
        "en": "no views to stack",
        "es": "no hay vistas para apilar",
    },
    "err_pdf_too_many_strokes": {
        "en": "the PDF has too many strokes to read: export the plan with fewer layers or without hatching",
        "es": "el PDF tiene demasiados trazos para leer: exportar el plano con menos capas o sin sombreados",
    },
    "err_pdf_unreadable": {
        "en": "the PDF cannot be read: it may be damaged or protected",
        "es": "no se puede leer el PDF: puede estar dañado o protegido",
    },
    "err_plan_empty": {
        "en": "the plan has no lines to read",
        "es": "el plano no tiene líneas para leer",
    },
    "err_section_no_cut": {
        "en": "the plane {plane} = {at_m:g} m does not cut the building",
        "es": "el plano {plane} = {at_m:g} m no corta el edificio",
    },
    "err_section_plane": {
        "en": "a section is cut by an x plane seen to the E or W, or by a y plane seen to the N or S",
        "es": "un corte se hace con un plano x visto hacia E u O, o con un plano y visto hacia N o S",
    },
    "err_section_position": {
        "en": "the place of the section plane is a number of metres",
        "es": "la posición del plano de corte es un número de metros",
    },
    "err_sheet_no_viewbox": {
        "en": "the sheet SVG has no viewBox",
        "es": "el SVG de la lámina no tiene viewBox",
    },
    "err_sheet_no_zone": {
        "en": "the sheet SVG does not say its usable zone (data-zona-util): it is not an IRAM sheet of epc_titleblock",
        "es": "el SVG de la lámina no indica su zona útil (data-zona-util): no es una lámina IRAM de epc_titleblock",
    },
    "err_sheet_not_xml": {
        "en": "the sheet SVG cannot be read: it is not well-formed XML",
        "es": "no se puede leer el SVG de la lámina: no es XML bien formado",
    },
    "err_style_invalid": {
        "en": "the style change is not valid: {details}",
        "es": "el cambio de estilo no es válido: {details}",
    },
    "err_svg_not_xml": {
        "en": "the SVG cannot be read: it is not well-formed XML",
        "es": "no se puede leer el SVG: no es XML bien formado",
    },
    "err_view_no_units": {
        "en": "the view cannot be drawn: the plan does not say its units or scale",
        "es": "no se puede dibujar la vista: el plano no indica sus unidades ni su escala",
    },
    "err_view_no_walls": {
        "en": "the view cannot be drawn: the plan has no walls",
        "es": "no se puede dibujar la vista: el plano no tiene muros",
    },
    "err_view_not_drawable": {
        "en": "the view cannot be drawn: {reason}",
        "es": "no se puede dibujar la vista: {reason}",
    },
    "err_views_mixed": {
        "en": "only views of one kind are stacked",
        "es": "solo se apilan vistas de un mismo tipo",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
