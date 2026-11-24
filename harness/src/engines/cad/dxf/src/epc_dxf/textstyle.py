"""The text look and the tray blocks of every DXF: typeface, text heights and whether a tray (with its text) is drawn as one block.

Like the layer catalog, three sources, the later winning field by field (a file may carry only what it changes):
  1. `harness/config/dxf/text.json`: the file the values live in, edit it (one source, no copy in the code);
  2. the same file name in another folder named by the settings in force (`epc_dxf.settings`, `config_dir`; empty: none), when it is not that one;
  3. the files the settings name (`text_files`).
The settings are handed in by the caller (`settings.use`); the process environment is never read here (ADR-0042).
Nothing is cached: edit the file and the next DXF is written with the change. Old DXFs are not touched: write them again.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_CONFIG = Path(__file__).resolve().parents[6] / "config" / "dxf"          # harness/config/dxf: the files that hold the values in force (one source)
DEFAULT_FILE = REPO_CONFIG / "text.json"
FILE_NAME = "text.json"
SECTIONS = {
    "font": {"regular": str, "bold": str, "style": str, "style_bold": str},
    "heights": {"plan_text_m": float, "plan_symbol_mm": float, "plan_text_mm": float, "titleblock_mm": float, "legal_notice_mm": float, "diagram_text_mm": float, "frame_text_mm": float},
    "trays": {"as_block": bool, "kinds": list, "block_prefix": str, "default_kind": str, "rung_pitch_mm": float, "rung_width_mm": float, "lip_mm": float, "slot_pitch_mm": float, "slot_length_mm": float, "wire_pitch_mm": float, "radius_mm": float, "joint_length_mm": float},
}


def config_dir() -> Optional[Path]:
    """The editable folder: the one the settings name (empty: none), else `harness/config/dxf` when it exists."""
    from epc_dxf import settings
    named = settings.current().config_dir
    if named is not None:
        return Path(named) if named else None
    return REPO_CONFIG if REPO_CONFIG.is_dir() else None


def _read(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _files() -> List[Path]:
    folder = config_dir()
    folder = folder if folder and folder.resolve() != REPO_CONFIG.resolve() else None
    from epc_dxf import settings
    named = [Path(x) for x in settings.current().text_files]
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


def load_file(name: str) -> Dict[str, Any]:
    """A table of the editable folder (`unify.json`...): the packaged default with, key by key, what the file of the folder and those of the settings (when they have this name) change."""
    out = {k: dict(v) if isinstance(v, dict) else v for k, v in _read(REPO_CONFIG / name).items()}
    folder = config_dir()
    for p in ([folder / name] if folder and folder.resolve() != REPO_CONFIG.resolve() else []):
        if p.is_file():
            for k, v in _read(p).items():
                out[k] = {**out.get(k, {}), **v} if isinstance(v, dict) else v
    return out
