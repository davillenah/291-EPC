"""A logo as data (ADR-0042): the title block engine is handed the bytes, it does not look for the file."""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Logo:
    """`name` is the file name (its extension says SVG or PNG), `data` its bytes."""
    name: str
    data: bytes


def as_logo(value) -> Optional[Logo]:
    """A `Logo` as it comes, or the one a path names (read here: this is the caller's side of the door); None when there is no logo or no such file."""
    if isinstance(value, Logo):
        return value
    if value and os.path.isfile(value):
        with open(value, "rb") as f:
            return Logo(os.path.basename(str(value)), f.read())
    return None
