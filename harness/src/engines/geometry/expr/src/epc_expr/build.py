"""The public function of the engine: `evaluate`."""
import math
import re

from epc_expr.errors import ExprError
from epc_expr.lexer import tokenize
from epc_expr.parser import Parser

MAX_LENGTH = 1000
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def _variables(raw):
    checked = {}
    for name, value in (raw or {}).items():
        number = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        if not isinstance(name, str) or not NAME.match(name) or not number:
            raise ExprError("err_bad_variable", name=name, value=value)
        checked[name] = float(value)
    return checked


def evaluate(expression, variables=None):
    """The value of an arithmetic expression as a float.

    Operators `+ - * / ^ %`, parentheses, functions `abs sin cos tan sqrt ceil floor round log exp PtDist PtAngle` (names are not case sensitive; angles are in
    degrees), the constant `pi` and the names given in `variables` (case sensitive; the constant `pi` cannot be overridden). Nothing is ever
    run as code. A result that is not a finite number is an error.
    """
    if not isinstance(expression, str) or not expression.strip():
        raise ExprError("err_not_text", value=expression)
    if len(expression) > MAX_LENGTH:
        raise ExprError("err_too_long", limit=MAX_LENGTH)
    value = Parser(tokenize(expression), _variables(variables)).parse()
    if not math.isfinite(value):
        raise ExprError("err_not_finite")
    return float(value)
