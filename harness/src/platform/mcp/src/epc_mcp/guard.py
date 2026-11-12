"""Project resolution and the write guard (SPEC 4.3): writes only under <projects>/<CLIENT>/<CODE>/{workspace,deliverables,.epc}."""
import re
from pathlib import Path

from epc_mcp.envelope import ToolError

WRITABLE = ("workspace", "deliverables", ".epc")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def check_id(value) -> str:
    """A client or project code as a single safe folder name."""
    text = str(value or "")
    if not _ID.match(text) or ".." in text or text.endswith("."):
        raise ToolError("invalid_project", "codes use letters, digits, dot, dash and underscore")
    return text


def project_dir(projects_root: Path, project: str) -> Path:
    """Folder of a project given as `CLIENT/CODE`; refuses anything that is not that shape."""
    parts = str(project or "").split("/")
    if len(parts) != 2 or not all(_ID.match(p) and ".." not in p and not p.endswith(".") for p in parts):
        raise ToolError("invalid_project", "project must be CLIENT/CODE")
    d = (Path(projects_root) / parts[0] / parts[1]).resolve()
    root = Path(projects_root).resolve()
    if root not in d.parents:
        raise ToolError("invalid_project", "project is outside the projects root")
    if not d.is_dir():
        raise ToolError("project_not_found", "unknown project %s" % project)
    return d


def check_write(project_folder: Path, target) -> Path:
    """Resolved write path, or ToolError `forbidden_path` when it leaves the writable folders."""
    base = Path(project_folder).resolve()
    p = Path(target)
    p = (p if p.is_absolute() else base / p).resolve()
    for sub in WRITABLE:
        allowed = base / sub
        if p == allowed or allowed in p.parents:
            return p
    raise ToolError("forbidden_path", "writes are limited to workspace/, deliverables/ and .epc/ of the project")
