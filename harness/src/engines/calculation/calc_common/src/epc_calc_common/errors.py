"""The error of the engine: a code with an English and a Spanish text (ADR-0039)."""
from epc_calc_common.messages import text


class CalcCommonError(ValueError):
    """A value or a table lookup is not valid: `str(error)` is the Spanish text (as before), `en` the English one, `code` the stable code."""

    def __init__(self, code: str, **params):
        t = text(code, **params)
        super().__init__(t["es"])        # this engine's messages were Spanish first and pinned that way by golden files: `str(error)` stays Spanish, `.en` is the English text
        self.code, self.en, self.es = code, t["en"], t["es"]
