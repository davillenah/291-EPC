# `landing`

Status: **in development**

One-screen local page to talk to the harness: a request box, the discipline checklist, the dynamic guided form, the project folder and the documentation drop zone.

```
python harness/tools/landing/server.py [--port 8291] [--projects-root DIR]
```

Then open `http://127.0.0.1:8291`. Standard library only.

- The electrical form is built from `harness/schemas/intake_answers.schema.json`; validation uses the harness validator (D24 included); submit runs `epc init` through the CLI.
- Architectural fields follow the description taken by `epc_arch.author`; the other disciplines have no intake yet, so their request is saved under `_pending/` and nothing is calculated.
- The last folder of the project path is the project code. The folder must be outside the repository. The request and the attached files are stored as intake inputs (`inputs/minutes/`, `inputs/docs/`).
- The page is in English and Spanish (ES/EN switch).
