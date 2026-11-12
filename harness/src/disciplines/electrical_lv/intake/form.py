"""Guided-form answers (PRD section 11): validation against intake_answers.schema.json.

D24: the earthing scheme and the available short-circuit level are mandatory. A missing one is an
explicit error, never a default.
"""
from disciplines.electrical_lv.intake.schema_check import load_schema, validate

CRITICAL = (
    ("earthing_system", "earthing scheme (TT, TN or IT)"),
    ("short_circuit_level", "available short-circuit level with its origin"),
)


class IntakeError(ValueError):
    """The answers cannot become a project profile; `errors` lists every reason."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = list(errors)


def critical_errors(answers):
    """D24 errors for missing critical supply data (empty when both are present)."""
    supply = answers.get("supply") if isinstance(answers, dict) else None
    supply = supply if isinstance(supply, dict) else {}
    return [f"supply.{key}: D24 {label} is mandatory and has no default" for key, label in CRITICAL if supply.get(key) in (None, "", {})]


def validate_answers(answers):
    """All errors of the answers: D24 data first, then the schema (without repeating a D24 field)."""
    errors = critical_errors(answers)
    flagged = tuple(e.split(":")[0] for e in errors)
    schema_errors = [e for e in validate(answers, load_schema("intake_answers.schema.json")) if not e.startswith(flagged)]
    return errors + schema_errors


def check_answers(answers):
    """Return the answers when valid, otherwise raise IntakeError."""
    errors = validate_answers(answers)
    if errors:
        raise IntakeError(errors)
    return answers
