"""Version and the data the engine reads: the typical values of the method (losses, thermal model, inverter curve, string rules), which the owner confirms on the norms page."""
import json
from functools import lru_cache
from pathlib import Path

VERSION = "0.1.0"                                           # the same as `__version__` of the package
SCHEMA_VERSION = "1.0"
HERE = Path(__file__).resolve().parent
PARAMS = HERE / "data" / "params.json"                  # the file the norms page edits


@lru_cache(maxsize=None)
def _data() -> dict:
    return json.loads(PARAMS.read_text(encoding="utf-8"))


def clear_cache() -> None:
    """Read the parameters again (the norms page changed one)."""
    _data.cache_clear()


def params() -> dict:
    return _data()


def losses_total_pct(losses_pct: dict) -> float:
    """Combined loss in percent: the components multiply, they do not add."""
    kept = 1.0
    for value in losses_pct.values():
        kept *= 1.0 - float(value) / 100.0
    return 100.0 * (1.0 - kept)
