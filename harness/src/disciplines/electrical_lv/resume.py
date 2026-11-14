"""Automatic start stage of a re-run (RUN-01): the first stage that reads something that changed since the recorded run.

Every run writes the signatures of its inputs (`run_inputs.json` in its run folder): the SHA-256 of the intake answers, of the load list and of each section of `engine_inputs`. A run that asks to
`resume` compares them with the ones of the new inputs and starts at the first stage that reads a changed section; the stages before it are reused by `pipeline.run(from_stage=...)`, which checks
that reuse is still valid. A change to the answers or the load list (or to anything the building section derives into them) is refused: those are read by the first stage and everything after depends on them.

`STAGE_OF_SECTION` is the first stage that reads each section of `engine_inputs`; a section that is not listed is read from stage 3 on (the earliest stage that reads `engine_inputs`), so a new section never
skips a stage it should have run.
"""
import hashlib
import json

FILE = "run_inputs.json"
LAST_STAGE = 12
DEFAULT_STAGE = 3
MODE_STAGE = 11
STAGE_OF_SECTION = {"transformer": 4, "drawings": 10, "documents": 11, "boq": 11, "datasheets": 11, "rfq": 11, "deliverable_names": 12}


class NothingToResume(ValueError):
    """The change cannot be resumed from a later stage (answers or load list changed) or there is no recorded run; the message says why."""


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def signatures(answers, loads, engine_inputs, mode="production"):
    """{"answers": sha, "loads": sha, "engine_inputs": {section: sha}} of the inputs of a run, and its `mode` when it is not the default (so a production run writes what it always wrote)."""
    out = {"answers": _sha(answers), "loads": _sha(loads), "engine_inputs": {k: _sha(v) for k, v in sorted((engine_inputs or {}).items())}}
    return dict(out, mode=mode) if mode != "production" else out


def first_stage(previous, current):
    """The stage to start from: the first one that reads a section that changed (12 when nothing changed). Raises `NothingToResume` when the answers or the load list changed."""
    for key in ("answers", "loads"):
        if previous.get(key) != current[key]:
            raise NothingToResume(f"the {'intake answers' if key == 'answers' else 'load list'} changed: run the pipeline from the start")
    before, now = previous.get("engine_inputs") or {}, current["engine_inputs"]
    changed = sorted(k for k in set(before) | set(now) if before.get(k) != now.get(k))
    stages = [STAGE_OF_SECTION.get(k, DEFAULT_STAGE) for k in changed]
    if previous.get("mode", "production") != current.get("mode", "production"):
        stages.append(MODE_STAGE)                  # the mode is read by the documents (marks) and the package (manifest)
    return min(stages or [LAST_STAGE])
