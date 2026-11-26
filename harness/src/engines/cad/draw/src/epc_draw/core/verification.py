"""Read-only verification of a DXF drawing: advisory findings with a rule id that can be switched off, a bilingual text and where the entity is.

Nothing is changed and nothing blocks (a finding is advice, like the problems of the other engines): `verify` reads a document or a file and reports
tiny and zero-length lines, duplicated lines, entities on layers that are not defined, inserts of blocks that are not defined and empty texts. The
smallest acceptable line length is an input in drawing units (EPC sheets are in millimetres); the engine holds no default for it.
"""
import math
from pathlib import Path

from epc_draw.core.errors import DxfError

TOLERANCE = 1e-9
MAX_PER_RULE = 200
ROUND = 6

RULES = {
    "zero-length": {"severity": "error", "en": "Line {handle} on layer {layer} ({where}) has zero length",
                    "es": "La línea {handle} de la capa {layer} ({where}) tiene largo cero"},
    "tiny-line": {"severity": "warning", "en": "Line {handle} on layer {layer} ({where}) is shorter than {min_length:g}: {length:.4g}",
                  "es": "La línea {handle} de la capa {layer} ({where}) es más corta que {min_length:g}: {length:.4g}"},
    "duplicate-line": {"severity": "warning", "en": "Line {handle} on layer {layer} ({where}) repeats another line with the same end points",
                       "es": "La línea {handle} de la capa {layer} ({where}) repite otra línea con los mismos extremos"},
    "undefined-layer": {"severity": "error", "en": "Entity {handle} ({where}) is on layer {layer}, which is not defined in the drawing",
                        "es": "La entidad {handle} ({where}) está en la capa {layer}, que no está definida en el dibujo"},
    "undefined-block": {"severity": "error", "en": "Insert {handle} ({where}) refers to block {block}, which is not defined in the drawing",
                        "es": "La inserción {handle} ({where}) refiere al bloque {block}, que no está definido en el dibujo"},
    "empty-text": {"severity": "warning", "en": "Text {handle} on layer {layer} ({where}) is empty",
                   "es": "El texto {handle} de la capa {layer} ({where}) está vacío"},
}


def _document(source):
    """The ezdxf document of `source`: a document already open, or the path of a DXF file."""
    if isinstance(source, (str, Path)):
        import ezdxf
        return ezdxf.readfile(str(source))
    return source


def _spaces(doc):
    """`(name, entities)` of every layout and every block definition (the logo and the symbols live in blocks)."""
    for layout in doc.layouts:
        yield layout.name, list(layout)
    for block in doc.blocks:
        if not block.name.startswith("*"):
            yield f"block {block.name}", list(block)


def _finding(rule, entity, where, **params):
    layer = entity.dxf.get("layer", "0")
    text = {lang: RULES[rule][lang].format(handle=entity.dxf.handle, layer=layer, where=where, **params) for lang in ("en", "es")}
    return {"rule": rule, "severity": RULES[rule]["severity"], "handle": entity.dxf.handle, "layer": layer, "where": where, "text": text}


def _length(entity):
    a, b = entity.dxf.start, entity.dxf.end
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def _line_findings(entity, where, min_length):
    length = _length(entity)
    if length <= TOLERANCE:
        return [_finding("zero-length", entity, where)]
    if length < min_length:
        return [_finding("tiny-line", entity, where, min_length=min_length, length=length)]
    return []


def _line_key(entity):
    a, b = entity.dxf.start, entity.dxf.end
    ends = sorted([(round(a.x, ROUND), round(a.y, ROUND), round(a.z, ROUND)), (round(b.x, ROUND), round(b.y, ROUND), round(b.z, ROUND))])
    return entity.dxf.get("layer", "0"), tuple(ends)


def _entity_findings(entity, where, doc, seen, min_length):
    kind = entity.dxftype()
    found = []
    if entity.dxf.get("layer", "0") not in doc.layers:
        found.append(_finding("undefined-layer", entity, where))
    if kind == "LINE":
        found += _line_findings(entity, where, min_length)
        key = _line_key(entity)
        if key in seen:
            found.append(_finding("duplicate-line", entity, where))
        seen.add(key)
    elif kind == "INSERT" and entity.dxf.name not in doc.blocks:
        found.append(_finding("undefined-block", entity, where, block=entity.dxf.name))
    elif kind in ("TEXT", "MTEXT") and not (entity.dxf.get("text", "") if kind == "TEXT" else entity.text).strip():
        found.append(_finding("empty-text", entity, where))
    return found


def _check_arguments(min_length, off):
    if not isinstance(min_length, (int, float)) or isinstance(min_length, bool) or not math.isfinite(min_length) or min_length <= 0:
        raise DxfError("err_verify_min_length", value=min_length)
    unknown = sorted(set(off) - set(RULES))
    if unknown:
        raise DxfError("err_verify_unknown_rule", rules=", ".join(unknown))


def _collect(doc, min_length, off):
    """`(findings, entities checked)` over every layout and block, with the switched-off rules left out."""
    findings, checked = [], 0
    for where, entities in _spaces(doc):
        seen = set()
        for entity in entities:
            checked += 1
            findings += [f for f in _entity_findings(entity, where, doc, seen, min_length) if f["rule"] not in off]
    return findings, checked


def _tally(findings, off):
    """`(counts per rule, findings kept (at most MAX_PER_RULE per rule), rules that were cut)`."""
    by_rule = {rule: [f for f in findings if f["rule"] == rule] for rule in RULES if rule not in off}
    counts = {rule: len(items) for rule, items in by_rule.items()}
    kept = [f for items in by_rule.values() for f in items[:MAX_PER_RULE]]
    return counts, kept, sorted(r for r, n in counts.items() if n > MAX_PER_RULE)


def verify(source, *, min_length=None, off=()):
    """`{ok, rules, counts, findings, truncated, entities_checked, min_length}` for a DXF document or file.

    `min_length` (required, drawing units, > 0) is the shortest line that is not reported as tiny. `off` is a set of rule ids to skip. `ok` is true when
    no finding of severity `error` was found. Each rule keeps at most 200 findings; `counts` are exact and `truncated` lists the rules that were cut.
    """
    _check_arguments(min_length, off)
    findings, checked = _collect(_document(source), min_length, off)
    counts, kept, cut = _tally(findings, off)
    return {"ok": not any(f["severity"] == "error" for f in findings), "rules": sorted(counts), "counts": counts, "findings": kept, "truncated": cut,
            "entities_checked": checked, "min_length": float(min_length)}
