"""The audit of a set of reports (ADR-0043): finds inconsistencies in the documents and runs the correct-and-recheck loop, at most five times.

Pure functions. A report is the dict the writers take (`title`, `blocks`, ...). A report may also carry `facts`: the values it states, by a stable key (for
example `{"pv.dc_kwp": 12.4}`), so the same quantity can be compared between documents. The audit reads nothing and writes nothing: the corrector is a function the
caller gives, and it can only return new report dicts, so a correction never reaches outside the report engine.
"""
MAX_ITERATIONS = 5
PLACEHOLDERS = ("[DEFINIR]", "[VERIFICAR]", "[SUPUESTO", "TODO", "TBD", "XXX")
_TEXT_KEYS = ("text", "title", "caption")


def finding(code, severity, doc, where, en, es):
    """One finding: what is wrong, where, in English and Spanish."""
    return {"code": code, "severity": severity, "doc": doc, "where": where, "en": en, "es": es}


def _texts(block):
    out = [str(block[k]) for k in _TEXT_KEYS if block.get(k)]
    out += [str(i) for i in block.get("items", [])]
    for row in block.get("rows", []):
        out += [str(v) for v in row]
    return out


def _check_report(rep, index):
    name = rep.get("title") or f"report {index + 1}"
    out = []
    if not rep.get("title"):
        out.append(finding("missing_title", "error", name, "title", "The report has no title.", "El informe no tiene título."))
    if not rep.get("blocks"):
        out.append(finding("empty_report", "error", name, "blocks", "The report has no content.", "El informe no tiene contenido."))
    seen = set()
    for n, b in enumerate(rep.get("blocks", [])):
        where = f"block {n + 1}"
        kind = b.get("type")
        if kind == "h":
            if not b.get("text"):
                out.append(finding("empty_heading", "error", name, where, "A heading has no text.", "Un título no tiene texto."))
            elif b["text"] in seen:
                out.append(finding("duplicate_heading", "warning", name, where, f"The heading '{b['text']}' appears twice.", f"El título '{b['text']}' aparece dos veces."))
            seen.add(b.get("text"))
            nxt = rep["blocks"][n + 1] if n + 1 < len(rep["blocks"]) else None
            if nxt is None or nxt.get("type") == "h":
                out.append(finding("empty_section", "warning", name, where, f"The section '{b.get('text', '')}' has no content.", f"La sección '{b.get('text', '')}' no tiene contenido."))
        if kind == "table":
            width = len(b.get("columns", []))
            if not b.get("rows") and not b.get("empty"):
                out.append(finding("empty_table", "warning", name, where, "A table has no rows and no empty-table text.", "Una tabla no tiene filas ni texto de tabla vacía."))
            for r, row in enumerate(b.get("rows", [])):
                if len(row) != width:
                    out.append(finding("row_width", "error", name, f"{where}, row {r + 1}", f"A row has {len(row)} cells and the table has {width} columns.", f"Una fila tiene {len(row)} celdas y la tabla tiene {width} columnas."))
        for t in _texts(b):
            for p in PLACEHOLDERS:
                if p in t:
                    out.append(finding("placeholder", "warning", name, where, f"Unresolved placeholder {p}.", f"Marcador sin resolver {p}."))
                    break
            if "nan" == t.strip().lower() or "None" == t.strip():
                out.append(finding("bad_value", "error", name, where, f"A value reads '{t.strip()}'.", f"Un valor dice '{t.strip()}'."))
    return out


def _check_facts(reports):
    """The same fact with different values in two documents."""
    seen, out = {}, []
    for i, rep in enumerate(reports):
        name = rep.get("title") or f"report {i + 1}"
        for key, value in (rep.get("facts") or {}).items():
            if key in seen and not _same(seen[key][1], value):
                out.append(finding("fact_mismatch", "error", name, key, f"'{key}' is {value} here and {seen[key][1]} in '{seen[key][0]}'.", f"'{key}' vale {value} aquí y {seen[key][1]} en '{seen[key][0]}'."))
            seen.setdefault(key, (name, value))
    return out


def _same(a, b):
    try:
        return abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(float(a)), abs(float(b)))
    except (TypeError, ValueError):
        return a == b


def audit(reports):
    """All the findings of a set of reports, in the order of the documents."""
    out = []
    for i, rep in enumerate(reports):
        out += _check_report(rep, i)
    return out + _check_facts(reports)


def audit_loop(reports, corrector, max_iterations=MAX_ITERATIONS):
    """Audit, correct, audit again; stops when no error is left, when the corrector changes nothing, or after `max_iterations` (never more than five).

    `corrector(reports, findings)` returns the corrected list of report dicts. Returns `{"reports", "findings", "iterations", "clean"}`; `findings` are those left."""
    limit = min(int(max_iterations), MAX_ITERATIONS)
    current, found, done = list(reports), audit(reports), 0
    while done < limit and any(f["severity"] == "error" for f in found):
        new = corrector(current, found)
        done += 1
        if new == current:
            break
        current, found = list(new), audit(new)
    return {"reports": current, "findings": found, "iterations": done, "clean": not any(f["severity"] == "error" for f in found)}
