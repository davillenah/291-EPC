"""MCP over stdio, written by hand: newline-delimited JSON-RPC 2.0 (initialize, ping, tools/list, tools/call)."""
import json
from typing import Optional

from epc_mcp.registry import Context, Registry

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "epc", "version": "0.1.0"}


def _error(rid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def handle(message: dict, registry: Registry, ctx: Context) -> Optional[dict]:
    """Answer one JSON-RPC message; notifications (no id) get no answer."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or "method" not in message:
        return _error(message.get("id") if isinstance(message, dict) else None, -32600, "invalid request")
    rid, method, params = message.get("id"), message["method"], message.get("params")
    if "id" not in message:
        return None
    if params is None:
        params = {}
    if not isinstance(method, str) or not isinstance(params, dict):
        return _error(rid, -32602, "invalid params")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": registry.list(ctx.profile)}}
    if method == "tools/call":
        result = registry.call(params.get("name", ""), params.get("arguments"), ctx)
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "content": [{"type": "text", "text": json.dumps(result, default=str)}],
            "isError": not result.get("ok", False)}}
    return _error(rid, -32601, "method not found: %s" % method)


def serve(registry: Registry, ctx: Context, stdin, stdout) -> None:
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            text = json.dumps(_error(None, -32700, "parse error"))
        else:
            try:
                answer = handle(message, registry, ctx)
                text = json.dumps(answer) if answer is not None else None
            except Exception as e:  # nothing raises across the protocol; the loop keeps serving
                rid = message.get("id") if isinstance(message, dict) else None
                answer = _error(rid, -32603, "internal error: %s" % type(e).__name__) if rid is not None else None
                text = json.dumps(answer) if answer is not None else None
        if text is not None:
            stdout.write(text + "\n")
            stdout.flush()
