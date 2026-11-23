"""Terminal-block list (planilla de bornes) of one board: pure functions, no I/O (the size table is read lazily by `sizes`).

The engine computes no electrical value. Conductor sections and currents are inputs (outputs of the calculation engines); the engine counts the
conductors of each circuit, orders the circuits as given, numbers the terminals and looks up, by comparison, a terminal size that accepts each section.
"""
import math
import re

from epc_terminal_blocks import sizes
from epc_terminal_blocks.errors import TerminalBlocksError

STRIP_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,15}")
CIRCUIT_KEYS = ("tag", "phases", "s_mm2", "pe_mm2", "neutral_mm2", "description", "device", "in_a")
PENDING = "pending review: terminal sizes are generic values to be verified against the chosen manufacturer catalog"
ASSUMPTIONS = (
    PENDING,
    "one terminal per conductor to terminate; the neutral is terminated when the calculation reports a neutral section, and the PE when it reports a PE section",
    "terminals are numbered in the order of the circuits given, conductors in the order L (L1, L2, L3), N, PE, on one strip",
    "the smallest listed terminal size that accepts the conductor section is assigned; no size is guessed when none accepts it",
    "conductor sections and currents are inputs from the calculation engines; this engine calculates nothing",
    "not modelled: strip splitting, spare terminals, marshalling, terminal accessories, shared terminals and grouping by voltage level")


def _number(value, name, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise TerminalBlocksError("err_not_positive_number", name=name, value=value)
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise TerminalBlocksError("err_not_text", name=name, value=value)
    return value


def _circuit(raw, n):
    """A validated copy of one input circuit (defaults only for the optional text fields)."""
    if not isinstance(raw, dict):
        raise TerminalBlocksError("err_circuit_not_object", n=n, got=type(raw).__name__)
    unknown = sorted(set(raw) - set(CIRCUIT_KEYS))
    if unknown:
        raise TerminalBlocksError("err_circuit_unknown_keys", n=n, keys=', '.join(unknown))
    tag = _text(raw.get("tag"), f"circuit {n}: tag")
    where = f"circuit {tag}"
    if raw.get("phases") not in (1, 3) or isinstance(raw.get("phases"), bool):
        raise TerminalBlocksError("err_phases_not_1_or_3", where=where, value=raw.get('phases'))
    return {"tag": tag, "phases": raw["phases"], "s_mm2": _number(raw.get("s_mm2"), f"{where}: s_mm2"),
            "pe_mm2": _number(raw.get("pe_mm2"), f"{where}: pe_mm2", True), "neutral_mm2": _number(raw.get("neutral_mm2"), f"{where}: neutral_mm2", True),
            "in_a": _number(raw.get("in_a"), f"{where}: in_a", True), "description": str(raw.get("description") or ""), "device": str(raw.get("device") or "")}


def _validate(board_name, circuits, start_strip):
    _text(board_name, "board_name")
    if not isinstance(start_strip, str) or not STRIP_NAME.fullmatch(start_strip):
        raise TerminalBlocksError("err_start_strip_name", start_strip=start_strip)
    if not isinstance(circuits, (list, tuple)) or not circuits:
        raise TerminalBlocksError("err_circuits_empty")
    checked = [_circuit(c, n) for n, c in enumerate(circuits, start=1)]
    tags = [c["tag"] for c in checked]
    duplicates = sorted({t for t in tags if tags.count(t) > 1})
    if duplicates:
        raise TerminalBlocksError("err_duplicate_tags", tags=', '.join(duplicates))
    return checked


def conductors(circuit):
    """[(role, section_mm2)] to terminate: L (single-phase) or L1 L2 L3, then N and PE when the calculation reported their section."""
    roles = ["L"] if circuit["phases"] == 1 else ["L1", "L2", "L3"]
    found = [(role, circuit["s_mm2"]) for role in roles]
    if circuit["neutral_mm2"] is not None:
        found.append(("N", circuit["neutral_mm2"]))
    if circuit["pe_mm2"] is not None:
        found.append(("PE", circuit["pe_mm2"]))
    return found


def _fmt(value):
    return f"{value:g}"


def _terminal(strip, number, role, section, in_a, tag):
    """One terminal: id, conductor role and section, assigned size and the issues found by comparison."""
    size = sizes.accepting_size(section)
    issues = []
    if size is None:
        issues.append(f"no terminal size accepts section {_fmt(section)} mm2")
    elif role not in ("N", "PE") and in_a is not None and size["rated_current_a"] < in_a:
        issues.append(f"terminal rated current {_fmt(size['rated_current_a'])} A is below the circuit current {_fmt(in_a)} A")
    return {"id": f"{strip}:{number}", "role": role, "section_mm2": section, "terminal_size_mm2": size["size_mm2"] if size else None,
            "terminal_rated_a": size["rated_current_a"] if size else None, "issues": [f"{tag}/{role}: {i}" for i in issues]}


def _row(strip, first, circuit):
    terminals = [_terminal(strip, first + k, role, section, circuit["in_a"], circuit["tag"]) for k, (role, section) in enumerate(conductors(circuit))]
    row = {"circuit": circuit["tag"], "description": circuit["description"], "device": circuit["device"], "phases": circuit["phases"],
           "in_a": circuit["in_a"], "conductors": len(terminals), "terminals": terminals, "issues": [i for t in terminals for i in t["issues"]]}
    for key, role in (("neutral_mm2", "neutral"), ("pe_mm2", "PE")):
        if circuit[key] is None:
            row["issues"].append(f"{circuit['tag']}: no {role} section reported, no {role} terminal listed")
    return row


def _count(terminals, key_of):
    counts = {}
    for t in terminals:
        counts[key_of(t)] = counts.get(key_of(t), 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: float(kv[0]) if kv[0] != "none" else math.inf))


