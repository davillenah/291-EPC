"""Write harness/docs/REVISION_NORMAS.md: everything the owner has to verify before a value feeds a calculation.

  python harness/tools/build/review_list.py          # (re)write the file
  python harness/tools/build/review_list.py --check  # fail when it is out of date

Two sources, nothing typed by hand: the review units (read from the engines' data and `review.json`, `disciplines.electrical_lv.norm_review`) with their points still pending (what the owner approves) and the `[VERIFICAR]` marks the engines carry in their code
(a value or a clause that is still to be checked against the standard)."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import epc_paths as P  # noqa: E402

REPO = P.REPO
TARGET = P.DOCS / "REVISION_NORMAS.md"
ENGINES = ("aea90364", "calc_common", "load_balance", "voltage_drop", "feeder_sizing", "short_circuit", "grounding", "selectivity", "lighting", "receptacles", "plan", "hvac")
MARK = re.compile(r"\[VERIFICAR\]")


def _comment_text(t: str) -> str:
    return re.sub(r"^#\s*", "", t)[:150]


def _norm_units() -> list:
    """The units of the norms review: [(name, total, pending)]. Read from the engines' data and `review.json`, no backend (MIG-38b)."""
    sys.path[:0] = [str(REPO / "harness" / "src")] + [str(P.engine_src(n)) for n in P.engine_names()]
    from disciplines.electrical_lv import norm_review
    return [(u["name"], u["counts"]["total"], u["counts"]["pending"] + u["counts"]["stale"]) for u in norm_review.units()]


def _marks() -> dict:
    """The [VERIFICAR] marks of the engines: {file: [(line, text)]}."""
    out = {}
    for engine in ENGINES:
        for path in sorted((P.engine_src(engine)).rglob("*.py")):
            hits = [(n, line.strip()) for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if MARK.search(line)]
            if hits:
                out[path.relative_to(REPO).as_posix()] = hits
    return out


def text() -> str:
    units, marks = _norm_units(), _marks()
    pending = sum(p for _, _, p in units)
    lines = ["# Valores de normas que el dueño tiene que revisar", "",
             "Generado por `python harness/tools/build/review_list.py`; no se edita a mano. Un valor **sin revisar** se usa para calcular pero el resultado lo avisa; solo el dueño lo aprueba.", "",
             "## 1. En la página de normas", "",
             f"Se revisan en la pantalla de normas (aprobar, corregir o rechazar cada punto). Pendientes: **{pending}**.", "",
             "| Unidad | Puntos | Pendientes |", "|---|---:|---:|"]
    lines += [f"| {name} | {total} | {p} |" for name, total, p in units]
    lines += ["", "## 2. Marcas `[VERIFICAR]` en el código de los motores", "",
              f"Cada una es una fórmula, un valor o una cláusula que hay que contrastar con la norma. Total: **{sum(len(v) for v in marks.values())}** en {len(marks)} archivos.", ""]
    for path, hits in marks.items():
        lines += [f"### `{path}` ({len(hits)})", ""] + [f"- línea {n}: {_comment_text(t)}" for n, t in hits] + [""]
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    check = ap.parse_args(argv).check
    new = text()
    if check:
        old = TARGET.read_bytes().decode("utf-8").replace("\r\n", "\n") if TARGET.exists() else ""
        if old != new:
            print(f"{P.DOCS_REL}/REVISION_NORMAS.md is out of date: run `python harness/tools/build/review_list.py`")
            return 1
        return 0
    TARGET.write_text(new, encoding="utf-8", newline="\n")
    print(f"wrote {TARGET.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
