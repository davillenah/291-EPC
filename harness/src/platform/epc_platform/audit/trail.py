"""`AuditTrail`: the event log plus the id of the pipeline run it records (PRD 17).

Deterministic: the timestamp comes from the log's injected clock and the run id from an injected random source
(an object with `getrandbits`, such as `random.Random(seed)`); the system clock and system randomness are used only when the
caller gives none at all (`random.SystemRandom`, created when the id is requested, never at import).
"""
import random
import re
from collections import Counter


class AuditTrail:
    def __init__(self, log, clock, rng=None, run_id=None):
        self.log = log
        self._clock = clock
        self._rng = rng
        self.run_id = run_id

    def new_run_id(self):
        """`run-<UTC timestamp digits>-<8 hex digits>`; becomes this trail's run id and is returned."""
        rng = self._rng or random.SystemRandom()
        stamp = re.sub(r"[^0-9A-Za-z]", "", str(self._clock()))[:24] or "0"
        self.run_id = f"run-{stamp}-{rng.getrandbits(32):08x}"
        return self.run_id

    def record(self, actor, action, target, result, detail=None):
        """Append one event of this run. `actor` is {'role', 'id'}. Returns the stored record."""
        if self.run_id is None:
            raise ValueError("no pipeline_run_id yet: call new_run_id() first")
        return self.log.append({"pipeline_run_id": self.run_id, "actor": actor, "action": action, "target": target, "result": result, "detail": detail})

    def summary(self):
        """Counts of this run's events per actor role, action and result, how many events the whole log has, and its last hash."""
        records = self.log.read()
        mine = [r for r in records if r["pipeline_run_id"] == self.run_id]
        return {"pipeline_run_id": self.run_id, "events": len(mine), "total_events": len(records),
                "by_actor": dict(sorted(Counter(r["actor"]["role"] for r in mine).items())),
                "by_action": dict(sorted(Counter(r["action"] for r in mine).items())),
                "by_result": dict(sorted(Counter(r["result"] for r in mine).items())),
                "last_hash": records[-1]["hash"] if records else None}
