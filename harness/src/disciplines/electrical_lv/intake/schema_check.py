"""Small JSON Schema validator (draft-07 subset) using only the standard library.

Supported keywords: type, enum, required, properties, additionalProperties (false), minLength, pattern,
minimum, exclusiveMinimum, items, minItems, and the conditional if / then / else (used by the project profile and state
schemas: nulls are allowed only while `status` is `template`). Any other keyword in a schema is ignored, so the schemas
under harness/schemas stay usable by a full validator as well.
"""
import json
import re
from pathlib import Path

SCHEMAS = Path(__file__).resolve().parents[4] / "schemas"

_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def load_schema(name):
    """Read harness/schemas/<name>."""
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _is_type(value, name):
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, _TYPES[name])


def _same(a, b):
    """Equality that does not treat True as 1."""
    return type(a) is type(b) and a == b if isinstance(a, bool) or isinstance(b, bool) else a == b


def _check_number(value, schema, where):
    errors = []
    if "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{where}: must be at least {schema['minimum']}")
    if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
        errors.append(f"{where}: must be greater than {schema['exclusiveMinimum']}")
    return errors


def _check_string(value, schema, where):
    errors = []
    if len(value) < schema.get("minLength", 0):
        errors.append(f"{where}: must not be empty")
    if "pattern" in schema and not re.search(schema["pattern"], value):
        errors.append(f"{where}: does not match {schema['pattern']}")
    return errors


def _check_scalar(value, schema, where):
    errors = []
    if "enum" in schema and not any(_same(value, e) for e in schema["enum"]):
        errors.append(f"{where}: must be one of {schema['enum']}")
    if isinstance(value, str):
        errors += _check_string(value, schema, where)
    elif _is_type(value, "number"):
        errors += _check_number(value, schema, where)
    return errors


def _check_object(value, schema, where):
    prefix = f"{where}." if where else ""
    errors = [f"{prefix}{k}: is required" for k in schema.get("required", []) if k not in value]
    props = schema.get("properties", {})
    for key, sub in value.items():
        if key in props:
            errors += validate(sub, props[key], f"{prefix}{key}")
        elif schema.get("additionalProperties") is False:
            errors.append(f"{prefix}{key}: unknown field")
    return errors


def _check_array(value, schema, where):
    errors = []
    if len(value) < schema.get("minItems", 0):
        errors.append(f"{where}: needs at least {schema['minItems']} items")
    for i, item in enumerate(value):
        errors += validate(item, schema.get("items", {}), f"{where}[{i}]")
    return errors


def _check_conditional(value, schema, where):
    """if / then / else: `then` applies when the value conforms to `if`, `else` when it does not."""
    if "if" not in schema:
        return []
    branch = schema.get("then" if not validate(value, schema["if"], where) else "else")
    return validate(value, branch, where) if branch else []


def validate(value, schema, where=""):
    """List of readable errors ("path: message"); empty when the value conforms."""
    return _validate_base(value, schema, where) + _check_conditional(value, schema, where)


def _validate_base(value, schema, where):
    wanted = schema.get("type")
    wanted = [wanted] if isinstance(wanted, str) else (wanted or [])
    if wanted and not any(_is_type(value, t) for t in wanted):
        return [f"{where or 'value'}: must be of type {' or '.join(wanted)}"]
    if isinstance(value, dict):
        return _check_object(value, schema, where)
    if isinstance(value, list):
        return _check_array(value, schema, where)
    return _check_scalar(value, schema, where or "value")
