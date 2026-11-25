"""Draft bill of quantities (computo) of one board: pure functions, no I/O, no data tables.

Quantities only: the engine holds no price and no cost. Lengths, sections and currents are inputs (outputs of the calculation engines); the engine groups
circuits by specification, sums lengths, applies the wastage factor the caller gives, and counts devices and terminals. A field that was not supplied is
never guessed: the line carries an issue `<tag>: missing <field>`.
"""
import math

from epc_boq import inputs
from epc_boq.errors import BoqError

UNSPECIFIED = "unspecified"
PREFIX = {"cable": "CAB", "protective_device": "DEV", "terminal_block": "TRM", "enclosure": "ENC", "pv_equipment": "PVE", "tray_system": "BAN"}
EQUIPMENT_CATEGORIES = ("pv_equipment", "tray_system")
EQUIPMENT_BASIS = {"pv_equipment": "counted by the plant engine (epc_pv)", "tray_system": "counted by the 3D model take-off of the tray system (epc_plan)"}
DEVICE_FIELDS = ("device_kind", "in_a", "poles", "breaking_capacity_ka")
ASSUMPTIONS = (
    "quantities only: this engine holds no price and no cost; the cost engine is planned for a later phase",
    "cable length per specification = sum of the circuit lengths x (1 + allowance_pct / 100); the allowance is given explicitly by the caller (0 is allowed), never defaulted",
    "a cable specification is the material, the insulation and the conductors of the circuit (phase conductors, and the neutral and PE sections when reported)",
    "the cable length of a circuit is the one the calculation used; no extra length for terminations, bends or drops is added except the stated allowance",
    "one protective device is counted per circuit, taken from the device the calculation selected for it (kind, rated current, poles and breaking capacity); the other elements of a chain (contactors, relays) are not counted",
    "the enclosure is one item per board; its sizing is not modelled",
    "the bill is a draft (D21): descriptions are generated from the specification values and translated by the document builders")


def _fmt(value):
    return f"{value:g}"


def _rank(value):
    """Sort key for an optional number: unspecified first."""
    return -1 if value is None else value


def _label(value, kind, upper=False):
    if value is None:
        return f"{kind} unspecified"
    return value.upper() if upper else value.capitalize()


def _cable_spec(circuit):
    conductors = 1 if circuit["phases"] == 1 else 3
    cores = conductors + (circuit["neutral_mm2"] is not None) + (circuit["pe_mm2"] is not None)
    return {"material": circuit["material"], "insulation": circuit["insulation"], "phase_conductors": conductors, "s_mm2": circuit["s_mm2"],
            "neutral_mm2": circuit["neutral_mm2"], "pe_mm2": circuit["pe_mm2"], "cores": cores}


def _cable_key(spec):
    return (spec["material"] or UNSPECIFIED, spec["insulation"] or UNSPECIFIED, spec["phase_conductors"], spec["s_mm2"], _rank(spec["neutral_mm2"]), _rank(spec["pe_mm2"]))


def _cable_text(spec):
    text = f"{_label(spec['material'], 'material')} {_label(spec['insulation'], 'insulation', True)} cable {spec['phase_conductors']}x{_fmt(spec['s_mm2'])} mm2"
    if spec["neutral_mm2"] is not None:
        text += f" + N {_fmt(spec['neutral_mm2'])} mm2"
    if spec["pe_mm2"] is not None:
        text += f" + PE {_fmt(spec['pe_mm2'])} mm2"
    return f"{text} ({spec['cores']} cores)"


def _cable_issues(members):
    issues = []
    for c in members:
        issues += [f"{c['tag']}: missing {field}" for field in ("material", "insulation") if c[field] is None]
        if c["length_m"] is None:
            issues.append(f"{c['tag']}: missing length_m (circuit not counted)")
    return issues


def _gross(net, allowance_pct, round_up_m):
    gross = round(net * (1 + allowance_pct / 100), 6)
    return math.ceil(gross) if round_up_m else gross


