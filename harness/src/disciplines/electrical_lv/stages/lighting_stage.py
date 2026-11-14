"""Slice 17 of stage 3 (lighting calculation of the rooms), optional.

The discipline calculates nothing: it hands the `lighting` section of `context.engine_inputs` to `epc_lighting.run` and returns what comes back.
The section is `{"document": <input document of epc_lighting>, "options": {<epc_lighting.Options fields>}}`; `options` is optional, `document`
carries the luminaires, rooms and exterior areas with every datum the engine asks for (nothing is defaulted here). It is the lighting counterpart of
the transformer inputs of stage 4: the data of a room (size, height, activity, luminaire) cannot come from the load list, which only holds watts.

  no `lighting` section   the slice is not available and the stage goes on without it (`optional`, see `grouped.py`)
  invalid section         `blocked` with the engine's message (or the unknown key); the grouped stage adds the `lighting:` prefix
  valid section           `ok`: the engine result as it is, one engine call, a `major` finding for every room or area whose mean illuminance
                          does not reach its target, and one `note` finding per engine warning (draft, D21)

The result does NOT change the load list: the power of the lighting circuits is still the one of `loads.csv`. The engine's installed power is reported
beside it so the engineer can compare both.
"""
from disciplines.electrical_lv.stages import engine_calls as EC
from disciplines.electrical_lv.stages.base import Stage, StageInputError, engine_finding

ENGINE = "calculation/lighting"
FUNCTION = "epc_lighting.run"
KEYS = ("document", "options")
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


def _run(section):
    import epc_lighting
    try:
        options = epc_lighting.Options(**(section.get("options") or {}))
        return epc_lighting.run(section["document"], options).as_dict()
    except (epc_lighting.LightingError, TypeError) as exc:  # TypeError: an option the engine does not have
        raise StageInputError([str(exc)]) from exc


class LightingStage(Stage):
    wired = True
    wiring_task = "MIG-40"
    optional = True      # without its inputs the grouped stage skips it instead of ending as not_available

    def execute(self, context):
        section = _section(context)
        if section is None:
            return self.result("not_available", message=NOT_PROVIDED, reason="no_lighting_inputs")
        result = _run(section)
        run_id, slug = context.pipeline_run_id, self.spec.slug
        findings = [engine_finding(n, run_id, slug, item["id"], "mean_illuminance_complies", False, True)
                    for n, item in enumerate([i for i in result["rooms"] + result["areas"] if i["verification"]["complies"] is False], start=1)]
        findings += [warning_finding(len(findings) + n, run_id, slug, w) for n, w in enumerate(result["warnings"], start=1)]
        counts = result["counts"]
        return self.result("ok", outputs=result, findings=findings, engine_calls=[EC.record_for(ENGINE, FUNCTION)],
                           message=f"{counts['rooms']} room(s), {counts['areas']} area(s), {counts['luminaires']} luminaire(s) (draft)")
