"""Rules, issues and findings.

A check yields `Issue` tuples (rule id, where, what was found, what was expected, what to do). `finding()` turns an issue into a dict valid against
`finding.schema.json`: the id, run id, verifier and severity come from the rule table, never from the check.
"""
import importlib
from collections import namedtuple

from epc_calc_check._values import safe

SEVERITIES = ("blocking", "major", "minor", "note")
VERIFIERS = ("calc-check", "format-check", "document-check")

Rule = namedtuple("Rule", "id verifier severity title norm")
Issue = namedtuple("Issue", "rule document field value expected action evidence severity", defaults=(None,))


def issue(rule, document, field, value, expected, action, evidence, severity=None):
    return Issue(rule, document, field, value, expected, action, tuple([evidence] if isinstance(evidence, str) else evidence), severity)


def first_sentence(text, limit=200):
    text = " ".join((text or "").split())
    cut = text.find(". ")
    text = text[: cut + 1] if cut > 0 else text
    return text[:limit].rstrip()


def engine_clause(dotted):
    """The first sentence of the docstring of the engine function `dotted` (the clause text the engine itself carries), or ''."""
    try:
        module, _, name = dotted.rpartition(".")
        return first_sentence(getattr(importlib.import_module(module), name).__doc__)
    except (ImportError, AttributeError, ValueError):
        return ""


def clause_of(rule):
    """`<rule id>: <text the engine carries>` for a rule that comes from a norm criterion, `project criterion <rule id>` otherwise."""
    text = engine_clause(rule.norm) if rule.norm else ""
    return f"{rule.id}: {text}" if text else f"project criterion {rule.id}"


def finding(number, run_id, rule, found):
    """One finding dict (finding.schema.json) for `found`, an Issue of `rule`."""
    return {
        "id": f"F-{number:04d}", "run_id": run_id, "verifier": rule.verifier, "severity": found.severity or rule.severity,
        "document": found.document, "field": found.field, "value": safe(found.value), "expected": safe(found.expected),
        "clause": clause_of(rule), "action": found.action, "evidence": list(found.evidence) or [f"rule {rule.id}"], "status": "open"}
