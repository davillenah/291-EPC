"""Plain-text letter (Spanish) of a request for quotation, generated only by string templates from the values of the structure.

No number is typed in a template: line numbers, quantities, days and dates all come from the values.
"""
from epc_rfq.build import reference_text

TITLE = "PEDIDO DE COTIZACIÓN {rfq_id}"
BOARD = "Tablero: {board}"
TO = "Dirigido a: {names}"
INTRO = "Se solicita cotizar los siguientes ítems, con las condiciones indicadas."
TERMS_HEAD = "Condiciones"
CURRENCY = "- Moneda de la oferta: {currency}"
DEADLINE = "- Fecha límite de respuesta: {response_deadline}"
SITE = "- Lugar de entrega: {delivery_site}"
VALIDITY = "- Validez de la oferta: {validity_days} días"
PAYMENT = "- Condiciones de pago: {payment_terms}"
NOTES = "- Observaciones: {notes}"
LINES_HEAD = "Ítems solicitados"
LINE = "{line_no}. {description} - cantidad: {quantity} {unit}"
LINE_NO_QUANTITY = "{line_no}. {description} - cantidad: sin definir"
REFERENCE = "   Referencia aceptable: {reference}"
INCOMPLETE = "   Ítem incompleto: {issues}"
INCOMPLETE_NO_ISSUE = "   Ítem incompleto: falta información"
RESPONSE = "Para cada ítem indique: precio unitario, plazo de entrega en días, marca ofrecida y observaciones."
DRAFT = "Borrador sujeto a revisión del ingeniero responsable."


def _terms_lines(terms):
    lines = [CURRENCY.format(**terms), DEADLINE.format(**terms), SITE.format(**terms), VALIDITY.format(**terms)]
    if terms["payment_terms"]:
        lines.append(PAYMENT.format(**terms))
    if terms["notes"]:
        lines.append(NOTES.format(**terms))
    return lines


def _line_lines(ln):
    head = (LINE if ln["quantity"] is not None else LINE_NO_QUANTITY).format(**ln)
    out = [head] + [REFERENCE.format(reference=reference_text(r)) for r in ln["references"]]
    if ln["incomplete"]:
        out.append(INCOMPLETE.format(issues="; ".join(ln["issues"])) if ln["issues"] else INCOMPLETE_NO_ISSUE)
    return out


def rfq_to_text(rfq):
    """The request as a plain-text letter (Spanish), one numbered paragraph per line; a quantity is written with `%g`."""
    shown = [dict(ln, quantity=None if ln["quantity"] is None else f"{ln['quantity']:g}") for ln in rfq["lines"]]
    names = ", ".join(s["name"] for s in rfq["issued_for"])
    out = [TITLE.format(**rfq), BOARD.format(**rfq), TO.format(names=names), "", INTRO, "", TERMS_HEAD] + _terms_lines(rfq["terms"]) + ["", LINES_HEAD]
    for ln in shown:
        out += _line_lines(ln)
    return "\n".join(out + ["", RESPONSE, DRAFT]) + "\n"
