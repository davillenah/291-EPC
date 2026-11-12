"""Per-stage preconditions of the electrical_lv pipeline, loaded from `preconditions.json` (data, no norm values).

`check_preconditions` returns finding-shaped dicts (rule ids PC-<stage>-<n>); an empty list means the stage may run.
"""
import json
from pathlib import Path

PATH = Path(__file__).with_name("preconditions.json")
VERIFIER = "input-verifier"


def load_preconditions(path=None):
    """{stage number: [requirement dict]} read from the JSON data file."""
    data = json.loads(Path(path or PATH).read_text(encoding="utf-8"))
    return {int(k): list(v) for k, v in data["stages"].items()}


def _present(context, name):
    return getattr(context, name, None) not in (None, "", {}, [])


def _ok_context(req, context):
    return _present(context, req["field"])


def _ok_any(req, context):
    return any(_present(context, name) for name in req["fields"])


def _ok_list(req, context):
    doc = getattr(context, req["field"], None)
    return bool(isinstance(doc, dict) and doc.get(req["key"]))


def _ok_stage(req, context):
    result = context.results.get(req["stage"])
    return result is not None and result.status == "ok"


CHECKS = {"context": _ok_context, "context_any": _ok_any, "nonempty_list": _ok_list, "stage_ok": _ok_stage}


def _field_name(req):
    return req.get("field") or "|".join(req.get("fields", [])) or f"stage {req.get('stage')}"


def _finding(n, run_id, stage, index, req):
    rule = f"PC-{stage:02d}-{index}"
    return {
        "id": f"F-{n:04d}", "run_id": run_id, "verifier": VERIFIER, "severity": "blocking",
        "document": "pipeline", "field": f"stage {stage}/{_field_name(req)}", "value": None,
        "expected": req["text"], "clause": f"project criterion {rule}",
        "action": "Provide the missing input or fix the earlier stage.", "evidence": [f"rule {rule}"], "status": "open",
    }


def check_preconditions(stage, context, run_id="run-0", table=None):
    """Findings for the preconditions of `stage` that `context` does not meet (fixed order, empty when met)."""
    reqs = (table if table is not None else load_preconditions()).get(stage, [])
    unmet = [(i, r) for i, r in enumerate(reqs, start=1) if not CHECKS[r["kind"]](r, context)]
    return [_finding(n, run_id, stage, i, r) for n, (i, r) in enumerate(unmet, start=1)]
