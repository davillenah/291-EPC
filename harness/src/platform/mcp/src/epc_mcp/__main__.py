"""python -m epc_mcp: serve the `epc` tools on stdio. EPC_PROJECTS = projects root; EPC_MCP_PROFILE = full | readonly;
EPC_ACTOR_ROLE / EPC_ACTOR_ID = the RACI role and id the pipeline tools act as (default orchestrator / mcp)."""
import os
import sys
from pathlib import Path

from epc_mcp.protocol import serve
from epc_mcp.registry import PROFILES, Context
from epc_mcp.tools import build_registry


def main() -> int:
    root = os.environ.get("EPC_PROJECTS")
    if not root:
        sys.stderr.write("EPC_PROJECTS is not set\n")
        return 2
    profile = os.environ.get("EPC_MCP_PROFILE", "full")
    if profile not in PROFILES:
        sys.stderr.write("EPC_MCP_PROFILE must be one of %s\n" % ", ".join(PROFILES))
        return 2
    actor = {"role": os.environ.get("EPC_ACTOR_ROLE", "orchestrator"), "id": os.environ.get("EPC_ACTOR_ID", "mcp")}
    serve(build_registry(), Context(Path(root), profile, actor=actor), sys.stdin, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
