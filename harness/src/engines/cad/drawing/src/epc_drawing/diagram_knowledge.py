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
    """{'sld_symbol', 'mld_symbols', 'ports', 'match', 'status'} of a researched device; sld_symbol None when the library has no symbol.

    The map holds only the device to symbol link; the ports and the MLD variants (`<symbol>_<n>p_mld`) come from the symbol catalogue (one source, COD-03)."""
    for m in _json("puente_motor_dibujo/device_symbol_map.json")["mappings"]:
        if m["device_id"] == device_id:
            return {**m, **_from_catalogue(m["sld_symbol"])}
    raise KeyError(f"no device '{device_id}' in the diagram knowledge")


def _from_catalogue(symbol):
    """Ports and MLD variants of a library symbol id (empty when the device has no symbol)."""
    if symbol is None:
        return {"ports": [], "mld_symbols": []}
    from epc_symbols import registry
    mld = (i.split(".", 1)[1] for i in registry.list_ids(view="mld"))
    variants = sorted(i for i in mld if i.startswith(symbol + "_") and i.endswith("p_mld") and i[len(symbol) + 1:-5].isdigit())
    return {"ports": [t["id"] for t in registry.terminals(symbol)], "mld_symbols": variants}


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


def iec_60617_for(device_id: str) -> dict:
    """The IEC 60617 reference of a researched device (`symbol_ref` of its research file: {'id', 'status', ...}); {'id': 'not_found'} when it has none."""
    for folder in ("sld_mld/devices", "pv_sld_mld/devices"):
        path = root() / folder / f"{device_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8")).get("symbol_ref") or {"id": "not_found"}
    return {"id": "not_found"}


def constraints() -> list:
    """The design constraints on the connections of a board (`model/design_constraints.json`), all typical and unverified."""
    return _json("puente_motor_dibujo/model/design_constraints.json")["constraints"]


def _downstream(model: dict, start: str) -> list:
    """Device ids reachable from the device `start` following the wires of the model (nearest first)."""
    nxt = {}
    for w in model["wires"]:
        nxt.setdefault(w["from"]["ref"], []).append(w["to"]["ref"])
    out, queue = [], list(nxt.get(start, []))
    while queue:
        cur = queue.pop(0)
        if cur not in out:
            out.append(cur)
            queue += nxt.get(cur, [])
    return out


def _poles_violations(c: dict, model: dict, by_id: dict) -> list:
    found = []
    for up in (d for d in model["devices"] if d["device_id"] in c["upstream"] and d.get("poles")):
        for did in _downstream(model, up["id"]):
            d = by_id.get(did)
            if d and d["device_id"] in c["downstream"] and d.get("poles") and d["poles"] > up["poles"]:
                found.append({"constraint": c["id"], "device": d["id"], "upstream": up["id"], "detail": f"{d['poles']}P downstream of {up['poles']}P"})
    return found


def _requires_violations(c: dict, model: dict, by_id: dict) -> list:
    found = []
    for dev in (d for d in model["devices"] if d["device_id"] == c["device"]):
        if not any(by_id[i]["device_id"] in c["requires"] for i in _downstream(model, dev["id"]) if i in by_id):
            found.append({"constraint": c["id"], "device": dev["id"], "upstream": None, "detail": "needs " + "/".join(c["requires"]) + " downstream"})
    return found


_CHECKS = {"poles_downstream_le_upstream": _poles_violations, "requires_downstream": _requires_violations}


def check_constraints(model: dict) -> list:
    """Violations of the design constraints in the netlist `model` (devices, wires): [{constraint, severity, device, upstream, detail, en, es}]. A constraint whose data
    are missing (a device without poles) is not applied, never guessed. Advisory: a person reviews them."""
    by_id = {d["id"]: d for d in model["devices"]}
    out = []
    for c in constraints():
        for v in _CHECKS[c["type"]](c, model, by_id):
            out.append(dict(v, severity=c["severity"], status=c["status"], en=c["message"]["en"], es=c["message"]["es"]))
    return out


BLOCKING = ("blocking", "major")


def audit(model: dict) -> dict:
    """The verdict on a board model: {'verdict': 'ok' | 'not_ok', 'findings': [...], 'status': 'unverified'}.

    The design constraints are checked on the connections (`check_constraints`); 'not_ok' when a finding is blocking or major, 'ok' otherwise (minor findings travel with the verdict). It is the
    only place that decides pass or fail before the assembly (PRD-diagram-flow, step 5); it never changes the model, and no verdict is ever marked verified."""
    findings = check_constraints(model)
    return {"verdict": "not_ok" if any(f["severity"] in BLOCKING for f in findings) else "ok", "findings": findings, "status": "unverified"}

