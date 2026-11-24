"""expr: a safe arithmetic expression evaluator (no eval) for parametric values, fields and dimension formulas.

Generic geometry engine: it holds no norm value. Pure functions, standard library only.
"""
from epc_expr.build import evaluate
from epc_expr.errors import ExprError

__all__ = ["evaluate", "ExprError"]
__version__ = "0.1.0"
