"""Where things live in the repository: the ONE place the build and CI tools read folder locations from (MIG-20).

Every tool under `harness/tools/` gets the location of an engine, the documents, the schemas, the Claude layer, the web application and so on from here, never from a
hard-coded `"engine"` or `"docs"`. When a relocation task (MIG-21 ... MIG-27) moves a tree, only this file (plus the files that moved) changes.

  from epc_paths import REPO, ENGINE_DIRS, engine_dir, engine_src, DOCS, SCHEMAS

The module has no side effects at import and uses only the standard library. Tools import it with `sys.path.insert(0, <tools folder>)`; see `tools/harness/tests/test_paths.py`.
Paths are `pathlib.Path` objects; the `*_REL` strings are the same locations relative to the repository root with forward slashes (for globs, git and messages)."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# --- locations (today's layout; relocation tasks edit these lines) ---------------------------------------------------------------------
ENGINES_REL = "harness/src/engines"          # folder that holds the engine groups (cad, calculation, validation, quality), each with its engine packages (src/ and tests/)
JURISDICTIONS_REL = "harness/config/normative"   # norm tables and constants per jurisdiction
NORMATIVE_AR_REL = f"{JURISDICTIONS_REL}/AR"      # Argentina: jurisdiction.json and one folder per discipline (MIG-37a)
# Norm data of an engine, inside the normative folder (read by the engine through its own loader, for example `epc_aea90364.norm_data`).
NORM_DATA_REL = {"aea90364": f"{NORMATIVE_AR_REL}/electrical/aea90364"}
# Where files of norm data lived before MIG-37a (repo-relative, forward slashes) -> where they are now. Frozen reference cases still name the old places.
_AEA_PKG = "harness/src/engines/calculation/aea90364/src/epc_aea90364"
MOVED_NORM_DATA = {f"{_AEA_PKG}/aea_tables.json": f"{NORM_DATA_REL['aea90364']}/aea_tables.json",
                   f"{_AEA_PKG}/rules/": f"{NORM_DATA_REL['aea90364']}/rules/",
                   f"{_AEA_PKG}/data/design-criteria.json": f"{NORM_DATA_REL['aea90364']}/design-criteria.json",
                   f"{_AEA_PKG}/data/standard-solutions.json": f"{NORM_DATA_REL['aea90364']}/standard-solutions.json",
                   f"{_AEA_PKG}/data/system_voltages.json": f"{NORM_DATA_REL['aea90364']}/system_voltages.json"}
DOCS_REL = "harness/docs"
SCHEMAS_REL = "harness/schemas"
CATALOG_REL = "harness/catalogs"
I18N_REL = "harness/config/i18n"
MANAGEMENT_REL = "harness/config/pmo"
CLAUDE_REL = "harness/.claude"               # plugins, skills, agents, prompts, marketplace
PLUGINS_REL = "harness/.claude/plugins"
SKILLS_REL = "harness/.claude/skills"
AGENTS_REL = "harness/.claude/agents"
PROMPTS_REL = "harness/.claude/prompts"
MARKETPLACE_REL = "harness/.claude/marketplace"
MCP_REL = "harness/src/platform/mcp"         # the EPC MCP server package (pyproject.toml, src/epc_mcp, tests)
EVALS_REL = "harness/tests/evals"
TOOLS_REL = "harness/tools"
ARCHIVE_REL = "_archive"                     # superseded material, moved here instead of deleted (MIG-29)
PLANNING_REL = "_archive/planning"           # BOARD.md, epics, stories and releases checked by tools/planning/board.py (archived in MIG-29)
INCOMING_REL = "_archive/incoming"           # staging folder of tools/dev/new_module.py (archived in MIG-29)

# Engine package -> folder relative to the repository root. Packages keep their names (decision M6); only the folder changes when they are relocated.
CAD_ENGINES_REL = "harness/src/engines/cad"      # group folder of the drawing engines (MIG-24a, MIG-24f)
VALIDATION_ENGINES_REL = "harness/src/engines/validation"      # group folder of the rules and standards engines (MIG-24b)
CALCULATION_ENGINES_REL = "harness/src/engines/calculation"      # group folder of the calculation engines (MIG-24c, MIG-24d, MIG-24e)
QUALITY_ENGINES_REL = "harness/src/engines/quality"      # group folder of the document-quality engines (MIG-24g)
PROCUREMENT_ENGINES_REL = "harness/src/engines/procurement"      # group folder of the procurement engines (MIG-39c)
GEOMETRY_ENGINES_REL = "harness/src/engines/geometry"                # group folder of the generic geometry engines (expr, arrays)
BIM_ENGINES_REL = "harness/src/engines/bim"                          # group folder of the building engines (walls)
FABRICATION_ENGINES_REL = "harness/src/engines/fabrication"      # group folder of the fabrication engines (cut list)
_GROUP_OF = {**{n: CAD_ENGINES_REL for n in ("dxf", "symbols", "titleblock", "plan", "arch", "sld", "mld", "drawing")}, **{n: VALIDATION_ENGINES_REL for n in ("rules", "standards", "calc_check")}, **{n: CALCULATION_ENGINES_REL for n in ("aea90364", "calc_common", "load_balance", "voltage_drop", "feeder_sizing", "short_circuit", "grounding", "selectivity", "transformer_sizing", "hvac", "pv", "lighting", "receptacles")}, **{n: QUALITY_ENGINES_REL for n in ("documents", "terminal_blocks", "design_basis", "descriptive_report", "changes")}, **{n: PROCUREMENT_ENGINES_REL for n in ("boq", "datasheets", "rfq")}, **{n: FABRICATION_ENGINES_REL for n in ("cutlist",)}, **{n: BIM_ENGINES_REL for n in ("walls", "dims")}, **{n: GEOMETRY_ENGINES_REL for n in ("expr", "arrays")}}
ENGINE_FOLDERS_REL = {name: f"{_GROUP_OF.get(name, ENGINES_REL)}/{name}" for name in (
    "aea90364", "calc_common", "load_balance", "voltage_drop", "feeder_sizing", "short_circuit", "grounding", "selectivity", "transformer_sizing", "rules", "standards", "calc_check", "dxf", "symbols", "titleblock", "plan", "arch", "lighting", "receptacles", "hvac", "pv", "sld", "mld", "drawing", "documents", "terminal_blocks", "design_basis", "descriptive_report", "boq", "datasheets", "rfq", "cutlist", "walls", "dims", "expr", "arrays", "changes")}


def _p(rel: str) -> Path:
    return REPO / rel


ENGINES = _p(ENGINES_REL)
JURISDICTIONS = _p(JURISDICTIONS_REL)
DOCS = _p(DOCS_REL)
SCHEMAS = _p(SCHEMAS_REL)
CATALOG = _p(CATALOG_REL)
I18N = _p(I18N_REL)
MANAGEMENT = _p(MANAGEMENT_REL)
CLAUDE = _p(CLAUDE_REL)
PLUGINS = _p(PLUGINS_REL)
SKILLS = _p(SKILLS_REL)
AGENTS = _p(AGENTS_REL)
PROMPTS = _p(PROMPTS_REL)
MARKETPLACE = _p(MARKETPLACE_REL)
MCP = _p(MCP_REL)
EVALS = _p(EVALS_REL)
TOOLS = _p(TOOLS_REL)
ARCHIVE = _p(ARCHIVE_REL)
PLANNING = _p(PLANNING_REL)
INCOMING = _p(INCOMING_REL)
ENGINE_DIRS = [_p(rel) for rel in ENGINE_FOLDERS_REL.values()]


def engine_dir(name: str) -> Path:
    """Folder of the engine package `name` (for example `aea90364`)."""
    return _p(ENGINE_FOLDERS_REL[name])


def engine_src(name: str) -> Path:
    """`src/` folder of the engine package `name`."""
    return engine_dir(name) / "src"


def engine_src_rel(name: str) -> str:
    """`src/` folder of the engine package `name`, relative to the repository root, with forward slashes."""
    return f"{ENGINE_FOLDERS_REL[name]}/src"


def norm_data_dir(name: str) -> Path:
    """Folder with the norm data of the engine `name` (for example `aea90364`), inside the normative folder."""
    return _p(NORM_DATA_REL[name])


def current_location(rel: str) -> str:
    """Repo-relative path of a file as it is now: a file of norm data that moved in MIG-37a is mapped to its new place, any other path is returned unchanged."""
    for old, new in MOVED_NORM_DATA.items():
        if rel == old or (old.endswith("/") and rel.startswith(old)):
            return new + rel[len(old):]
    return rel


def engine_names() -> list[str]:
    return list(ENGINE_FOLDERS_REL)