def _cables(circuits, allowance_pct, round_up_m):
    """(cable lines without ids, issues): one line per distinct specification that has at least one circuit length."""
    groups = {}
    for c in circuits:
        spec = _cable_spec(c)
        groups.setdefault(_cable_key(spec), (spec, []))[1].append(c)
    lines, issues = [], []
    for key in sorted(groups):
        spec, members = groups[key]
        found = _cable_issues(members)
        issues += found
        counted = [c for c in members if c["length_m"] is not None]
        if counted:
            net = round(sum(c["length_m"] for c in counted), 6)
            rule = f"sum of circuit lengths ({_fmt(net)} m) x (1 + {_fmt(allowance_pct)} %)" + (", rounded up to the next whole metre" if round_up_m else "")
            lines.append(("cable", _cable_text(spec), "m", _gross(net, allowance_pct, round_up_m), [c["tag"] for c in counted], rule, spec, found))
    return lines, issues


def _device_spec(circuit):
    return {"kind": circuit["device_kind"], "in_a": circuit["in_a"], "poles": circuit["poles"], "breaking_capacity_ka": circuit["breaking_capacity_ka"]}


def _device_key(spec):
    return (spec["kind"] or UNSPECIFIED, _rank(spec["in_a"]), _rank(spec["poles"]), _rank(spec["breaking_capacity_ka"]))


def _device_text(spec):
    kind = spec["kind"].upper() if spec["kind"] else "unspecified-kind"
    parts = [f"{kind} protective device",
             f"{_fmt(spec['in_a'])} A" if spec["in_a"] is not None else "rated current unspecified",
             f"{spec['poles']} poles" if spec["poles"] is not None else "poles unspecified",
             f"{_fmt(spec['breaking_capacity_ka'])} kA breaking capacity" if spec["breaking_capacity_ka"] is not None else "breaking capacity unspecified"]
    return ", ".join(parts)


def _device_issues(circuit):
    return [f"{circuit['tag']}: missing {name}" for name in DEVICE_FIELDS if circuit[name] is None]


def _devices(circuits):
    """(device lines without ids, issues): a circuit with no device data at all gets one issue and no line."""
    groups, issues = {}, []
    for c in circuits:
        found = _device_issues(c)
        if len(found) == len(DEVICE_FIELDS):
            issues.append(f"{c['tag']}: missing device")
            continue
        issues += found
        spec = _device_spec(c)
        groups.setdefault(_device_key(spec), (spec, []))[1].append(c)
    lines = []
    for key in sorted(groups):
        spec, members = groups[key]
        found = sorted({i for c in members for i in _device_issues(c)})
        lines.append(("protective_device", _device_text(spec), "un", len(members), [c["tag"] for c in members],
                      "one device per circuit, as selected by the calculation", spec, found))
    return lines, issues


def _terminals(by_size):
    """(terminal lines without ids, issues) from `{size_mm2: count}`: sizes in numeric order, `none` (no size assigned) reported and not counted."""
    lines, issues = [], []
    for size in sorted((s for s in by_size if s != "none"), key=float):
        if by_size[size]:
            lines.append(("terminal_block", f"Terminal block, {_fmt(float(size))} mm2", "un", by_size[size], [],
                          "terminal-block list totals (by_terminal_size)", {"size_mm2": float(size)}, []))
    if by_size.get("none"):
        issues.append(f"{by_size['none']} terminal(s) have no assigned terminal size (not counted)")
    return lines, issues


def _numbered(lines):
    """Lines with deterministic ids: category order, then the order the builders produced (sorted by specification), numbered per category."""
    order = {cat: n for n, cat in enumerate(PREFIX)}
    counters, items = {}, []
    for category, description, unit, quantity, source, basis, spec, issues in sorted(lines, key=lambda line: order[line[0]]):
        counters[category] = counters.get(category, 0) + 1
        items.append({"item_id": f"{PREFIX[category]}-{counters[category]:03d}", "category": category, "description": description, "unit": unit,
                      "quantity": quantity, "source": sorted(source), "basis": basis, "spec": spec, "issues": issues})
    return items


