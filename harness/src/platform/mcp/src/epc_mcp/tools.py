"""The tools of the `epc` server: every tool calls `epc_platform.api` (MIG-38b retired the tools that read the parked web backend)."""
from epc_mcp import pipeline_tools
from epc_mcp.registry import Registry


def build_registry() -> Registry:
    reg = Registry()
    pipeline_tools.register(reg)
    return reg
