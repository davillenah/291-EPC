"""The default mode of a run (ADR-0035): `production` or `edit`.

An explicit mode (`epc run --mode`, the `mode` argument of the API and of the MCP tool) always wins. Without one the default is, in this order:
  1. the environment variable `EPC_RUN_MODE`, when it is set (a deployment or a test can pin it);
  2. the single versioned file `harness/config/default_run_mode` (`production` or `edit`): `edit` on `dev` while the system is built and checked, `production` on `main`;
  3. `production` when the file is missing or says something else: the strict behaviour is the one a mistake falls back to.

The file is what changes between `dev` and `main`. The gate check `default-run-mode` fails when it says `edit` on `main` or on a release; `tools/build/set_default_run_mode.py` is the promotion step.
"""
import os
from pathlib import Path

MODES = ("production", "edit")
STRICT = "production"
ENV = "EPC_RUN_MODE"
FILE = Path(__file__).resolve().parents[3] / "config" / "default_run_mode"


def read_file(path=None):
    """The mode the versioned file says, or None when it is missing or says something that is not a mode."""
    path = Path(path) if path is not None else FILE
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value if value in MODES else None


def default_mode(environ=None, path=None):
    """The mode of a run that does not ask for one (see the module text for the order)."""
    environ = os.environ if environ is None else environ
    pinned = (environ.get(ENV) or "").strip()
    if pinned in MODES:
        return pinned
    return read_file(path) or STRICT
