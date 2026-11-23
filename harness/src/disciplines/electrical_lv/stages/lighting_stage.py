"""Slice 17 of stage 3 (lighting calculation of the rooms), optional.

The discipline calculates nothing: it hands the `lighting` section of `context.engine_inputs` to `epc_lighting.run` and returns what comes back.
The section is `{"document": <input document of epc_lighting>, "options": {<epc_lighting.Options fields>}}`; `options` is optional, `document`
carries the luminaires, rooms and exterior areas with every datum the engine asks for (nothing is defaulted here). It is the lighting counterpart of
the transformer inputs of stage 4: the data of a room (size, height, activity, luminaire) cannot come from the load list, which only holds watts.

  no `lighting` section   the slice is not available and the stage goes on without it (`optional`, see `grouped.py`)
  invalid section         `blocked` with the engine's message (or the unknown key); the grouped stage adds the `lighting:` prefix
  valid section           `ok`: the engine result as it is, one engine call, a `major` finding for every room or area whose mean illuminance
                          does not reach its target, and one `note` finding per engine warning (draft, D21)

The result does NOT change the load list: the power of the lighting circuits is still the one of `loads.csv`. To compare both, the section may also carry
`loads` ({load id: [room ids]}) and `tolerance_pct` (required with `loads`, never defaulted): the installed power of those rooms is compared with the power of
the load (units W or kW only) and `outputs["load_check"]` lists each pair; a pair that differs by more than the tolerance is a `major` finding.
"""
from disciplines.electrical_lv import lux_map
from disciplines.electrical_lv.stages import engine_calls as EC
from disciplines.electrical_lv.stages.base import Stage, StageInputError, engine_finding, reason

ENGINE = "calculation/lighting"
FUNCTION = "epc_lighting.run"
KEYS = ("document", "options", "loads", "tolerance_pct")
POWER_TO_W = {"W": 1.0, "kW": 1000.0}
NOT_PROVIDED = "lighting inputs not provided"


def warning_finding(n, run_id, slug, text):
    """A note-severity finding that states one warning of the engine."""
    return {"id": f"F-{n:04d}", "run_id": run_id, "verifier": "calc-check", "severity": "note", "document": slug, "field": "warning",
            "value": text, "expected": "reviewed by the engineer of record", "clause": "engine warning", "action": "Review the warning or correct the input.",
            "evidence": [f"engine {FUNCTION}"], "status": "open"}


def _section(context):
    section = (context.engine_inputs or {}).get("lighting")
    if section is None:
        return None
    if not isinstance(section, dict) or not isinstance(section.get("document"), (dict, str, bytes)):
        raise StageInputError(["must be an object with `document` (the epc_lighting input) and optional `options`"])
    unknown = sorted(set(section) - set(KEYS))
    if unknown:
        raise StageInputError([f"unknown input(s) {', '.join(unknown)}"])
    if not isinstance(section.get("options", {}), dict):
        raise StageInputError(["`options` must be an object"])
    return section


def _room_ids(ids):
    return isinstance(ids, list) and bool(ids) and all(isinstance(r, str) for r in ids)


def _loads_shape_error(loads, tol):
    """The error of a malformed `loads` / `tolerance_pct` pair, or None."""
    if not (isinstance(loads, dict) and loads and all(map(_room_ids, loads.values()))):
        return "`loads` must be an object {load id: [room ids]}"
    if isinstance(tol, bool) or not isinstance(tol, (int, float)) or tol < 0:
        return "`tolerance_pct` is required with `loads` (a number >= 0; it has no default)"
    return None


def _check_loads(section, context):
    """Errors of the `loads` / `tolerance_pct` pair (empty when they are fine or absent)."""
    loads, tol = section.get("loads"), section.get("tolerance_pct")
    if loads is None and tol is None:
        return []
    shape = _loads_shape_error(loads, tol)
    if shape:
        return [shape]
    return _load_list_errors(loads, {load["id"]: load for load in (context.loads or {}).get("loads") or []})


def _load_list_errors(loads, known):
    """The mapped loads that are not in the load list or whose power unit cannot be compared."""
    errors = [f"`loads`: {i} is not in the load list" for i in loads if i not in known]
    errors += [f"`loads`: {i} has power in {known[i]['power']['unit']}; only W and kW can be compared" for i in loads if i in known and known[i]["power"]["unit"] not in POWER_TO_W]
    return errors


def load_check(section, result, loads):
    """[{load, load_w, calculated_w, difference_pct, within_tolerance}]: the power of each mapped load against the installed power of its rooms."""
    installed = {r["id"]: r["energy"]["installed_power_w"] for r in result["rooms"]}
    missing = sorted({r for ids in section["loads"].values() for r in ids} - set(installed))
    if missing:
        raise StageInputError([f"`loads`: room(s) {', '.join(missing)} are not in the lighting document"])
    by_id = {load["id"]: load for load in loads}
    rows = []
    for lid, ids in section["loads"].items():
        power = by_id[lid]["power"]
        load_w, calc_w = power["value"] * POWER_TO_W[power["unit"]], sum(installed[r] for r in ids)
        diff = 100.0 * (calc_w - load_w) / load_w if load_w else None
        rows.append({"load": lid, "rooms": list(ids), "load_w": load_w, "calculated_w": calc_w, "difference_pct": diff,
                     "within_tolerance": diff is not None and abs(diff) <= section["tolerance_pct"]})
    return rows


def _run(section):
    import epc_lighting
    try:
        options = epc_lighting.Options(**{**lux_map.RETURN_GRID, **(section.get("options") or {})})
        return epc_lighting.run(section["document"], options).as_dict()
    except (epc_lighting.LightingError, TypeError) as exc:  # TypeError: an option the engine does not have
        raise StageInputError([reason(exc)]) from exc


def _findings(result, checks, section, run_id, slug):
    """A major finding per room or area under its target and per load outside the tolerance, then one note per engine warning."""
    failing = [i for i in result["rooms"] + result["areas"] if i["verification"]["complies"] is False]
    findings = [engine_finding(n, run_id, slug, item["id"], "mean_illuminance_complies", False, True) for n, item in enumerate(failing, start=1)]
    findings += [engine_finding(len(findings) + n, run_id, slug, c["load"], "load_power_vs_calculated", c["difference_pct"], f"within {section['tolerance_pct']} %")
                 for n, c in enumerate([c for c in checks or [] if not c["within_tolerance"]], start=1)]
    return findings + [warning_finding(len(findings) + n, run_id, slug, w) for n, w in enumerate(result["warnings"], start=1)]


class LightingStage(Stage):
    wired = True
    wiring_task = "MIG-40"
    optional = True      # without its inputs the grouped stage skips it instead of ending as not_available

    def execute(self, context):
        section = _section(context)
        if section is None:
            return self.result("not_available", message=NOT_PROVIDED, reason="no_lighting_inputs")
        errors = _check_loads(section, context)
        if errors:
            raise StageInputError(errors)
        result = _run(section)
        checks = load_check(section, result, context.loads["loads"]) if section.get("loads") else None
        findings = _findings(result, checks, section, context.pipeline_run_id, self.spec.slug)
        counts = result["counts"]
        outputs = dict(result, load_check=checks) if checks is not None else result
        return self.result("ok", outputs=outputs, findings=findings, engine_calls=[EC.record_for(ENGINE, FUNCTION)],
                           message=f"{counts['rooms']} room(s), {counts['areas']} area(s), {counts['luminaires']} luminaire(s) (draft)")
