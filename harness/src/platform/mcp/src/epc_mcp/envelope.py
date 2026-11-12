"""The answer every tool returns: {ok, data, warnings[], reason?, confidence?} or {ok:false, error:{code, message}}."""
from typing import Any, List, Optional


class ToolError(Exception):
    """A failure a tool reports to the caller (never raised across the protocol)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def ok(data: Any = None, warnings: Optional[List[str]] = None, reason: Optional[str] = None,
       confidence: Optional[str] = None) -> dict:
    out = {"ok": True, "data": data, "warnings": list(warnings or [])}
    if reason is not None:
        out["reason"] = reason
    if confidence is not None:
        out["confidence"] = confidence
    return out


def fail(code: str, message: str) -> dict:
    return {"ok": False, "error": {"code": code, "message": message}}
