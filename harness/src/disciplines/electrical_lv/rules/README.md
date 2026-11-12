# `rules`

Status: **in development**

Rules the discipline owns, as data: `preconditions.json` lists, per stage, what the context must hold before the stage runs (for example a non-empty load list and the verified inputs of stage 3), and `design_rules.py` loads it and returns finding-shaped dicts for what is missing. It holds no norm values.
