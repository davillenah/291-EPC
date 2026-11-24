"""The expression evaluator: hand-checked values, precedence, functions, variables and every error."""
import math
import unittest

from epc_expr import ExprError, api, evaluate


class ValueTests(unittest.TestCase):
    def test_arithmetic_and_precedence(self):
        for source, expected in (("1+2*3", 7), ("(1+2)*3", 9), ("10/4", 2.5), ("7%4", 3), ("-7%4", 1), ("2^3^2", 512), ("-2^2", -4), ("2^-1", 0.5),
                                 ("--3", 3), ("+3", 3), ("1e2+.5", 100.5), ("2 * ( 3 + 4 ) - 1", 13)):
            with self.subTest(source=source):
                self.assertAlmostEqual(evaluate(source), expected)

    def test_functions_and_constant(self):
        for source, expected in (("abs(-3)", 3), ("sqrt(16)", 4), ("sin(30)", 0.5), ("cos(60)", 0.5), ("tan(45)", 1), ("ceil(1.2)", 2), ("floor(-1.2)", -2),
                                 ("round(2.5)", 3), ("round(-2.5)", -2), ("log(exp(2))", 2), ("pi", math.pi), ("PI*2", 2 * math.pi), ("SQRT(9)", 3),
                                 ("PtDist(0,0,3,4)", 5), ("PtAngle(0,0,0,1)", 90), ("PtAngle(0,0,-1,0)", 180), ("PtAngle(0,0,0,-1)", 270)):
            with self.subTest(source=source):
                self.assertAlmostEqual(evaluate(source), expected)

    def test_variables(self):
        self.assertAlmostEqual(evaluate("w*h/2", {"w": 4, "h": 3}), 6)
        self.assertAlmostEqual(evaluate("pi", {"x": 1}), math.pi)

    def test_nesting_inside_the_limit(self):
        self.assertEqual(evaluate("(" * 20 + "1" + ")" * 20), 1)


class ErrorTests(unittest.TestCase):
    def check(self, code, source, variables=None):
        with self.assertRaises(ExprError) as c:
            evaluate(source, variables)
        self.assertEqual(c.exception.code, code)
        self.assertTrue(c.exception.en and c.exception.es and c.exception.en != c.exception.es)

    def test_errors(self):
        self.check("err_not_text", "")
        self.check("err_not_text", 5)
        self.check("err_too_long", "1+" * 600)
        self.check("err_too_deep", "(" * 60 + "1" + ")" * 60)
        self.check("err_too_deep", "-" * 60 + "1")
        self.check("err_syntax", "1 + $")
        self.check("err_syntax", "1 +")
        self.check("err_syntax", "1 2")
        self.check("err_syntax", "(1")
        self.check("err_syntax", "sin(30")
        self.check("err_unknown_name", "x+1")
        self.check("err_unknown_function", "foo(1)")
        self.check("err_arity", "sin(1,2)")
        self.check("err_arity", "ptdist(1,2,3)")
        self.check("err_arity", "abs()")
        self.check("err_division_by_zero", "1/0")
        self.check("err_division_by_zero", "1%0")
        self.check("err_math_domain", "sqrt(-1)")
        self.check("err_math_domain", "log(0)")
        self.check("err_math_domain", "tan(90)")
        self.check("err_math_domain", "exp(1000)")
        self.check("err_math_domain", "(-8)^0.5")
        self.check("err_math_domain", "10^1000")
        self.check("err_not_finite", "1e308*10")
        self.check("err_bad_variable", "1", {"1x": 1})
        self.check("err_bad_variable", "1", {"x": float("nan")})
        self.check("err_bad_variable", "1", {"x": True})
        self.check("err_bad_variable", "1", {5: 1})

    def test_it_never_runs_code(self):
        self.check("err_syntax", "__import__('os').system('x')")
        self.check("err_unknown_name", "__import__")


class DoorTests(unittest.TestCase):
    def test_the_public_door(self):
        self.assertEqual(sorted(api.__all__), ["ExprError", "evaluate"])


if __name__ == "__main__":
    unittest.main()
