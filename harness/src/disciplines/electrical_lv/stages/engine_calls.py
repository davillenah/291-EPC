"""The adapter between the pipeline context and the calculation chain of the engines (MIG-30c).

The discipline calculates nothing. This module (a) builds the board form that `epc_drawing.board_design` reads from the
profile, the load list and the optional `context.engine_inputs`, (b) calls the engines ONCE per run (the result is cached in
`context.engine_cache`) and (c) hands the raw engine result to the stages, which only select slices of it.

Missing data is never defaulted: it raises `StageInputError` (the stage is `blocked` with one finding per reason).

`context.engine_inputs` (all optional, form keys of `board_design`):
  board            {"name", "fp_default", "frequency_hz", "feeder_length_m", "supply_name"}
  circuits         {<load id>: {parent_tag, topology, fp, efficiency, kind, ...}}  (keys in `mappings.OVERRIDE_KEYS`)
  extra_circuits   [circuit form rows]  circuits that are not loads (feeders, groups); every row has a `tag`
  criteria         {design criterion id: value}  (the engine's own table values apply when absent)
  feeders, upstream, titleblock, criteria_validated   passed to the engine as they are
  boq              {"allowance_pct": percent of wastage on cable lengths, 0 allowed}  stage 15 builds the bill of quantities only when it is given (never defaulted)
  datasheets       {"catalog_dir": folder of the manufacturer catalog, "voltage_v": optional voltage for the breaking-capacity comparison}  stage 15 builds the datasheets only when catalog_dir is given
  rfq              {"suppliers": [{"name", "contact"?}], "currency", "response_deadline": ISO date, "delivery_site", "validity_days", "payment_terms"?, "notes"?, "requestable_categories"?}  stage 15 builds the RFQ only when the BOQ was produced and the terms are given (never defaulted)
"""
import copy
import importlib

from disciplines.electrical_lv.stages.base import StageInputError
from disciplines.electrical_lv.stages.mappings import (
    KIND_TAG_PREFIX, KIND_TOPOLOGY, OVERRIDE_KEYS, PHASE_CODE, POWER_UNITS_WITH_FP)

BOARD_OPTIONS = ("frequency_hz", "feeder_length_m", "supply_name")
PASS_THROUGH = ("feeders", "upstream", "titleblock")


def inputs_of(context):
    return context.engine_inputs or {}


def engine_tag(load):
    prefix = KIND_TAG_PREFIX[load["kind"]]
    return load["id"] if load["id"].upper().startswith(prefix) else prefix + load["id"]


def _board(context, errors):
    """The `board` of the form: copied from the profile (verbatim) and from `engine_inputs["board"]`."""
    profile = context.profile or {}
    supply = profile.get("supply") or {}
    extra = inputs_of(context).get("board") or {}
    voltage, level = supply.get("voltage") or {}, supply.get("short_circuit_level") or {}
    for name, got, unit in (("supply.voltage", voltage, "V"), ("supply.short_circuit_level", level, "kA")):
        if got.get("value") is None or got.get("unit") != unit:
            errors.append(f"{name}: a value in {unit} is required by the calculation and has no default")
    board = {"name": extra.get("name") or profile.get("project_code"), "voltage_v": voltage.get("value"), "system": supply.get("earthing_system"),
             "icc_ka": level.get("value"), "project": profile.get("project_code")}
    board.update({k: extra[k] for k in BOARD_OPTIONS if k in extra})
    if extra.get("fp_default") is not None:
        board["fp_default"] = extra["fp_default"]
    return board


def _override(load, overrides, errors):
    row = dict(overrides.get(load["id"]) or {})
    unknown = sorted(set(row) - set(OVERRIDE_KEYS))
    if unknown:
        errors.append(f"{load['id']}: unknown engine input(s) {', '.join(unknown)}")
    return {k: v for k, v in row.items() if k in OVERRIDE_KEYS}


def _length(load, row):
    return row.get("length_m", (load.get("length") or {}).get("value"))


