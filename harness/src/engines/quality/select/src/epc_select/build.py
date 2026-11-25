"""Quick select: the records that meet the conditions.

`select(records, conditions, *, match, max_results)` answers `{matches, indices, count}`: the matching records in their order, their positions in `records`, and
how many. A condition is `{field, op, value}`; `op` is one of
  eq ne          equal, different (a record without the field is different, never equal)
  lt le gt ge    ordered comparison of numbers (booleans are not numbers), or of two texts; mixed kinds never meet the condition
  in             the field value is one of the `value` list
  contains       the field is a text that contains the text `value`, or a list that has `value` as an item
  exists         the field is present (`value` true) or absent (`value` false)
`match` is `all` (every condition) or `any` (at least one); no condition at all selects every record under `all` and none under `any`. `match` and `max_results`
have no default.
"""
from epc_select.errors import SelectError

OPS = ("eq", "ne", "lt", "le", "gt", "ge", "in", "contains", "exists")
_MISSING = object()


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _ordered(a, b):
    return (_number(a) and _number(b)) or (isinstance(a, str) and isinstance(b, str))


_COMPARE = {"lt": lambda a, b: a < b, "le": lambda a, b: a <= b, "gt": lambda a, b: a > b, "ge": lambda a, b: a >= b}


def _contains(value, wanted):
    if isinstance(value, str):
        return isinstance(wanted, str) and wanted in value
    return isinstance(value, list) and wanted in value


def _holds(op, value, wanted):
    if op == "exists":
        return (value is not _MISSING) == bool(wanted)
    if op == "ne":
        return value is _MISSING or value != wanted
    if value is _MISSING:
        return False
    if op == "eq":
        return value == wanted
    if op == "in":
        return value in wanted
    if op == "contains":
        return _contains(value, wanted)
    return _ordered(value, wanted) and _COMPARE[op](value, wanted)


def _condition(raw, index):
    if not isinstance(raw, dict) or not isinstance(raw.get("field"), str) or not raw["field"] or "op" not in raw:
        raise SelectError("err_bad_condition", index=index, value=raw)
    op = raw["op"]
    if op not in OPS:
        raise SelectError("err_unknown_op", index=index, op=op, allowed=", ".join(OPS))
    if "value" not in raw:
        if op != "exists":
            raise SelectError("err_bad_condition", index=index, value=raw)
        raw = {**raw, "value": True}
    if op == "in" and not isinstance(raw["value"], list):
        raise SelectError("err_bad_condition", index=index, value=raw)
    return raw["field"], op, raw["value"]


def _check(records, match, max_results):
    if match not in ("all", "any"):
        raise SelectError("err_bad_match", value=match)
    if isinstance(max_results, bool) or not isinstance(max_results, int) or max_results < 1:
        raise SelectError("err_not_count", value=max_results)
    if not isinstance(records, (list, tuple)) or any(not isinstance(r, dict) for r in records):
        raise SelectError("err_not_records", value=records)


def select(records, conditions, *, match, max_results):
    """The records that meet the conditions, in their order."""
    _check(records, match, max_results)
    rules = [_condition(c, i) for i, c in enumerate(conditions)]
    combine = all if match == "all" else any
    indices = [i for i, r in enumerate(records) if combine(_holds(op, r.get(f, _MISSING), v) for f, op, v in rules)]
    if len(indices) > max_results:
        raise SelectError("err_too_many", count=len(indices), limit=max_results)
    return {"matches": [records[i] for i in indices], "indices": indices, "count": len(indices)}
