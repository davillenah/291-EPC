"""Reads `harness/knowledge/diagrams`: symbol of a device, decision rules (when to use MCB, MCCB, RCCB...), and an advisory cross-check of a calculated board.

The data are criteria (status unverified / typical / not_found), never numbers of a calculation: nothing here changes a result. The cross-check only returns
notes for a person (EN and ES) and a symbol lookup for the drawing code. The data folder is `EPC_DIAGRAM_KNOWLEDGE` or `harness/knowledge/diagrams`.
"""
import json
import os
import re
from functools import lru_cache
from pathlib import Path

_RULE_FILES = ("sld_mld/decision_rules.json", "pv_sld_mld/pv_decision_rules.json")
_OPS = {"eq": lambda a, b: a == b, "ne": lambda a, b: a != b, "in": lambda a, b: a in b, "gt": lambda a, b: a > b,
        "gte": lambda a, b: a >= b, "lt": lambda a, b: a < b, "lte": lambda a, b: a <= b}
_CLASS = re.compile(r"\b(ACB|MCCB|MCB|RCBO|RCCB|MPCB)\b")


def root() -> Path:
    env = os.environ.get("EPC_DIAGRAM_KNOWLEDGE")
    return Path(env) if env else Path(__file__).resolve().parents[6] / "knowledge" / "diagrams"


@lru_cache(maxsize=None)
def _json(rel: str) -> dict:
    return json.loads((root() / rel).read_text(encoding="utf-8"))


def rules(domain: str = None) -> list:
    """The decision rules of every file, optionally of one `domain` (lv_protection, rcd, dc_protection...)."""
    out = [r for f in _RULE_FILES for r in _json(f)["rules"]]
    return [r for r in out if domain is None or r["domain"] == domain]


def _holds(cond: dict, variables: dict) -> bool:
    """A condition on a variable that was not given is not met (unknown never matches)."""
    name = cond["variable"]
    return name in variables and variables[name] is not None and _OPS[cond["op"]](variables[name], cond["value"])


def matching(variables: dict, domain: str = None) -> list:
    """Rules whose every condition holds for `variables`."""
    return [r for r in rules(domain) if all(_holds(c, variables) for c in r["when"])]


def symbol_for(device_id: str) -> dict:
    """{'sld_symbol', 'mld_symbols', 'ports', 'match', 'status'} of a researched device; sld_symbol None when the library has no symbol."""
    for m in _json("puente_motor_dibujo/device_symbol_map.json")["mappings"]:
        if m["device_id"] == device_id:
            return m
    raise KeyError(f"no device '{device_id}' in the diagram knowledge")


def _device_class(disp: str):
    found = _CLASS.search(disp or "")
    return found.group(1).lower() if found else None


def check_board(calculo: dict) -> list:
    """Advisory notes for a `{tag: {In, disp, ...}}` calculation: the protective device of a circuit differs from the one the LV rules select for its current.

    Only the current is known here, so only rules that depend on the current (and the voltage level) can match; a note is a prompt to review, not an error.
    """
    notes = []
    for tag, c in sorted(calculo.items()):
        cls, current = _device_class(c.get("disp")), c.get("In")
        if cls is None or not isinstance(current, (int, float)):
            continue
        picks = {r["then"]["select"]: r for r in matching({"voltage_level": "LV", "rated_current_a": current}, "lv_protection")}
        if picks and cls not in picks:
            rule = next(iter(picks.values()))
            notes.append({"circuit": tag, "drawn": cls, "rule": rule["id"], "suggested": sorted(picks), "status": rule["status"],
                          "en": f"{tag}: {cls.upper()} drawn for {current} A; rule {rule['id']} ({rule['status']}) selects {', '.join(sorted(picks)).upper()}. Review.",
                          "es": f"{tag}: se dibuja {cls.upper()} para {current} A; la regla {rule['id']} ({rule['status']}) elige {', '.join(sorted(picks)).upper()}. Revisar."})
    return notes
