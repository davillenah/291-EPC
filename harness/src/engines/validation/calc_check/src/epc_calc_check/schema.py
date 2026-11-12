"""A small JSON Schema (draft-07) validator: only the keywords `deliverable_manifest.schema.json` needs.

Supported: type (name or list of names), enum, required, properties, additionalProperties (false or a schema), minLength, pattern, items, minItems,
if / then / else. Any other keyword is ignored. It returns error strings, it never raises on bad data.
"""
import re


def _is_type(value, name):
    checks = {"object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list), "string": lambda v: isinstance(v, str),
              "boolean": lambda v: isinstance(v, bool), "null": lambda v: v is None,
              "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
              "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)}
    return checks.get(name, lambda v: True)(value)


def _type_errors(value, schema, path):
    names = schema.get("type")
    if names is None:
        return []
    names = [names] if isinstance(names, str) else names
    return [] if any(_is_type(value, n) for n in names) else [f"{path}: expected {'/'.join(names)}"]


def _string_errors(value, schema, path):
    if not isinstance(value, str):
        return []
    errors = []
    if len(value) < schema.get("minLength", 0):
        errors.append(f"{path}: shorter than {schema['minLength']}")
    if "pattern" in schema and not re.search(schema["pattern"], value):
        errors.append(f"{path}: does not match {schema['pattern']}")
    return errors


def _property_errors(key, item, schema, path):
    props, extra = schema.get("properties", {}), schema.get("additionalProperties")
    if key in props:
        return validate(item, props[key], f"{path}/{key}")
    if extra is False:
        return [f"{path}: unexpected '{key}'"]
    return validate(item, extra, f"{path}/{key}") if isinstance(extra, dict) else []


def _object_errors(value, schema, path):
    if not isinstance(value, dict):
        return []
    errors = [f"{path}: missing '{k}'" for k in schema.get("required", []) if k not in value]
    for key, item in value.items():
        errors += _property_errors(key, item, schema, path)
    return errors


def _array_errors(value, schema, path):
    if not isinstance(value, list):
        return []
    errors = [f"{path}: fewer than {schema['minItems']} items"] if len(value) < schema.get("minItems", 0) else []
    for i, item in enumerate(value):
        errors += validate(item, schema.get("items", {}), f"{path}/{i}")
    return errors


def _condition_errors(value, schema, path):
    if "if" not in schema:
        return []
    branch = "then" if not validate(value, schema["if"], path) else "else"
    return validate(value, schema[branch], path) if branch in schema else []


def validate(value, schema, path="$"):
    """Error strings of `value` against `schema` (empty list = valid)."""
    if not isinstance(schema, dict):
        return []
    errors = _type_errors(value, schema, path)
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not one of {schema['enum']}")
    return errors + _string_errors(value, schema, path) + _object_errors(value, schema, path) + _array_errors(value, schema, path) + _condition_errors(value, schema, path)
