# epc_walls

Generic building engine: straight walls from an axis and either a thickness or a layer assembly, the join records between them (L, T, X) and the corner geometry
(mitre, butt, square). Plan geometry only, in the unit the caller uses; pure functions, standard library only.

```python
from epc_walls.api import outlines

result = outlines(
    [{"id": "A", "a": [0, 0], "b": [4000, 0], "t": 200},
     {"id": "B", "a": [4000, 0], "b": [4000, 3000], "layers": [
         {"mat": "finish", "t": 15, "function": "finish"}, {"mat": "block", "t": 185, "function": "structure"}]}],
    tol=1.0,                                   # no default on purpose
    styles={"A:end|B:start": {"style": "butt", "through": "A"}})
```

- `result["walls"][id]`: `thickness`, `outline` (four points), `layered`, and `bands` for layered walls (layers across the wall with the priority of each).
- `result["joins"]`: `key` (the same whatever the order of the pair), `kind` (`L`, `T`, `X`), the two ends, and `applied` (`mitre`, `butt`, `square`, `tee`, `cross`).
- `result["issues"]`: notes with a code and English and Spanish text; a corner that cannot be made as asked keeps square ends and says so.

Nothing here is a norm value: thicknesses and materials are inputs, and the design parameters (the sharpest mitre, the default layer priority by function) are in
`params.json`, marked `pending review`. The unit of `tol` is the unit of the points. Version 0.1 does not yet cut layers by priority at a junction and does not
handle openings; a node where three or more ends meet keeps square ends.
