"""The append-only event log of a project (`projects/<code>/audit/events.jsonl`, PRD 10.3 and 17).

One JSON object per line (sorted keys, compact separators, ASCII escapes, LF). Fields:

    seq             1, 2, 3 ... without gaps
    ts              text from the injected clock (this module never reads the system clock)
    pipeline_run_id the run the event belongs to
    actor           {"role": ..., "id": ...}
    action, target  what was attempted and on what (free text)
    result          allowed | denied | ok | failed
    detail          dict with further plain-JSON data
    prev_hash       `hash` of the previous line (64 zeros for the first one)
    hash            sha256 of the canonical JSON of all the other fields (which include prev_hash)

The chain makes edits, removals and reordering visible to `verify()`. Removing the LAST lines cannot be seen from the file alone:
keep the last hash (`AuditTrail.summary()`) elsewhere and pass it as `expected_last_hash` to detect that.

The class has no update or delete method and opens the file only in append mode. This is a guard against accidents, not against
somebody who edits the file with another tool; that case is what `verify()` is for. One writer at a time is assumed.
This is the only platform module that may write a file (architecture test).
"""
import hashlib
import json
from pathlib import Path

GENESIS = "0" * 64
RESULTS = ("allowed", "denied", "ok", "failed")
FIELDS = ("seq", "ts", "pipeline_run_id", "actor", "action", "target", "result", "detail", "prev_hash", "hash")
LOG_REL = ("audit", "events.jsonl")


class EventLogError(ValueError):
    """An event or a log location the log refuses."""


def canonical(record):
    """The canonical text of a record (without the `hash` field)."""
    body = {k: v for k, v in record.items() if k != "hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def hash_of(record):
    return hashlib.sha256(canonical(record).encode("utf-8")).hexdigest()


def line_of(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _check_event(event):
    problems = []
    actor = event.get("actor")
    if not (isinstance(actor, dict) and isinstance(actor.get("role"), str) and isinstance(actor.get("id"), str)):
        problems.append("actor must be {'role': str, 'id': str}")
    for key in ("pipeline_run_id", "action", "target"):
        if not isinstance(event.get(key), str) or not event[key]:
            problems.append(f"{key} must be a non-empty string")
    if event.get("result") not in RESULTS:
        problems.append(f"result must be one of {RESULTS}")
    if not isinstance(event.get("detail") or {}, dict):
        problems.append("detail must be a dict")
    if problems:
        raise EventLogError("; ".join(problems))


def _inside(path, base):
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


class EventLog:
    """Append-only log. `clock()` returns the timestamp text. With `project_dir` the file must be that project's audit/events.jsonl."""

    def __init__(self, path, clock, project_dir=None):
        if not callable(clock):
            raise EventLogError("an injected clock is required")
        self.path = Path(path).resolve()
        self._clock = clock
        if project_dir is not None:
            self._check_location(Path(project_dir).resolve())

    @classmethod
    def for_project(cls, project_dir, clock):
        root = Path(project_dir).resolve()
        return cls(root.joinpath(*LOG_REL), clock, project_dir=root)

    def _check_location(self, root):
        audit = (root / LOG_REL[0]).resolve()
        if not _inside(audit, root) or self.path.parent != audit or self.path.name != LOG_REL[1]:
            raise EventLogError(f"the event log must be {root.name}/audit/events.jsonl, not {self.path}")

    # -- reading -------------------------------------------------------------------------------------------------------------
    def _lines(self):
        if not self.path.is_file():
            return []
        return self.path.read_bytes().decode("utf-8").split("\n")[:-1]

    def read(self):
        """Every record, in file order (no verification; use `verify()`)."""
        return [json.loads(line) for line in self._lines()]

    def last(self):
        """(seq, hash) of the last line: (0, GENESIS) for an empty log. Raises EventLogError when the last line is unreadable."""
        lines = self._lines()
        if not lines:
            return 0, GENESIS
        try:
            rec = json.loads(lines[-1])
            return int(rec["seq"]), str(rec["hash"])
        except (ValueError, KeyError, TypeError) as exc:
            raise EventLogError(f"the last line of the log is unreadable: {exc}") from exc

    # -- writing (append only) -----------------------------------------------------------------------------------------------
    def append(self, event):
        """Add one event (pipeline_run_id, actor, action, target, result, optional detail); returns the stored record."""
        _check_event(event)
        seq, prev = self.last()
        record = {"seq": seq + 1, "ts": str(self._clock()), "pipeline_run_id": event["pipeline_run_id"], "actor": dict(event["actor"]),
                  "action": event["action"], "target": event["target"], "result": event["result"], "detail": dict(event.get("detail") or {}),
                  "prev_hash": prev}
        try:
            record["hash"] = hash_of(record)
            data = (line_of(record) + "\n").encode("ascii")
        except (TypeError, ValueError) as exc:
            raise EventLogError(f"event is not plain JSON: {exc}") from exc
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "ab") as handle:
            handle.write(data)
            handle.flush()
        return record

    # -- verification --------------------------------------------------------------------------------------------------------
    def verify(self, expected_last_hash=None, expected_count=None):
        """Findings (list of {'line', 'problem'}) for a broken chain, an altered, removed or reordered line; empty = intact."""
        findings = []
        prev = GENESIS
        lines = self._lines()
        for number, text in enumerate(lines, start=1):
            problem = self._line_problem(number, text, prev)
            if problem:
                findings.append({"line": number, "problem": problem})
            prev = self._next_prev(text, prev)
        return findings + self._tail_problems(len(lines), prev, expected_last_hash, expected_count)

    @staticmethod
    def _next_prev(text, fallback):
        try:
            return json.loads(text).get("hash", fallback)
        except (ValueError, AttributeError):
            return fallback

    @staticmethod
    def _line_problem(number, text, prev):
        try:
            rec = json.loads(text)
        except ValueError:
            return "not valid JSON"
        if not isinstance(rec, dict) or sorted(rec) != sorted(FIELDS):
            return "fields are not the expected ones"
        if line_of(rec) != text:
            return "line is not in canonical form"
        if rec["seq"] != number:
            return f"seq is {rec['seq']}, expected {number} (line removed, added or reordered)"
        if rec["prev_hash"] != prev:
            return "prev_hash does not match the previous line (chain broken)"
        if rec["hash"] != hash_of(rec):
            return "hash does not match the content (line altered)"
        return None

    @staticmethod
    def _tail_problems(count, last_hash, expected_last_hash, expected_count):
        out = []
        if expected_count is not None and count != expected_count:
            out.append({"line": count, "problem": f"{count} lines, expected {expected_count} (lines removed or added)"})
        if expected_last_hash is not None and last_hash != expected_last_hash:
            out.append({"line": count, "problem": "last hash differs from the anchored one"})
        return out
