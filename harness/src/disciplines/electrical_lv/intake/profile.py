"""Build the `project_profile` from the form answers.

The structure and the normative defaults (PRD section 8) come from projects/_template/.epc/project_profile.json;
nothing is invented here. Critical data missing from the answers (D24) is an error, not a default.
"""
import copy
import json
from pathlib import Path

from disciplines.electrical_lv.intake.form import check_answers

TEMPLATE = Path(__file__).resolve().parents[5] / "projects" / "_template" / ".epc" / "project_profile.json"
STATUS = "draft"


def load_template(path=None):
    return json.loads(Path(path or TEMPLATE).read_text(encoding="utf-8"))


def _merge(base, extra):
    """Copy of `base` with the values of `extra` laid over it (dicts merge, anything else replaces)."""
    out = copy.deepcopy(base)
    for key, value in extra.items():
        both_dicts = isinstance(value, dict) and isinstance(out.get(key), dict)
        out[key] = _merge(out[key], value) if both_dicts else copy.deepcopy(value)
    return out


def build_profile(answers, template=None):
    """The project profile for valid answers; IntakeError (with every reason) otherwise."""
    check_answers(answers)
    profile = _merge(load_template() if template is None else template, answers)
    profile["status"] = STATUS
    return profile
