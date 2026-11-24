"""Plane vectors as tuples. Pure functions; no imports from the rest of the engine."""
import math

EPS = 1e-9


def sub(p, q):
    return (p[0] - q[0], p[1] - q[1])


def mul(p, k):
    return (p[0] * k, p[1] * k)


def dot(p, q):
    return p[0] * q[0] + p[1] * q[1]


def cross(p, q):
    return p[0] * q[1] - p[1] * q[0]


def length(p):
    return math.hypot(p[0], p[1])


def unit(p):
    n = length(p)
    return (p[0] / n, p[1] / n)


def left(d):
    """The normal on the left of the unit vector `d`."""
    return (-d[1], d[0])


def intersect(p, d, q, e):
    """`(s, t)` with `p + s d == q + t e`, or None when the lines are parallel."""
    den = cross(d, e)
    if abs(den) < EPS:
        return None
    w = sub(q, p)
    return (cross(w, e) / den, cross(w, d) / den)


def at(p, d, s):
    return (p[0] + d[0] * s, p[1] + d[1] * s)


def round_point(p, places=6):
    return [round(p[0], places) + 0.0, round(p[1], places) + 0.0]
