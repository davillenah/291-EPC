"""The blocks the structured documents of stage 11 are made of: a paragraph, a list, a table, a gap (a datum the project does not have: `[DEFINIR]`, and who must give it) and a section of them."""


def paragraph(text):
    return {"type": "paragraph", "text": text}


def items(values):
    return {"type": "list", "items": list(values)}


def table(columns, rows):
    return {"type": "table", "columns": list(columns), "rows": [list(r) for r in rows]}


def gap(text, who):
    return {"type": "gap", "text": f"[DEFINIR] {text}", "who": who}


def section(number, title, *blocks):
    return {"id": str(number), "title": title, "blocks": list(blocks)}
