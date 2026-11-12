"""The generic terminal-block size table, read lazily from `data/terminal_sizes.json` (pending review, see the norm register)."""
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "terminal_sizes.json"
RECORD_ID = "terminal_blocks.params.terminal_sizes"
_CACHE = {}


def _load():
    if "sizes" not in _CACHE:
        _CACHE["sizes"] = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return _CACHE["sizes"]


def terminal_sizes():
    """The table as a tuple of dicts sorted by `size_mm2` (copies: the cache cannot be altered by the caller)."""
    return tuple(dict(row) for row in sorted(_load()["terminal_sizes"], key=lambda r: r["size_mm2"]))


def review_status():
    return _load()["review_status"]


def accepting_size(section_mm2, table=None):
    """The smallest terminal of `table` (default: the data file) that accepts the conductor section, or None. Comparison only."""
    rows = terminal_sizes() if table is None else sorted(table, key=lambda r: r["size_mm2"])
    for row in rows:
        if row["accepts_min_mm2"] <= section_mm2 <= row["accepts_max_mm2"]:
            return row
    return None


def clear_cache():
    _CACHE.clear()
