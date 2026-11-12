"""Satisfaction rules: a product is a candidate only when catalog numbers satisfy the requirement by COMPARISON. Nothing is calculated.

A requirement the catalog cannot answer (no data) is not satisfied: requirements are never relaxed. The only soft points are the ones listed in
`unconfirmed` of a candidate (data the catalog does not carry at all, e.g. the section of a cable).
"""
import re


def rated_current_contains(rated, in_a):
    """True when the catalog rated-current data contains `in_a`: a list holds it, or an object has `max` and min <= in_a <= max (no `min` = no lower bound)."""
    if isinstance(rated, list):
        return in_a in rated
    if not isinstance(rated, dict) or "max" not in rated:
        return False
    return rated.get("min", 0) <= in_a <= rated["max"]


def capacity_entries(product, required_ka, voltage_v):
    """The catalog breaking-capacity entries with icu_ka >= required_ka (and, when the voltage is required, voltage_v >= the required voltage)."""
    return [dict(e) for e in product.get("breaking_capacity", [])
            if e["icu_ka"] >= required_ka and (voltage_v is None or e["voltage_v"] >= voltage_v)]


def device_match(requirement, product):
    """`None` when the product does not satisfy the device requirement, else `{"matched": {...}, "unconfirmed": [...]}`.

    Rules: the product is in a `breakers` document; its type equals the requested kind; its rated-current data contains In; when a breaking capacity is
    required, a catalog entry at a voltage >= the required one (any voltage when none is required) is >= the required kA; when poles are required and the
    catalog lists poles they must include them (no poles data = `unconfirmed`).
    """
    if product["category"] != "breakers" or product["type"] != requirement["device_kind"]:
        return None
    if not rated_current_contains(product.get("rated_current_a"), requirement["in_a"]):
        return None
    matched, unconfirmed = {"in_a": requirement["in_a"]}, []
    if requirement["breaking_capacity_ka"] is not None:
        entries = capacity_entries(product, requirement["breaking_capacity_ka"], requirement["voltage_v"])
        if not entries:
            return None
        matched["breaking_capacity"] = entries
    if requirement["poles"] is not None:
        if "poles" not in product:
            unconfirmed.append("poles")
        elif requirement["poles"] not in product["poles"]:
            return None
    return {"matched": matched, "unconfirmed": unconfirmed}


def mentions(text, word):
    return re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", text.lower()) is not None


def cable_match(requirement, product):
    """`None` when the product does not satisfy the cable requirement, else `{"matched": {...}, "unconfirmed": [...]}`.

    Rules: the product is in a `cables` document; when an insulation is required, the catalog `construction` or `family` text mentions it as a word.
    The catalog carries no material, section or conductor-count data: those are always `unconfirmed`.
    """
    if product["category"] != "cables":
        return None
    matched = {}
    if requirement["insulation"] is not None:
        if not mentions(f"{product.get('construction', '')} {product['family']}", requirement["insulation"]):
            return None
        matched["insulation"] = requirement["insulation"]
    return {"matched": matched, "unconfirmed": ["material", "section", "conductors"]}
