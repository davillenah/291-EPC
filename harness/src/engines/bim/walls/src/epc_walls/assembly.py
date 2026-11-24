"""Layered assemblies: layers from the exterior inward, the thickness that is their sum, bands across the wall and the priority of each layer.

The priority says which layer cuts which where walls meet (the stronger one cuts the weaker; equal priority never cuts). The defaults by function are a design
choice of this engine (params.json, pending review), not a norm; a layer may carry its own priority. Thicknesses and materials are inputs: nothing is invented.
"""
from epc_walls import inputs

PRIORITY = inputs.PARAMS["layer_priority_default"]


def validate(items):
    """The layers checked, with their derived thickness: `{layers, thickness}`."""
    checked = inputs.layers(items)
    return {"layers": checked, "thickness": round(sum(c["t"] for c in checked), 6)}


def priority(layer):
    """The priority of a layer: its own when set, else the default of its kind (a cavity) or of its function."""
    if layer.get("priority") is not None:
        return layer["priority"]
    return PRIORITY["cavity"] if layer.get("kind") == "cavity" else PRIORITY[layer["function"]]


def bands(items, ext_side="left"):
    """The bands of the layers across the wall: `[{index, lo, hi, priority, mat}]` sorted by `lo`.

    `lo` and `hi` are offsets from the centre line measured to the wall's LEFT (left of a to b); `ext_side` is the side of the exterior face, which is where
    the first layer is. Layers of no thickness (membranes) have no band.
    """
    checked = inputs.layers(items)
    total = sum(c["t"] for c in checked)
    out, edge = [], total / 2 if ext_side == "left" else -total / 2
    for index, layer in enumerate(checked):
        if layer["t"] > 0:
            near, far = edge, edge - layer["t"] if ext_side == "left" else edge + layer["t"]
            out.append({"index": index, "lo": round(min(near, far), 6), "hi": round(max(near, far), 6), "priority": priority(layer), "mat": layer["mat"]})
            edge = far
    return sorted(out, key=lambda b: b["lo"])
