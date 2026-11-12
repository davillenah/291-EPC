"""The default sheet: an IRAM sheet. The engines do not import one another, so it is not taken from `epc_titleblock` by an import but by its command line (`python -m epc_titleblock.sheet_generator
A1 sheet.svg`), run with the same Python, like any other tool; when that package is not there the engine says so and draws on its own simple frame."""
import json
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Optional

from epc_arch.export.sheet_iram import SheetTemplate, load_template

FORMATS = ("A0", "A1", "A2", "A3", "A4")
DEFAULT_FORMAT = "A1"


def iram_template(sheet_format: str = DEFAULT_FORMAT, config: Optional[dict] = None) -> Optional[SheetTemplate]:
    """The blank IRAM sheet of a format (A0 to A4), or None when `epc_titleblock` cannot make it here. `config` is how the organization changed the sheet (margins, pens, text, title block)."""
    return _iram_template(sheet_format, json.dumps(config, sort_keys=True) if config else "")


@lru_cache(maxsize=8)
def _iram_template(sheet_format: str, config_json: str) -> Optional[SheetTemplate]:
    if sheet_format not in FORMATS:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "sheet.svg"
        extra = []
        if config_json:
            (Path(tmp) / "config.json").write_text(config_json, encoding="utf-8")
            extra = ["--config", str(Path(tmp) / "config.json")]
        try:
            run = subprocess.run([sys.executable, "-m", "epc_titleblock.sheet_generator", sheet_format, str(out), *extra], capture_output=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            return None
        if run.returncode != 0 or not out.exists():
            return None
        return load_template(out.read_text(encoding="utf-8"))


iram_template.cache_clear = _iram_template.cache_clear                 # the cache is that of the sheets the organizations' configurations give
