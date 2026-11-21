"""Relational diagram model of ONE board: devices, loads, wires and circuits linked only by stable ids (ADR-0037, knowledge/diagrams).

The model says what connects to what; it holds no value. Sizes, ratings and lengths stay in the calculation and in the cable list (a wire only carries `cable_ref`, the tag
of its row there). The SLD and MLD engines look each id up in its file. Ids are built from the circuit tag and the role (`dev-IUG-01-mcb`), never from a counter, so the same
input always gives the same ids and adding a circuit changes none of the others. The device chain of a circuit comes from the calculation (`disp`, e.g. "MCB > KM > OL (25 A)");
only when it is missing is the typical topology of the circuit kind used (`circuit_topologies.json`). A circuit with `parent` hangs from the last device of its parent (one RCCB
feeding several MCBs). Other disciplines build their own models the same way with their own topology kinds.
"""
import re

from epc_drawing import diagram_knowledge as K

_TOPO = "puente_motor_dibujo/model/circuit_topologies.json"
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _slug(text: str) -> str:
    return _SAFE.sub("-", str(text)).strip("-")


def _topologies() -> dict:
    return K._json(_TOPO)


_POLES = re.compile(r"\b([1-4])P\b", re.IGNORECASE)


def _chain_from_disp(disp, tokens: dict):
    """([device ids], [unmapped tokens], [poles or None]) of a calculation device text such as 'MCB > KM > OL (25 A)' or 'RCCB 4P 63 A 30 mA'."""
    devices, unmapped, poles = [], [], []
    for part in (disp or "").split(">"):
        words = part.split()
        if not words:
            continue
        device = tokens.get(words[0].upper())
        (devices if device else unmapped).append(device or words[0])
        if device:
            found = _POLES.search(part)
            poles.append(int(found.group(1)) if found else None)
    return devices, unmapped, poles


def _ports(device_id: str):
    ports = K.symbol_for(device_id)["ports"]
    top = next((p for p in ports if p.startswith("top")), ports[0] if ports else None)
    bottom = next((p for p in reversed(ports) if p.startswith("bottom")), ports[-1] if ports else None)
    return top, bottom


def build_board_model(board: str, circuits: dict, cable_refs: dict = None) -> dict:
    """{'devices', 'loads', 'wires', 'circuits', 'unmapped'} of the board `board`.

    `circuits` = {tag: {"disp": calculation device text or None, "kind": circuit kind or None, "parent": tag or None, "load_ref": id in the load list or None}};
    `cable_refs` = {tag: tag of the row of the cable list} (default: the circuit tag for the external wire). Deterministic: circuits are taken in tag order."""
    topo, cable_refs = _topologies(), cable_refs or {}
    bus = {"id": f"dev-{_slug(board)}-bus", "tag": f"-{board}", "device_id": "switchboard_tgbt", "symbol": K.symbol_for("switchboard_tgbt")["sld_symbol"], "enclosure": None}
    model = {"devices": [bus], "loads": [], "wires": [], "circuits": [], "unmapped": []}
    last = {}
    for tag in sorted(circuits):
        c = circuits[tag]
        start = last.get(c.get("parent")) or (bus["id"], _ports("switchboard_tgbt")[1] or "bottom")
        last[tag] = _add_circuit(model, board, tag, c, start, topo, cable_refs.get(tag, tag))
    return model


def _device(did, tag, device_id, board, poles):
    """A device of the model; `poles` (2P, 4P) is carried only when the calculation names it."""
    device = {"id": did, "tag": tag, "device_id": device_id, "symbol": K.symbol_for(device_id)["sld_symbol"], "enclosure": board}
    return dict(device, poles=poles) if poles else device


def _add_circuit(model, board, tag, c, start, topo, cable_ref):
    """Adds the devices, the load, the wires and the circuit group of one circuit to `model`; returns the (id, port) its children hang from."""
    slug, kind = _slug(tag), topo["kinds"].get(c.get("kind") or "general", topo["kinds"]["general"])
    chain, bad, poles = _chain_from_disp(c.get("disp"), topo["token_to_device"])
    model["unmapped"] += [{"circuit": tag, "token": t} for t in bad]
    chain, wire_ids, prev = chain or list(kind["chain"]), [], start
    for n, device_id in enumerate(chain, 1):
        did = f"dev-{slug}-{device_id}" + (f"-{n}" if chain.count(device_id) > 1 else "")
        model["devices"].append(_device(did, f"-{tag}.{n}", device_id, board, poles[n - 1] if n <= len(poles) else None))
        wire_ids.append(_link(model, prev, (did, _ports(device_id)[0]), f"wire-{slug}-{n}", "internal", None))
        prev = (did, _ports(device_id)[1])
    has_load = kind["load_symbol"] is not None and c.get("kind") != "feeder"
    if has_load:
        model["loads"].append({"id": f"load-{slug}", "tag": f"-{tag}", "kind": "load", "symbol": kind["load_symbol"], "load_ref": c.get("load_ref")})
        wire_ids.append(_link(model, prev, (f"load-{slug}", "top"), f"wire-{slug}-load", "external", cable_ref))
    model["circuits"].append({"id": f"circ-{slug}", "name": {"en": tag, "es": tag}, "load": f"load-{slug}" if has_load else None, "wires": wire_ids})
    return prev


def _link(model, a, b, wid, zone, cable_ref) -> str:
    """Appends the wire `wid` from end `a` to end `b` (each (id, port)) to the model; returns its id."""
    model["wires"].append({"id": wid, "from": {"ref": a[0], "port": a[1]}, "to": {"ref": b[0], "port": b[1]}, "zone": zone, "cable_ref": cable_ref})
    return wid


def main(argv=None) -> int:
    """`python -m epc_drawing.diagram_model --input boards.json --out DIR`: writes devices/loads/wires/circuits.json of each board of the input to DIR/<board>/.

    The input is {"boards": {board: {"circuits": {...}, "cable_refs": {...}}}} (see `build_board_model`)."""
    import argparse
    import json
    from pathlib import Path
    ap = argparse.ArgumentParser(prog="epc_drawing.diagram_model", description=main.__doc__)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    boards = json.loads(Path(args.input).read_text(encoding="utf-8"))["boards"]
    for board, data in sorted(boards.items()):
        model = build_board_model(board, data["circuits"], data.get("cable_refs"))
        folder = Path(args.out) / _slug(board)
        folder.mkdir(parents=True, exist_ok=True)
        for key in ("devices", "loads", "wires", "circuits"):
            doc = {"schema_version": "1.0", "model_id": _slug(board), "board": board, "status": "typical", key: model[key]}
            (folder / f"{key}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        for u in model["unmapped"]:
            print(f"WARNING {board}/{u['circuit']}: device '{u['token']}' has no mapping; add it to circuit_topologies.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
