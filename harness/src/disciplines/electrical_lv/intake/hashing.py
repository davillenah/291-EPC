"""SHA-256 of the input files and a deterministic manifest of an `inputs/` folder.

Inputs are immutable after intake: `verify_inputs` reports any file that changed, disappeared or appeared.
"""
import hashlib
import json
from pathlib import Path

CHUNK = 1 << 20


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def _entries(folder):
    root = Path(folder)
    files = sorted(p for p in root.rglob("*") if p.is_file())
    return [{"path": p.relative_to(root).as_posix(), "sha256": sha256_file(p)} for p in files]


def manifest_hash(entries):
    """Hash of the entry list sorted by path (canonical JSON): equal inputs give equal manifests."""
    blob = json.dumps(sorted(entries, key=lambda e: e["path"]), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_manifest(folder):
    """{"algorithm", "files": [{"path", "sha256"}] sorted by path, "manifest_sha256"}."""
    entries = _entries(folder)
    return {"algorithm": "sha256", "files": entries, "manifest_sha256": manifest_hash(entries)}


def verify_inputs(manifest, folder):
    """Problems found comparing the folder with the manifest: [{"path", "problem"}], empty when untouched.

    problem is one of "missing", "changed", "added".
    """
    expected = {e["path"]: e["sha256"] for e in manifest["files"]}
    found = {e["path"]: e["sha256"] for e in _entries(folder)}
    problems = [{"path": p, "problem": "missing"} for p in sorted(expected) if p not in found]
    problems += [{"path": p, "problem": "changed"} for p in sorted(expected) if p in found and found[p] != expected[p]]
    problems += [{"path": p, "problem": "added"} for p in sorted(found) if p not in expected]
    return problems
