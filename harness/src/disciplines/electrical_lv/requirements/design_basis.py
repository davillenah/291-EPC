"""Design basis (stage 2): profile + criteria + assumptions, assembled by copying and merging only.

No engine is called and no value is computed. Every assumption records its reason; D24 data must already
be in the profile (it is never defaulted here either).
"""
import copy

from disciplines.electrical_lv.intake.form import CRITICAL, IntakeError

COPIED = ("project_code", "normative_profile", "supply", "language")


def _check_profile(profile):
    supply = profile.get("supply") or {}
    errors = [f"supply.{key}: D24 {label} is missing in the profile" for key, label in CRITICAL if supply.get(key) in (None, "", {})]
    if errors:
        raise IntakeError(errors)


def _assumptions(items):
    out = []
    for n, item in enumerate(items or [], start=1):
        text, reason = str(item.get("text", "")).strip(), str(item.get("reason", "")).strip()
        if not text or not reason:
            raise ValueError(f"assumption {n}: text and reason are both required")
        out.append({"id": f"A-{n:02d}", "text": text, "reason": reason})
    return out


def _criteria(profile, criteria):
    base = profile.get("criteria") or {}
    extra = criteria or {}
    return {
        "set": extra.get("set") or base.get("set"),
        "exceptions": list(base.get("exceptions") or []) + list(extra.get("exceptions") or []),
    }


def build_design_basis(profile, criteria=None, assumptions=None, requirements=None):
    """Design-basis dict. `requirements` is an optional requirements.schema.json document, copied as is."""
    _check_profile(profile)
    basis = {key: copy.deepcopy(profile.get(key)) for key in COPIED}
    basis["criteria"] = _criteria(profile, criteria)
    basis["assumptions"] = _assumptions(assumptions)
    basis["requirements"] = copy.deepcopy((requirements or {}).get("items", []))
    return basis
