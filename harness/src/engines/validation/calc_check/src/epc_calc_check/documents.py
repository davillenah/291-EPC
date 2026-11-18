"""Group D, cross-document consistency (document-check): the same circuit has the same tag, section, device and Iz in the stage outputs, in the memo document
of stage 15, in the memo summary and in the drawing summary of stage 14.

Only fields that exist in both places are compared; a field in one place only is a note (`CC-D07`). The memo cells are text formatted by the engine
(`board_memo.sig2`, `mm`, `p1`, `mark`): the stage value is formatted with the same functions and the two texts are compared.
"""
import hashlib
import json
import re

from epc_calc_check import view as V
from epc_calc_check._engine import engine
from epc_calc_check._values import num
from epc_calc_check.findings import issue
from epc_calc_check.formats import hash_issues

MEMO = "calculation_memo"
# memo table column -> (stage, key, formatter name of board_memo or None for text)
CABLE_COLUMNS = {"Ib A": (8, "ib_a", "sig2"), "In A": (8, "in_a", "sig2"), "S int. mm²": (8, "s_internal_mm2", "mm"), "S ext. mm²": (8, "s_mm2", "mm"),
                 "Largo m": (9, "length_m", "sig2"), "Iz A": (8, "iz_a", "sig2"), "ΔU %": (9, "own_pct", "p1"), "ΔU acum. %": (9, "accumulated_pct", "p1"),
                 "Límite %": (9, "limit_pct", "p1"), "Cumple": (8, "compliant", "mark")}
PROTECTION_COLUMNS = {"Dispositivo": (11, "device", None), "Curva": (11, "curve", None), "In A": (11, "in_a", "sig2"), "Icu kA": (10, "icu_ka", "sig2"),
                      "Icc mín A": (10, "icc_min_a", "sig2"), "Disparo": (10, "trip_ok", "mark"), "Sobrec.": (11, "overload_ok", "mark"), "I2 A": (8, "i2_a", "sig2"),
                      "Coord.": (11, "coordination_ok", "mark"), "Cumple": (11, "protection_ok", "mark")}
TABLES = (("S ext. mm²", CABLE_COLUMNS), ("Dispositivo", PROTECTION_COLUMNS))
SHARED = (((8, "in_a"), (11, "in_a")), ((8, "overload_ok"), (11, "overload_ok")), ((8, "coordination_ok"), (11, "coordination_ok")),
          ((7, "device"), (11, "device")), ((8, "compliant"), (9, "compliant")), ((7, "parent"), (4, "parent")))
ROUND_1 = 0.0501


