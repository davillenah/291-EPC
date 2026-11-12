"""Shared helpers for the standard-ingest scripts (stdlib only, except pypdf/pypdfium2 where noted)."""
import json
import re
import unicodedata
from pathlib import Path

_PARENTS = Path(__file__).resolve().parents
WORKSPACE = next((p for p in _PARENTS if (p / "harness" / "schemas").is_dir() and (p / "harness" / "config" / "normative").is_dir()), _PARENTS[min(7, len(_PARENTS) - 1)])   # repository root (this file is 7 levels below it)
ENGINE = WORKSPACE / "harness" / "src" / "engines"        # folder that holds the engine groups (cad, calculation, ...); pack_dir() finds a norm engine in them
JURISDICTIONS = WORKSPACE / "harness" / "config" / "normative"
DEV_KNOWLEDGE = WORKSPACE / "local" / "dev-knowledge"
SCHEMAS = WORKSPACE / "harness" / "schemas"
SHINGLE = 12                                              # consecutive words that count as verbatim copying


def jurisdictions_dir(engine):
    """Folder with the `<CC>/jurisdiction.json` files: `<engine>/jurisdictions` in a test tree that holds at least one, else the repository's `harness/config/normative`."""
    own = Path(engine) / "jurisdictions"
    return own if any(own.glob("*/jurisdiction.json")) else JURISDICTIONS


def pack_dir(engine, name):
    """Folder of the norm engine `name`: `<engine>/<name>`. When the engine folder has no such pack and is not a test tree (no jurisdictions/<CC>/jurisdiction.json of its own), the pack is
    looked up in the repository's group folders `harness/src/engines/<group>/<name>`."""
    own = Path(engine) / name
    if own.is_dir() or any((Path(engine) / "jurisdictions").glob("*/jurisdiction.json")):
        return own
    return next(iter(sorted((WORKSPACE / "harness" / "src" / "engines").glob(f"*/{name}"))), own)


def _pack_names(jurisdiction, domain, pack=None):
    """The norm engines a jurisdiction names for a domain (one string or a list), narrowed to `pack` when one is asked."""
    value = (jurisdiction.get("packs") or {}).get(domain)
    names = [n for n in ([value] if isinstance(value, str) else list(value or [])) if n]
    return ([pack] if pack in names else []) if pack else names


def pack_standards_dir(engine, jurisdiction, domain, pack=None):
    """Where the promoted standards of a domain go: the `standards/` folder of the norm engine the jurisdiction names for it. Returns (folder, problem); `problem` says what to fix."""
    names = _pack_names(jurisdiction, domain, pack)
    if not names:
        return None, f"the jurisdiction names no norm engine for {domain!r} (packs.{domain} in jurisdiction.json)"
    if len(names) > 1:
        return None, f"the jurisdiction names several norm engines for {domain!r} ({', '.join(names)}): choose one with --pack"
    folder = pack_dir(engine, names[0]) / "src" / f"epc_{names[0]}"
    return (folder / "standards", None) if folder.is_dir() else (None, f"the norm engine {names[0]!r} does not exist under {engine}")


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def write_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def norm_words(text):
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", t)


def shingles(words, n=SHINGLE):
    return {" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1))}


def standard_dir(arg):
    """Accept a folder path or '<CC>/<ID>' / '<ID>' (searched under dev-knowledge/standards)."""
    p = Path(arg)
    if p.is_dir():
        return p.resolve()
    base = DEV_KNOWLEDGE / "standards"
    for cand in (base / arg, *base.glob(f"*/{arg}")):
        if cand.is_dir():
            return cand
    raise SystemExit(f"standard folder not found: {arg}")


def source_text_words(sdir):
    """All words of the extracted text layer of a standard, or None when it has no text."""
    pages = sorted(Path(sdir).glob("extracted/*/pages/p*.txt"))
    if not pages:
        return None
    words = []
    for f in pages:
        words.extend(norm_words(f.read_text(encoding="utf-8")))
    return words or None
