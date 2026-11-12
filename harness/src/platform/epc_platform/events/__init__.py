"""Append-only, hash-chained event log."""
from epc_platform.events.log import GENESIS, RESULTS, EventLog, EventLogError

__all__ = ["EventLog", "EventLogError", "GENESIS", "RESULTS"]