def _totals(rows):
    terminals = [t for r in rows for t in r["terminals"]]
    return {"terminals": len(terminals), "by_section": _count(terminals, lambda t: _fmt(t["section_mm2"])),
            "by_terminal_size": _count(terminals, lambda t: "none" if t["terminal_size_mm2"] is None else _fmt(t["terminal_size_mm2"]))}


def build_terminal_list(board_name, circuits, *, start_strip="X1"):
    """The terminal-block list of a board.

    `circuits`: list of {"tag", "phases" (1 or 3), "s_mm2", optional "pe_mm2", "neutral_mm2", "description", "device", "in_a"}, in board order.
    Returns {"board", "strips": [{"strip", "rows"}], "totals", "assumptions", "norm_records", "issues"}; a ValueError names an invalid input.
    """
    checked = _validate(board_name, circuits, start_strip)
    rows, count = [], 0
    for circuit in checked:
        row = _row(start_strip, count + 1, circuit)
        count += row["conductors"]
        rows.append(row)
    return {"board": board_name, "strips": [{"strip": start_strip, "rows": rows}], "totals": _totals(rows), "assumptions": list(ASSUMPTIONS),
            "norm_records": [sizes.RECORD_ID], "issues": [i for r in rows for i in r["issues"]]}


def _flat(board, strip, row, terminal):
    return {"board": board, "strip": strip, "terminal": terminal["id"], "circuit": row["circuit"], "description": row["description"],
            "device": row["device"], "conductors": row["conductors"], "role": terminal["role"], "section_mm2": terminal["section_mm2"],
            "terminal_size_mm2": terminal["terminal_size_mm2"], "terminal_rated_a": terminal["terminal_rated_a"], "issue": "; ".join(terminal["issues"])}


def render_rows(terminal_list):
    """Flat rows (one dict per terminal) for the document builders: no file is written here."""
    return [_flat(terminal_list["board"], s["strip"], row, t) for s in terminal_list["strips"] for row in s["rows"] for t in row["terminals"]]
