"""Recursive-descent evaluation of the token list. Grammar (lowest to highest precedence):

    sum     := product (('+' | '-') product)*
    product := unary (('*' | '/' | '%') unary)*
    unary   := ('-' | '+') unary | power
    power   := atom ('^' unary)?                    # right associative: 2^3^2 = 2^9; -2^2 = -4; 2^-1 = 0.5
    atom    := number | name | name '(' [sum (',' sum)*] ')' | '(' sum ')'

`%` is the remainder with the sign of the divisor (Python's `%`).
"""
import math

from epc_expr.errors import ExprError

MAX_DEPTH = 50


def _pt_dist(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def _pt_angle(x1, y1, x2, y2):
    """Angle of the line from the first point to the second, in degrees, from 0 (included) to 360 (excluded)."""
    return math.degrees(math.atan2(y2 - y1, x2 - x1)) % 360.0


def _checked(name, test, function):
    def call(x):
        if not test(x):
            raise ExprError("err_math_domain", name=name, value=x)
        return function(x)
    return call


FUNCTIONS = {
    "abs": (1, abs), "sin": (1, lambda x: math.sin(math.radians(x))), "cos": (1, lambda x: math.cos(math.radians(x))),
    "tan": (1, _checked("tan", lambda x: abs(math.cos(math.radians(x))) > 1e-12, lambda x: math.tan(math.radians(x)))),
    "sqrt": (1, _checked("sqrt", lambda x: x >= 0, math.sqrt)), "ceil": (1, lambda x: float(math.ceil(x))), "floor": (1, lambda x: float(math.floor(x))),
    "round": (1, lambda x: float(math.floor(x + 0.5))), "log": (1, _checked("log", lambda x: x > 0, math.log)),
    "exp": (1, _checked("exp", lambda x: x < 700, math.exp)), "ptdist": (4, _pt_dist), "ptangle": (4, _pt_angle),
}
CONSTANTS = {"pi": math.pi}


class Parser:
    def __init__(self, tokens, variables):
        self.tokens, self.at, self.variables, self.depth = tokens, 0, variables, 0

    def _peek(self):
        return self.tokens[self.at]

    def _take(self):
        token = self.tokens[self.at]
        self.at += 1
        return token

    def _op(self, *symbols):
        kind, value, _ = self._peek()
        return value if kind == "op" and value in symbols else None

    def _enter(self):
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise ExprError("err_too_deep", limit=MAX_DEPTH)

    def parse(self):
        value = self.sum()
        kind, _, position = self._peek()
        if kind != "end":
            raise ExprError("err_syntax", at=position, what="unexpected token")
        return value

    def sum(self):
        value = self.product()
        while (op := self._op("+", "-")):
            self._take()
            value = value + self.product() if op == "+" else value - self.product()
        return value

    def product(self):
        value = self.unary()
        while (op := self._op("*", "/", "%")):
            _, _, position = self._take()
            right = self.unary()
            value = self._apply(op, value, right)
        return value

    @staticmethod
    def _apply(op, left, right):
        if op == "*":
            return left * right
        if right == 0:
            raise ExprError("err_division_by_zero")
        return left / right if op == "/" else left % right

    def unary(self):
        self._enter()
        sign = self._op("-", "+")
        if sign:
            self._take()
            value = self.unary()
            self.depth -= 1
            return -value if sign == "-" else value
        value = self.power()
        self.depth -= 1
        return value

    def power(self):
        base = self.atom()
        if self._op("^"):
            self._take()
            exponent = self.unary()
            try:
                return math.pow(base, exponent)
            except (ValueError, OverflowError):
                raise ExprError("err_math_domain", name="^", value=base) from None
        return base

    def atom(self):
        kind, value, position = self._take()
        if kind == "number":
            return value
        if kind == "name":
            return self.call(value, position) if self._op("(") else self.name(value)
        if kind == "op" and value == "(":
            self._enter()
            inner = self.sum()
            self.depth -= 1
            self._close()
            return inner
        raise ExprError("err_syntax", at=position, what="a value was expected")

    def _close(self):
        kind, value, position = self._take()
        if not (kind == "op" and value == ")"):
            raise ExprError("err_syntax", at=position, what="')' was expected")

    def name(self, name):
        key = name.lower()
        if key in CONSTANTS:
            return CONSTANTS[key]
        if name in self.variables:
            return self.variables[name]
        raise ExprError("err_unknown_name", name=name)

    def call(self, name, position):
        key = name.lower()
        if key not in FUNCTIONS:
            raise ExprError("err_unknown_function", name=name, known=", ".join(sorted(FUNCTIONS)))
        self._take()
        args = self._arguments()
        expected, function = FUNCTIONS[key]
        if len(args) != expected:
            raise ExprError("err_arity", name=name, expected=expected, got=len(args))
        return function(*args)

    def _arguments(self):
        args = []
        if not self._op(")"):
            args.append(self.sum())
            while self._op(","):
                self._take()
                args.append(self.sum())
        self._close()
        return args
