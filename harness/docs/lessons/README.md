# lessons

Status: **implemented**

Engineering lessons learned and the solutions generated for problems found in simulations and in real projects. It is not about code (that is the CHANGELOG and the ADRs): it is what the work taught us about the engineering, so the next project starts from the standard solution and not from zero.

## What goes in and what does not
- **In:** a design or calculation decision that worked, a trap we fell into and how to avoid it, a standard way to solve a recurring problem (sizing, layout, drawing, documents, field), a limit found by stress testing, a question the owner answered that will come back.
- **Out:** norm values (only a person approves those; they live in the norm register, never here), copyrighted content (a standard, a data sheet or a book is never copied: cite title, edition and clause), real client data, and bugs without an engineering lesson (those go to `../BACKLOG.md`).

## How it is used
1. After a simulation, an exercise or a real project, write one lesson per file from `TEMPLATE.md`: `LL-NNNN-short-name.md` (next free number, see `INDEX.md`).
2. Add one row to `INDEX.md` (it is the only table; keep it sorted by number).
3. A lesson has a status: `proposed` (found, solution not tried), `validated` (tried in a run or a project, with the evidence), `standard` (the owner accepted it as the way we do it), `superseded` (replaced by another lesson, which it names).
4. Before designing something new, read the index for the discipline: if a lesson applies, use its solution and say so in the minutes of the project.
5. A lesson that needs a code change gets a `BACKLOG.md` id in its "Follow-up" line; the code is never described here.
6. Only the owner moves a lesson to `standard`. Values quoted in a lesson are examples from a run and stay `pending review`.

Language: English (owner rule), with a one-line Spanish summary in each file.
