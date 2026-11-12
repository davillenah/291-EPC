"""Load list by area (JSON file) read into load_list.schema.json; unknown fields are rejected."""
import json
from pathlib import Path

from disciplines.electrical_lv.intake.schema_check import load_schema, validate


class LoadListError(ValueError):
    """The load list is not valid JSON or does not conform to the schema; `errors` lists the reasons."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = list(errors)


def read_load_list(path):
    """Read and validate a load-list file; return the data as written."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LoadListError([f"{Path(path).name}: cannot be read as JSON ({exc})"]) from exc
    errors = validate(data, load_schema("load_list.schema.json"))
    if errors:
        raise LoadListError(errors)
    return data
