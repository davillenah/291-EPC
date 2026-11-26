"""The blocks every report is made of, as the writers (`report_pdf`, `report_docx`) take them: headings, paragraphs, bullets, tables (ADR-0043).

Moved from `disciplines/electrical_lv/stages/rendering.py` with the same behaviour."""

PAGE_LABEL = "Page {n} of {total}"


def cell(value):
    """The text of a table cell: empty for None."""
    return "" if value is None else str(value)


def table(columns, rows):
    """A table block with equal column widths; every value becomes text."""
    width = 1.0 / max(len(columns), 1)
    return {"type": "table", "columns": [(str(c), width) for c in columns], "rows": [[cell(v) for v in r] for r in rows]}


def notes(document):
    """The assumptions and the issues a structured document carries, as headings and bullets."""
    out = []
    for key, title in (("assumptions", "Assumptions"), ("issues", "Open issues")):
        if document.get(key):
            out += [{"type": "h", "text": title}, {"type": "bullets", "items": [str(i) for i in document[key]]}]
    return out
