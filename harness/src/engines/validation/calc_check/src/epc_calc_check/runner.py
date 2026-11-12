"""The check registry and `check_run`: run the checks, number the issues as findings."""
from collections import namedtuple

from epc_calc_check.documents import check_documents
from epc_calc_check.findings import finding, issue
from epc_calc_check.formats import check_format
from epc_calc_check.invariants import check_invariants
from epc_calc_check.manifests import check_manifests
from epc_calc_check.recalc import check_recalc
from epc_calc_check.rules import RULES
from epc_calc_check.view import RunView

Check = namedtuple("Check", "group name func")

GROUP_RECALC, GROUP_INVARIANTS, GROUP_FORMAT, GROUP_DOCUMENTS, GROUP_MANIFESTS = "recalc", "invariants", "format", "documents", "manifests"
GROUPS = (GROUP_RECALC, GROUP_INVARIANTS, GROUP_FORMAT, GROUP_DOCUMENTS, GROUP_MANIFESTS)
CHECKS = (
    Check(GROUP_FORMAT, "format", check_format),
    Check(GROUP_RECALC, "recalculation", check_recalc),
    Check(GROUP_INVARIANTS, "invariants", check_invariants),
    Check(GROUP_DOCUMENTS, "documents", check_documents),
    Check(GROUP_MANIFESTS, "manifests", check_manifests),
)


def _run_check(check, view):
    """The issues of one check; a check that cannot read the data reports it (CC-F12) instead of crashing the run."""
    try:
        return list(check.func(view))
    except Exception as exc:  # malformed input must become a finding, not an exception
        return [issue("CC-F12", "model", f"check/{check.name}", f"{type(exc).__name__}: {exc}", "data of the shape the pipeline produces",
                      "Fix the malformed data and run the checks again.", f"check {check.name}")]


def check_run(run_result, *, project=None, files=None, run_id, start_id=1, groups=None, renumbered=False):
    """Findings (finding.schema.json dicts, ids `F-<start_id>...`) for a pipeline result in its JSON form.

    project  optional engine inputs the recalculation needs (see `recalc.py`): {"circuits": {tag: {engine row keys}}, "voltage_v", "conductor_temp_c", "manifest_schema"}
    files    optional {path: bytes | sha256 hex}: deliverable files (keyed `<directory>/<path>` of stage 14) and `*.manifest.json` files
    groups   run only these groups (names in `GROUPS`); None = all
    renumbered  True when the finding ids of `run_result` are already unique across the run (the final result of the pipeline); the default False is the
             state during a run, where every stage numbers its own findings from F-0001, so an id may only repeat inside one stage
    """
    view = RunView(run_result, project, files, renumbered)
    issues = [i for c in CHECKS if groups is None or c.group in groups for i in _run_check(c, view)]
    return [finding(n, run_id, RULES[i.rule], i) for n, i in enumerate(issues, start=start_id)]