def _circuit(load, overrides, errors):
    """Form row of a load (mapping table + per-load overrides); a datum the engine needs and nobody gave is an error."""
    row = {"tag": engine_tag(load), "description": load["description"], "load": load["power"]["value"], "unit": load["power"]["unit"],
           "phase": PHASE_CODE[load["phases"]], "topology": KIND_TOPOLOGY.get(load["kind"]), "kind": "auto"}
    row.update(_override(load, overrides, errors))
    row["length_m"] = _length(load, row)
    for key, what in (("length_m", "run length (m)"), ("topology", "starter topology")):
        if row.get(key) in (None, ""):
            errors.append(f"{load['id']}: {what} is required by the calculation and has no default")
    return row


def _needs_fp(circuits, board):
    missing = [c["tag"] for c in circuits if c["unit"] in POWER_UNITS_WITH_FP and c.get("fp") is None]
    if missing and board.get("fp_default") is None:
        return [f"board.fp_default: power factor needed for the load(s) in W/kW without their own fp ({', '.join(missing)}); it has no default"]
    return []


def build_form(context):
    """(form, tags, kinds): the board form for `board_design`, {engine tag: load id} and {engine tag: load kind}."""
    errors, loads = [], (context.loads or {}).get("loads") or []
    board = _board(context, errors)
    overrides = inputs_of(context).get("circuits") or {}
    circuits = [_circuit(load, overrides, errors) for load in loads]
    extra = [dict(c) for c in inputs_of(context).get("extra_circuits") or []]
    errors += [f"extra circuit {n}: tag is required" for n, c in enumerate(extra, start=1) if not c.get("tag")]
    errors += _needs_fp(circuits, board)
    if not loads:
        errors.append("loads: the load list is empty")
    if errors:
        raise StageInputError(errors)
    form = {"board": board, "circuits": circuits + extra}
    form.update({k: copy.deepcopy(inputs_of(context)[k]) for k in PASS_THROUGH if k in inputs_of(context)})
    form["validated"] = bool(inputs_of(context).get("criteria_validated", False))
    tags = {c["tag"]: load["id"] for c, load in zip(circuits, loads)}
    kinds = {c["tag"]: load["kind"] for c, load in zip(circuits, loads)}
    return form, tags, kinds


def call_record(engine, function, module):
    """What `StageResult.engine_calls` carries: engine, public function and the version the package exposes."""
    return {"engine": engine, "function": function, "version": getattr(module, "__version__", None)}


def record_for(engine, function):
    """`call_record` of a public function given by its dotted name; the version is the one of its package."""
    return call_record(engine, function, importlib.import_module(function.split(".")[0]))


def _records():
    import epc_aea90364
    import epc_drawing
    aea, draw = "calculation/aea90364", "cad/drawing"
    items = [(draw, "epc_drawing.board_design.groups_in", epc_drawing), (draw, "epc_drawing.board_design.calculate", epc_drawing),
             (aea, "epc_aea90364.aea_pipeline.calculate", epc_aea90364), (aea, "epc_aea90364.board_memo.build", epc_aea90364)]
    return {fn: call_record(engine, fn, mod) for engine, fn, mod in items}


def _run(form, criteria):
    from epc_aea90364 import board_memo
    from epc_drawing import board_design
    data = board_design.groups_in(form, criteria)
    try:
        res = board_design.calculate(data, criteria)
        memo = board_memo.build(data["board"], data["circuits"], res["datos"], res["detalle"], res["limites"], res["conductor"], res["rcd_ma"],
                                upstream=data.get("upstream"), validated=bool(data.get("validated", True)), feeders=res["acometidas"])
    except ValueError as exc:  # the engine refuses the inputs (unit, duplicate tag, parent that does not exist, ...)
        raise StageInputError([str(exc)]) from exc
    return data, res, memo


def chain(context):
    """The raw engine result of the whole board calculation, computed once per run: form, data, calc, memo, tags, kinds, calls."""
    if "chain" not in context.engine_cache:
        form, tags, kinds = build_form(context)
        criteria = inputs_of(context).get("criteria")
        data, res, memo = _run(form, criteria)
        context.engine_cache["chain"] = {
            "form": form, "data": data, "calc": res, "memo": memo, "tags": tags, "kinds": kinds, "criteria": criteria,
            "memo_by_tag": {c["tag"]: c for c in memo["circuits"]}, "calls": _records(), "invocations": 1}
    return context.engine_cache["chain"]


def calls(chain_result, *functions):
    """Engine-call records of the given functions, in the order asked."""
    return [dict(chain_result["calls"][fn]) for fn in functions]
