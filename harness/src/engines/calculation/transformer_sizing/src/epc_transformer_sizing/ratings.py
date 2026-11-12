"""The standard transformer ratings, read lazily from `data/standard_ratings.json` (pending review, see the norm register)."""
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "standard_ratings.json"
RECORD_ID = "transformer_sizing.params.standard_ratings"
_CACHE = {}


def _load():
    if "ratings" not in _CACHE:
        _CACHE["ratings"] = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return _CACHE["ratings"]


def standard_ratings_kva():
    """The standard series as a sorted tuple of kVA."""
    return tuple(sorted(_load()["ratings_kva"]))


def review_status():
    return _load()["review_status"]


def clear_cache():
    _CACHE.clear()