def _totals(items):
    cables = [i["quantity"] for i in items if i["category"] == "cable"]
    return {"lines": len(items), "cable_m": round(sum(cables), 6), "devices": sum(i["quantity"] for i in items if i["category"] == "protective_device")}


def _equipment_category(e):
    """The category of an equipment line: `pv_equipment` unless it names another of `EQUIPMENT_CATEGORIES`."""
    category = e.get("category", "pv_equipment")
    if category not in EQUIPMENT_CATEGORIES:
        raise BoqError("err_equipment_line", e=e)
    return category


def _equipment_valid(e):
    """An equipment line is an object with a description and a quantity of zero or more."""
    return isinstance(e, dict) and bool(e.get("description")) and not isinstance(e.get("quantity"), bool) and isinstance(e.get("quantity"), (int, float)) and e["quantity"] >= 0


def _equipment_lines(equipment):
    """Lines for equipment counted by another engine (the photovoltaic plant: modules, strings, inverters; the tray system: trays, fittings, supports): `[{"description", "unit", "quantity", "source"?,
    "category"?, "basis"?}]`, quantities as the engine counted them."""
    lines = []
    for e in equipment or []:
        if not _equipment_valid(e):
            raise BoqError("err_equipment_line", e=e)
        category = _equipment_category(e)
        lines.append((category, str(e["description"]), str(e.get("unit") or "un"), e["quantity"], list(e.get("source") or []), str(e.get("basis") or EQUIPMENT_BASIS[category]), {}, []))
    return lines


def build_boq(board_name, circuits, *, allowance_pct=None, terminal_totals=None, round_up_m=False, equipment=None):
    """The draft bill of quantities of a board (quantities only).

    `circuits`: list of {"tag", "phases" (1 or 3), "s_mm2", optional "neutral_mm2", "pe_mm2", "length_m", "material", "insulation", "device_kind", "in_a",
    "poles", "breaking_capacity_ka", "description", "device"}. `allowance_pct` is REQUIRED (percent of wastage on cable lengths, 0 allowed).
    `terminal_totals`: optional totals of a terminal-block list ({"by_terminal_size": {"2.5": 4, ...}}). `round_up_m`: round each cable length up to a whole metre. `equipment`: optional lines counted by another engine (the PV plant) as {description, unit, quantity, source}.
    Returns {"board", "allowance_pct", "round_up_m", "items", "totals", "assumptions", "norm_records", "issues"}; a ValueError names an invalid input.
    """
    allowance = inputs.allowance(allowance_pct)
    inputs.text(board_name, "board_name")
    if not isinstance(round_up_m, bool):
        raise BoqError("err_round_up_not_boolean", round_up_m=round_up_m)
    checked = inputs.circuits(circuits)
    by_size = inputs.terminal_totals(terminal_totals)
    cables, cable_issues = _cables(checked, allowance, round_up_m)
    devices, device_issues = _devices(checked)
    terminals, terminal_issues = _terminals(by_size)
    enclosure = [("enclosure", f"Enclosure/board {board_name} (sizing not modelled)", "un", 1, [c["tag"] for c in checked], "one enclosure per board",
                  {"board": board_name}, [])]
    items = _numbered(cables + devices + terminals + enclosure + _equipment_lines(equipment))
    assumptions = list(ASSUMPTIONS) + ([] if by_size else ["terminal blocks are not included: no terminal-block totals were given"])
    return {"board": board_name, "allowance_pct": allowance, "round_up_m": round_up_m, "items": items, "totals": _totals(items), "assumptions": assumptions,
            "norm_records": [], "issues": sorted(set(cable_issues + device_issues + terminal_issues))}


def render_rows(boq):
    """Flat rows (one dict per line) for the document builders: no file is written here."""
    return [{"board": boq["board"], "item_id": i["item_id"], "category": i["category"], "description": i["description"], "unit": i["unit"],
             "quantity": i["quantity"], "source": ", ".join(i["source"]), "basis": i["basis"], "issue": "; ".join(i["issues"])} for i in boq["items"]]
