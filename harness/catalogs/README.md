# Manufacturer catalog (organization data)

Status: **implemented**

One folder per manufacturer under `manufacturers/<id>/`:

- `manufacturer.json`: who they are (name, country, web, product categories).
- `<category>.json` (for example `breakers.json`, `cables.json`): the product families and models of that category.

Rules:

- Only facts (ratings, standards, ranges). No text copied from catalogs.
- Every product has a `source` (page it came from) and a `status`: `unverified` until someone checks it against the maker's current catalog, then `verified`.
- A value that is not known is left out; never guessed.
- The owner's PDF catalogs update these files later (see `E4-05` in `harness/docs/BACKLOG.md`).
- Shape: `harness/schemas/manufacturer_catalog.schema.json`.
