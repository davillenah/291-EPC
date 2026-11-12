"""Where the data of the AEA 90364 norm lives, and the ONE loader that reads it (MIG-37a).

Norm data (tables, constants, rules, design criteria, standard solutions, system voltages) is in the repository's normative folder,
`harness/config/normative/AR/electrical/aea90364/`:

  aea_tables.json          tables and constants of the norm
  rules/*.json             the engineering rules derived from the norm (+ `_indice.json`)
  design-criteria.json     the catalog of base design criteria (the norm reviewer corrects the values there; a project overrides them)
  standard-solutions.json  which symbols build each circuit
  system_voltages.json     the system voltages (230/400 V, 220/380 V) and their U0

The review state of the owner stays with the AEA 90364 engine package (`epc_aea90364/data/`) (`review.json`, `review-log.jsonl`).

The folder is found, in this order: (1) the environment variable `EPC_NORMATIVE_ROOT` (the `normative` folder that holds `AR/`), (2) the nearest parent of this
file that has `harness/config/normative` (the repository, or a built plugin's `lib/`), (3) otherwise `FileNotFoundError` naming what was searched.
Nothing is read at import: files are read lazily and kept in a cache that `clear_cache()` empties. Every other module asks here instead of building a path.
"""
import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

ENV_VAR = "EPC_NORMATIVE_ROOT"
SUBPATH = ("AR", "electrical", "aea90364")


def _review_dir() -> Path:
    """`data/` of the AEA 90364 engine package (found without importing it): the owner's review state stays with that engine, not here."""
    spec = importlib.util.find_spec("epc_aea90364")
    return Path(spec.origin).resolve().parent / "data" if spec and spec.origin else Path(__file__).resolve().parent / "data"


DATA = _review_dir()                                                  # review state of the owner (not norm data)
REVIEW = DATA / "review.json"
REVIEW_LOG = DATA / "review-log.jsonl"
CRITERIA = {"electrical": "design-criteria.json"}                    # AEA 90364 is an electrical norm: one catalog
_CACHE: Dict[str, Any] = {}


def _candidates() -> List[Path]:
    """Every place the folder is looked for, in order (the environment first)."""
    env = os.environ.get(ENV_VAR)
    if env:
        return [Path(env).joinpath(*SUBPATH)]
    return [p / "harness" / "config" / "normative" / Path(*SUBPATH) for p in Path(__file__).resolve().parents]


def normative_dir() -> Path:
    """The folder with the norm data of this engine; `FileNotFoundError` naming the searched places when there is none."""
    found = _candidates()
    for folder in found:
        if folder.is_dir():
            return folder
    where = f"{ENV_VAR}={os.environ[ENV_VAR]!r}" if os.environ.get(ENV_VAR) else "the parents of " + str(Path(__file__).resolve())
    raise FileNotFoundError(f"norm data folder not found (harness/config/normative/{'/'.join(SUBPATH)}); searched {where}: "
                            + ", ".join(str(c) for c in found[:4]) + (" ..." if len(found) > 4 else ""))


def path(*parts: str) -> Path:
    """A file or folder inside the norm data folder."""
    return normative_dir().joinpath(*parts)


def rules_dir() -> Path:
    return path("rules")


def read_json(file: Any) -> Any:
    """Parse a JSON file (no cache)."""
    return json.loads(Path(file).read_text(encoding="utf-8-sig"))


def load_json(name: str) -> Any:
    """The parsed JSON file `name` (relative to the norm data folder), cached until `clear_cache()`."""
    file = path(*name.split("/"))
    key = str(file)
    if key not in _CACHE:
        _CACHE[key] = read_json(file)
    return _CACHE[key]


def clear_cache() -> None:
    """Forget what was read: the next use reads the files again (after a norm value was corrected)."""
    _CACHE.clear()


def criteria_file(discipline: str = "electrical") -> Optional[Path]:
    """The design-criteria catalog of a discipline of this norm, or None when the norm has none for it."""
    name = CRITERIA.get(discipline)
    if not name:
        return None
    f = path(name)
    return f if f.is_file() else None
