"""Compare two revisions of a list of records that share an identifier field.

`compare(previous, current, *, id_field, ignore, max_changes)` answers
`{added, removed, changed, summary}`:
  added    the records of `current` whose identifier is not in `previous`, in the order of `current`;
  removed  the records of `previous` whose identifier is not in `current`, in the order of `previous`;
  changed  `{id, fields: [{field, before, after}]}` for each record in both that differs, fields in alphabetical order (a field that is absent on one side has `None`
           there and is marked `present: "before"` or `"after"` only when it exists on one side);
  summary  the counts, including `unchanged`.
Nested values are compared whole. `ignore` lists the fields that never count (a date, a revision letter). `id_field`, `ignore` and `max_changes` have no default.
"""
from epc_changes.errors import ChangesError

_MISSING = object()


def _text(value, name):
    if not isinstance(value, str) or not value:
        raise ChangesError("err_not_text", name=name, value=value)
    return value


def _names(value, name):
    if not isinstance(value, (list, tuple)) or any(not isinstance(v, str) or not v for v in value):
        raise ChangesError("err_not_names", name=name, value=value)
    return frozenset(value)


def _limit(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ChangesError("err_not_count", name="max_changes", value=value)
    return value


def _identifier(record, index, name, id_field):
    ident = record.get(id_field) if isinstance(record, dict) else None
    if isinstance(ident, bool) or not isinstance(ident, (str, int, float)) or ident == "":
        raise ChangesError("err_missing_id", index=index, name=name, id_field=id_field)
    return ident


def _index(records, name, id_field):
    if not isinstance(records, (list, tuple)):
        raise ChangesError("err_not_records", name=name, value=records)
    table = {}
    for i, record in enumerate(records):
        ident = _identifier(record, i, name, id_field)
        if ident in table:
            raise ChangesError("err_duplicate_id", name=name, identifier=ident)
        table[ident] = record
    return table


def _field_changes(before, after, ignore):
    out = []
    for field in sorted(set(before) | set(after), key=str):
        if field in ignore:
            continue
        a, b = before.get(field, _MISSING), after.get(field, _MISSING)
        if a != b:
            row = {"field": field, "before": None if a is _MISSING else a, "after": None if b is _MISSING else b}
            if a is _MISSING or b is _MISSING:
                row["present"] = "after" if a is _MISSING else "before"
            out.append(row)
    return out


def compare(previous, current, *, id_field, ignore, max_changes):
    """What changed from `previous` to `current`."""
    id_field, ignored, limit = _text(id_field, "id_field"), _names(ignore, "ignore"), _limit(max_changes)
    old, new = _index(previous, "previous", id_field), _index(current, "current", id_field)
    changed = []
    for ident, record in new.items():
        if ident in old:
            fields = _field_changes(old[ident], record, ignored | {id_field})
            if fields:
                changed.append({"id": ident, "fields": fields})
    added = [r for i, r in new.items() if i not in old]
    removed = [r for i, r in old.items() if i not in new]
    count = len(added) + len(removed) + len(changed)
    if count > limit:
        raise ChangesError("err_too_many", count=count, limit=limit)
    summary = {"added": len(added), "removed": len(removed), "changed": len(changed), "unchanged": len(new) - len(added) - len(changed)}
    return {"added": added, "removed": removed, "changed": changed, "summary": summary}
