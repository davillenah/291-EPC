# epc_dims

Generic building engine: automatic exterior dimensions from straight walls and their openings. Plan geometry only, in the unit the caller uses; pure functions,
standard library only.

```python
from epc_dims.api import dimensions

result = dimensions(walls, openings=openings, tol=1, gap=900, step=600, min_wall=1)
```

What it does: the outer face of each wall gives the bounds of the building; a total dimension on the south edge (X) and the west edge (Y); one chain along each of
the four edges from stop to stop (wall ends, opening edges, the centre of every wall that arrives at the edge); the chain row at `gap` from the outer face and the
total one `step` farther; a dimension whose two points already exist (in either order) is not made again. Each dimension is `{id, kind, edge, orientation, p1, p2,
line, value}`; drawing it (native DIMENSION or exploded) is the job of the drawing engine.

What it does not do (and says so in a note): interior rooms, grid axes, installation heights, text collisions, curved or oblique walls. `gap`, `step`, `tol` and
`min_wall` have no defaults: they are design choices of the project, not norm values.

Annotation sizes: `annotation_size(paper_mm, scale_denominator, drawing_unit_mm)` gives the size in drawing units of something that measures `paper_mm` on the
plotted sheet at the scale `1:N` (a 2.5 mm text at 1:50 is 125 in a drawing in millimetres, 12.5 in centimetres, 0.125 in metres); `paper_size` is the inverse.
The engine holds no list of scales: the project chooses.
