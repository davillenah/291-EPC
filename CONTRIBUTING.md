# Contributing to EPC-291

Thanks for helping. Please read `CLAUDE.md` and `harness/CLAUDE.md` first: they hold the rules that agents and people follow.

## Workflow

1. Branch from `main`: `feat/<topic>`, `fix/<topic>`, `docs/<topic>` or `chore/<topic>`. Do not commit directly on `main` once the repository is public.
2. Make a focused change with its tests.
3. Run the gate before opening a pull request: `python harness/tools/ci/run_gate.py` (about 5 minutes). While you work, `python harness/tools/ci/run_gate.py --changed` tests only the engines your change can affect and the ones that depend on them. Never weaken a test or a check to make it pass (no skips, no lowered coverage floors).
4. Open a pull request using the template. A person from `.github/CODEOWNERS` reviews changes to norms, schemas, permissions and hooks.

## Commit messages (Conventional Commits 1.0)

```
<type>(<scope>): <short imperative summary, max 72 chars>

<body: what and why, wrapped at 72>

<footer: BREAKING CHANGE: ..., Refs: #123>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. Use a scope such as `engines`, `platform`, `agents`, `disciplines`, `docs`, `web`. Breaking changes use `!` after the scope or a `BREAKING CHANGE:` footer.

## Rules that never bend

- **Numbers come from engines.** No hand-written values in agents, skills or documents.
- **Norm values** are never approved, changed or "fixed" by an agent. A new value is recorded as `pending review` in the norm register, with its clause. Only a person approves.
- **Golden files** are not edited by hand; changes to expected results need an owner decision.
- **Copyright.** Never commit standards, book PDFs, scanned material or client data. `.gitignore` blocks `*.pdf`; keep licensed material in `harness/knowledge/normative/` (local only).
- **Single source of truth** per datum (ADR-0012). Generated files (`registry.json`, `DEPENDENCIAS.md`, agent files) are regenerated, never edited.

## Language

New code, identifiers, documentation and product content are written in English. Existing Spanish names are not renamed. The interface is localized (es/en).

## Adding a discipline

Create `harness/src/disciplines/<name>/` with a README (scope, status, lead agent, reference standards), register its engines under `harness/src/engines/`, add its lead agent to `harness/.claude/roster.disciplines.json` and run `python harness/tools/build/regen_agents.py`.

## License

By contributing you agree that your work is released under the [MIT License](LICENSE), keeping the owner's attribution.
