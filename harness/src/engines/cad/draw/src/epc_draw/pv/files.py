"""The PV writers return their drawings as bytes (ADR-0042); this is the one place that puts them on disk for the callers that want files."""
from pathlib import Path
from typing import Dict


def save(out_dir, files: Dict[str, bytes]) -> Dict[str, Path]:
    """Writes {file name: bytes} under `out_dir` (created) and returns {file name: path}."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for file_name, data in files.items():
        paths[file_name] = out / file_name
        paths[file_name].write_bytes(data)
    return paths
