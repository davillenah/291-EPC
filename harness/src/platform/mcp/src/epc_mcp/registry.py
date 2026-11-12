"""Tool registry: what each tool is, which profile may call it, and a call that never raises."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from epc_mcp import guard
from epc_mcp.envelope import ToolError, fail, ok

PROFILES = ("full", "readonly")


DEFAULT_ACTOR = {"role": "orchestrator", "id": "mcp"}


def utc_now() -> str:
    """The default clock of the server (the only place of the MCP layer that reads the system clock); tests inject their own."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Context:
    projects_root: Path
    profile: str = "full"
    clock: Optional[Callable[[], str]] = None
    actor: Optional[dict] = None

    def now(self) -> str:
        return (self.clock or utc_now)()

    def who(self) -> dict:
        """The RACI role and id this server acts as (the platform checks every call against it)."""
        return dict(self.actor or DEFAULT_ACTOR)

    def project(self, args: dict) -> Path:
        return guard.project_dir(self.projects_root, args.get("project"))


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[[Context, dict], Any]
    properties: Dict[str, dict] = field(default_factory=dict)
    required: List[str] = field(default_factory=lambda: ["project"])
    profiles: tuple = ("full", "readonly")

    def schema(self) -> dict:
        return {"name": self.name, "description": self.description,
                "inputSchema": {"type": "object", "properties": self.properties, "required": self.required}}


class Registry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        if tool.name in self._tools:
            raise ValueError("duplicate tool %s" % tool.name)
        self._tools[tool.name] = tool
        return tool

    def names(self, profile: str = "full") -> List[str]:
        return sorted(n for n, t in self._tools.items() if profile in t.profiles)

    def list(self, profile: str = "full") -> List[dict]:
        return [self._tools[n].schema() for n in self.names(profile)]

    def call(self, name: str, args: Optional[dict], ctx: Context) -> dict:
        tool = self._tools.get(name) if isinstance(name, str) else None
        if tool is None or ctx.profile not in tool.profiles:
            return fail("unknown_tool", "no tool %s in profile %s" % (name, ctx.profile))
        if args is None:
            args = {}
        if not isinstance(args, dict):
            return fail("invalid_arguments", "arguments must be an object")
        missing = [r for r in tool.required if r not in args]
        if missing:
            return fail("invalid_arguments", "missing: " + ", ".join(missing))
        try:
            result = tool.handler(ctx, args)
        except ToolError as e:
            return fail(e.code, e.message)
        except Exception as e:  # nothing raises across the protocol
            return fail("internal_error", "%s: %s" % (type(e).__name__, e))
        if isinstance(result, dict) and "ok" in result:
            return result
        return ok(result)