def document_hash(doc):
    """The hash stage 15 records: SHA-256 of the document as canonical JSON (sorted keys, UTF-8)."""
    return hashlib.sha256(json.dumps(doc, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _shared(view):
    out = []
    for tag in view.tags():
        for (sa, ka), (sb, kb) in SHARED:
            a, b = view.value(sa, tag, ka), view.value(sb, tag, kb)
            if a is not None and b is not None and a != b:
                out.append(issue("CC-D01", view.slug(sb), f"circuits/{tag}/{kb}", b, a, "The stages must agree; re-run from the earliest stage.", f"stage {sa} {ka} = {a!r}, stage {sb} {kb} = {b!r}"))
    return out


def _ib(view):
    out = []
    for tag in view.tags():
        a, b = view.number(4, tag, "ib_a"), view.number(8, tag, "ib_a")
        if a is not None and b is not None and abs(a - b) > ROUND_1:
            out.append(issue("CC-D01", view.slug(8), f"circuits/{tag}/ib_a", b, a, "The stages must agree; re-run from the earliest stage.", f"stage 4 ib_a = {a}, stage 8 ib_a = {b}"))
    return out


def _memo_doc(view):
    for d in view.outputs(15).get("documents") or []:
        if isinstance(d, dict) and d.get("name") == MEMO and isinstance(d.get("document"), dict):
            return d["document"]
    return None


def _tables(doc):
    """[(first-key column title, columns map, {tag: {column title: cell}})] for the memo tables we know."""
    found = []
    for block in doc.get("blocks") or []:
        if not (isinstance(block, dict) and block.get("type") == "table"):
            continue
        titles = [c[0] for c in block.get("columns") or [] if isinstance(c, (list, tuple)) and c]
        for marker, columns in TABLES:
            if marker in titles and titles[:1] == ["TAG"]:
                rows = {r[0]: dict(zip(titles, r)) for r in block.get("rows") or [] if isinstance(r, list) and r}
                found.append((marker, columns, rows))
    return found


def _format(value, how):
    if how is None:
        return value if isinstance(value, str) else None
    return getattr(engine().MEMO, how)(value)


def _cell_issue(view, tag, title, spec, cell):
    stage, key, how = spec
    value = view.value(stage, tag, key)
    if value is None:
        return None
    expected = _format(value, how)
    if expected is None or str(cell) == str(expected):
        return None
    return issue("CC-D02", MEMO, f"tables/{tag}/{title}", cell, expected, "The memo must show what the stages hold; re-run the documents stage.", f"stage {stage} {key} = {value!r}")


def _memo_table(view, columns, rows):
    out = []
    for tag in view.tags():
        if tag not in rows:
            out.append(issue("CC-D02", MEMO, f"tables/{tag}", None, "a row for the circuit", "The memo lists every circuit.", f"stage 8 lists {tag}"))
            continue
        for title, spec in columns.items():
            if title in rows[tag]:
                found = _cell_issue(view, tag, title, spec, rows[tag][title])
                out += [found] if found else []
    return out


def _memo(view):
    doc = _memo_doc(view)
    if doc is None or not view.rows(8):
        return []
    tables = _tables(doc)
    if not tables:
        return [issue("CC-D07", MEMO, "tables", None, None, "None.", "the memo has no table the checks know, so its values cannot be compared")]
    out = []
    for _, columns, rows in tables:
        out += _memo_table(view, columns, rows)
    return out


def _document_hashes(view):
    return [issue("CC-D03", MEMO if d.get("name") == MEMO else str(d.get("name")), f"documents/{d.get('name')}/sha256", d.get("sha256"), document_hash(d["document"]),
                  "Recompute the hash; the document changed after it was recorded.", "SHA-256 of the canonical JSON of the document")
            for d in view.outputs(15).get("documents") or [] if isinstance(d, dict) and isinstance(d.get("document"), dict) and d.get("sha256") != document_hash(d["document"])]


def _expected_summary(view):
    tags = view.tags()
    ok = []
    for t in tags:
        ok.append(view.value(8, t, "compliant") is True and view.value(11, t, "protection_ok") is True and view.value(12, t, "differential_ok") is not False)
    return {"circuits": len(view.rows(8)), "cumplen": sum(ok), "no_cumplen": len(ok) - sum(ok), "global": all(ok) if ok else None,
            "transiciones": sum(1 for t in tags if view.value(8, t, "transition") is True)}


def _memo_summary(view):
    summary = view.outputs(15).get("memo_summary")
    if not isinstance(summary, dict) or not view.rows(8) or not view.rows(11):
        return []
    out = []
    for key, expected in _expected_summary(view).items():
        if key in summary and summary[key] != expected:
            out.append(issue("CC-D04", "documents", f"memo_summary/{key}", summary[key], expected, "The summary must follow the stages; re-run the documents stage.", "derived from stage 8, 11 and 12 verdicts"))
    return out


def _drop_max(summary):
    lines = [line for line in summary.get("log") or [] if isinstance(line, str)]
    found = [float(m) for line in lines for m in re.findall(r"dU max ([0-9.]+)", line)]
    return max(found, default=None)


def _drawing(view):
    summary = view.outputs(14).get("summary")
    if not isinstance(summary, dict) or not view.rows(8):
        return []
    out = []
    if "circuits" in summary and summary["circuits"] != len(view.rows(8)):
        out.append(issue("CC-D05", "drawings", "summary/circuits", summary["circuits"], len(view.rows(8)), "Re-draw from the current calculation.", "stage 8 row count"))
    bad = sorted(t for t in view.tags() if view.value(8, t, "compliant") is False)
    if isinstance(summary.get("non_compliant"), list) and sorted(summary["non_compliant"]) != bad:
        out.append(issue("CC-D05", "drawings", "summary/non_compliant", summary["non_compliant"], bad, "Re-draw from the current calculation.", "stage 8 compliant flags"))
    return out + _drawing_drop(view, summary)


def _drawing_drop(view, summary):
    shown = _drop_max(summary)
    drops = [num(r.get("du_pct")) for r in view.rows(9)]
    if shown is None or not drops or None in drops or abs(shown - max(drops)) <= ROUND_1 / 5:
        return []
    return [issue("CC-D05", "drawings", "summary/log/dU max", shown, max(drops), "Re-draw from the current calculation.", "largest du_pct of stage 9")]


def _file_bytes(view):
    """Recorded hash of each drawing file against the bytes the caller gave in `files` (keyed by `<directory>/<path>`)."""
    out, directory = [], view.outputs(14).get("directory")
    for f in view.outputs(14).get("files") or []:
        key = f"{directory}/{f.get('path')}" if isinstance(f, dict) else None
        if key in view.files and V.sha256_of(view.files[key]) != f.get("sha256"):
            out.append(issue("CC-D06", "drawings", key, V.sha256_of(view.files[key]), f.get("sha256"), "The file changed after stage 14 recorded it; re-draw.", "SHA-256 of the file bytes"))
    return out


def _notes(view):
    out = []
    summary = view.outputs(14).get("summary")
    if isinstance(summary, dict) and "circuits" not in summary and view.rows(8):
        out.append(issue("CC-D07", "drawings", "summary/circuits", None, None, "None.", "the drawing summary has no circuit count"))
    if view.outputs(15) and not isinstance(view.outputs(15).get("memo_summary"), dict):
        out.append(issue("CC-D07", "documents", "memo_summary", None, None, "None.", "stage 15 has no memo summary"))
    return out


def check_documents(view):
    """Cross-stage and cross-document consistency, and the format of the hashes of stages 14 and 15."""
    for check in (_shared, _ib, _memo, _document_hashes, _memo_summary, _drawing, _file_bytes, _notes):
        yield from check(view)
    yield from hash_issues(view, (14, 15))
