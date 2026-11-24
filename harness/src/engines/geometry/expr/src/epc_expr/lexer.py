"""Splits an expression into tokens: numbers, names, the operators `+ - * / ^ %`, parentheses and commas."""
import re

from epc_expr.errors import ExprError

TOKEN = re.compile(r"\s*(?:(?P<number>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)|(?P<name>[A-Za-z_][A-Za-z0-9_]*)|(?P<op>[-+*/^%(),]))")


def tokenize(source):
    """`[(kind, value, position)]` with kind `number`, `name` or `op`, ending with `('end', '', len)`."""
    tokens, at = [], 0
    while at < len(source) and source[at:].strip():
        found = TOKEN.match(source, at)
        if found is None:
            raise ExprError("err_syntax", at=at + 1 + len(source[at:]) - len(source[at:].lstrip()), what="unexpected character")
        kind = found.lastgroup
        tokens.append((kind, float(found.group(kind)) if kind == "number" else found.group(kind), found.start(kind) + 1))
        at = found.end()
    tokens.append(("end", "", len(source) + 1))
    return tokens
