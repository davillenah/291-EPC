"""The answer every API function returns: {ok, data, warnings[]} or {ok: false, error: {code, message, details?}}.

The shape is the one of the MCP server's envelope, so the MCP tools and the CLI hand the dicts through unchanged. Nothing raises across the
API boundary: `api_call` turns `ApiError` (and any unexpected exception) into an error envelope.
"""
import functools
import json


class ApiError(Exception):
    """A failure an API function reports to its caller. `code` is a short machine word; `details` is plain JSON (optional)."""

    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def plain(value):
    """A JSON round trip: the same data as plain dicts, lists, strings, numbers, booleans and None."""
    return json.loads(json.dumps(value, default=str))


def ok(data=None, warnings=None):
    return {"ok": True, "data": plain(data), "warnings": list(warnings or [])}


def fail(code, message, details=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = plain(details)
    return {"ok": False, "error": error}


def api_call(function):
    """Decorator: the function returns an envelope; `ApiError` and unexpected exceptions become error envelopes."""
    @functools.wraps(function)
    def run(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ApiError as exc:
            return fail(exc.code, exc.message, exc.details)
        except Exception as exc:  # nothing raises across the API boundary
            return fail("internal_error", f"{type(exc).__name__}: {exc}")
    return run
