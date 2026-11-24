"""The error of the engine: a code with an English and a Spanish text (ADR-0039)."""
from epc_walls.messages import text


class WallsError(ValueError):
    """The input or a step is not valid: `str(error)` is the English text, `es` the Spanish one, `code` the stable code."""

    def __init__(self, code: str, **params):
        t = text(code, **params)
        super().__init__(t["en"])
        self.code, self.en, self.es = code, t["en"], t["es"]
