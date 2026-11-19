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

## From the request to the pipeline (house flow)

Type the whole request (for example "a house with 4 bedrooms, 2 bathrooms, a garden, lighting and receptacles"), tick or accept the disciplines, give the project folder and attach the documents; nothing is asked by chat.

1. **Reading the request** (`brief.py`, fixed rules, es/en, no model): counts of rooms, the garden, the services and the disciplines. The ticks and the chips under the box show what was understood.
2. **Proposal** (`house.py`, sizes in `house_defaults.json`, all pending review): the rooms as boxes in metres (public band to the south, private band to the north, walls lined up, usual living room and kitchen added when not named), door and window rules, the board place. Everything lands in editable fields: the rooms table, and the "House assumptions" tab (heights, luminaire, outlet, board power factor, garden). The tabs say how many required fields are still empty (client, address, earthing scheme, short-circuit level and its origin, voltage); those cannot be proposed.
3. **Run** (`build.py`, `runner.py`): `Run` draws the plans with `epc_arch.author` (plan, isometric, elevation, section), reads them back with the same reader the pipeline uses, creates the project with `epc init`, stores the plans and documents as inputs and starts `epc run` (12 stages) in the background. The page shows the stage list as the pipeline records it and, at the end, the deliverables of the transmittal by numbered folder (`01_SLD`, `02_MLD`, `03_ARCHITECTURE`, `04_PLANS`, `06_DOCUMENTS`, `07_TABLES`...), each file a link, plus the project path.

Two floors ("two floors", "planta alta"): public rooms on PB, bedrooms and bathrooms on P1, a stair room on both (the plan reader drops rooms narrower than 2.4 m), the board next to the stair and the riser routed by the pipeline. Limits: at most two floors, stairs drawn only as a room, no roofs; no hall is generated (the plan reader splits halls into phantom rooms: BACKLOG LND-02); free-form descriptions, sizes and negations ("without garden") need a language model (LND-03).
