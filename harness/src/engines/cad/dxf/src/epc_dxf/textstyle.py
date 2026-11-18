"""The text look and the tray blocks of every DXF: typeface, text heights and whether a tray (with its text) is drawn as one block.

Like the layer catalog, three sources, the later winning field by field (a file may carry only what it changes):
  1. the default that travels with this package (`data/text.json`);
  2. the editable folder `harness/config/dxf/text.json` (or the folder named in EPC_DXF_CONFIG_DIR);
  3. the files named in EPC_DXF_TEXT_JSON (several are separated as paths are).
Nothing is cached: edit the file and the next DXF is written with the change. Old DXFs are not touched: write them again.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

ENV_DIR = "EPC_DXF_CONFIG_DIR"
ENV_FILES = "EPC_DXF_TEXT_JSON"
DEFAULT_FILE = Path(__file__).resolve().parent / "data" / "text.json"
REPO_CONFIG = Path(__file__).resolve().parents[6] / "config" / "dxf"          # harness/config/dxf
FILE_NAME = "text.json"
SECTIONS = {
    "font": {"regular": str, "bold": str, "style": str, "style_bold": str},
    "heights": {"plan_text_m": float, "titleblock_mm": float, "legal_notice_mm": float, "diagram_text_mm": float, "frame_text_mm": float},
    "trays": {"as_block": bool, "kinds": list, "block_prefix": str},
}


def config_dir() -> Optional[Path]:
    """The editable folder: the one EPC_DXF_CONFIG_DIR names (empty: none), else `harness/config/dxf` when it exists."""
    named = os.environ.get(ENV_DIR)
    if named is not None:
        return Path(named) if named else None
    return REPO_CONFIG if REPO_CONFIG.is_dir() else None


def _read(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _files() -> List[Path]:
    folder = config_dir()
    named = [Path(x) for x in (os.environ.get(ENV_FILES) or "").split(os.pathsep) if x]
    return ([folder / FILE_NAME] if folder else []) + named


def load() -> Dict[str, Dict[str, Any]]:
    """The text look in force: section -> field -> value."""
    out = {s: dict(v) for s, v in _read(DEFAULT_FILE).items() if isinstance(v, dict)}
    for p in _files():
        if p.is_file():
            for section, fields in _read(p).items():
                if isinstance(fields, dict):
                    out.setdefault(section, {}).update(fields)
    return out


def validate(look: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """{section.field: message} for what the file may not contain; empty when valid."""
    bad: Dict[str, str] = {}
    for section, fields in SECTIONS.items():
        for field, kind in fields.items():
            v = look.get(section, {}).get(field)
            ok = isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 if kind is float else isinstance(v, kind) and (kind is not str or v.strip() != "")
            if not ok:
                bad[f"{section}.{field}"] = "a number above 0" if kind is float else {bool: "true or false", list: "a list of tray kind codes", str: "a non-empty text"}[kind]
    return bad


def get(section: str, field: str) -> Any:
    return load()[section][field]


def add_styles(doc) -> None:
    """The text styles of the configured typeface (regular and bold) in an ezdxf document."""
    f = get_section("font")
    for style, font in ((f["style"], f["regular"]), (f["style_bold"], f["bold"])):
        if style not in doc.styles:
            doc.styles.add(style, font=font)


def get_section(section: str) -> Dict[str, Any]:
    return load()[section]
