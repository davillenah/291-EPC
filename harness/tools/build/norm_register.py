"""Norm register: one organized, machine-checked place that lists every norm-based value with its clause and source.

  python harness/tools/build/norm_register.py                 # validate and print a summary
  python harness/tools/build/norm_register.py --check         # exit 1 when a record or a pointer is wrong
  python harness/tools/build/norm_register.py --report        # (re)write harness/docs/NORM_REGISTER.md
  python harness/tools/build/norm_register.py --report --check  # fail when harness/docs/NORM_REGISTER.md is out of date

Hand records live in `engine/<pkg>/src/<module>/norm_register/<topic>.json` (schema: harness/schemas/norm-register.schema.json). A record of type `json` only
POINTS to the data (single source of truth, ADR-0012); a record of type `code` carries the literal in `value`. The rules of the AEA engine and of the lighting
engine are indexed automatically from their own fields (no hand records). Review state is read from the AEA `review.json`; this tool never writes it."""
import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import epc_paths as P  # noqa: E402

REPO = P.REPO
SCHEMA = Path(P.SCHEMAS_REL) / "norm-register.schema.json"
TARGET = Path(P.DOCS_REL) / "NORM_REGISTER.md"
REVIEW = Path(P.engine_src_rel("aea90364")) / "epc_aea90364" / "data" / "review.json"
AEA_RULES = f"{P.NORM_DATA_REL['aea90364']}/rules/*.json"
LIGHTING_RULES = f"{P.engine_src_rel('lighting')}/epc_lighting/rules/*.json"
ENGINE_GROUPS = sorted({rel.rsplit("/", 1)[0] for rel in P.ENGINE_FOLDERS_REL.values()})            # engine/ and the group folders (harness/src/engines/cad)


def _src_index(parts) -> int:
    """Index of the `src` folder of the engine (the last one: the group folder harness/src/engines also has one)."""
    return len(parts) - 1 - parts[::-1].index("src")


REGISTER_GLOBS = [f"{g}/*/src/*/norm_register/*.json" for g in ENGINE_GROUPS]
REVIEW_POINT = re.compile(r"^(rule|lighting-rule|table|criterion):[a-z0-9-]+\|.+$")
CONFLICT = re.compile(r"^(conflicts with|duplicated literal)", re.I)
PIPE = "|"


def load_json(path: Path):
    return json.loads(path.read_bytes().decode("utf-8-sig"))


def slug(text) -> str:
    """Same rule as the backend `slugify`: lowercase letters and digits joined by single dashes."""
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


# ------------------------------------------------------------------ pointers and code symbols
def resolve_pointer(doc, pointer: str):
    """RFC 6901 lookup. Returns (True, value) or (False, reason)."""
    if pointer == "":
        return True, doc
    if not pointer.startswith("/"):
        return False, "pointer must start with '/'"
    cur = doc
    for raw in pointer[1:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict):
            if key not in cur:
                return False, f"key {key!r} not found"
            cur = cur[key]
        elif isinstance(cur, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", key) or int(key) >= len(cur):
                return False, f"index {key!r} not valid"
            cur = cur[int(key)]
        else:
            return False, f"cannot step into a scalar at {key!r}"
    return True, cur


def module_assignment(source: str, symbol: str):
    """The module-level assignment node of `symbol`, or None. Raises SyntaxError."""
    tree = ast.parse(source.lstrip("\ufeff"))
    found = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == symbol for t in node.targets):
                found = node
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == symbol and node.value is not None:
            found = node
    return found


def _plain(x):
    """Normalize a Python literal to what JSON would say (tuples and sets become lists)."""
    if isinstance(x, (tuple, list, set, frozenset)):
        return [_plain(i) for i in (sorted(x, key=repr) if isinstance(x, (set, frozenset)) else x)]
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    return x


# ------------------------------------------------------------------ schema
def schema_errors(data, schema_path: Path) -> list:
    """Messages from jsonschema (when installed) plus the cross-field rules we always enforce ourselves."""
    out = []
    try:
        import jsonschema
    except ImportError:
        jsonschema = None
    if jsonschema is not None:
        validator = jsonschema.Draft7Validator(load_json(schema_path))
        for e in sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.path))):
            out.append("schema: /" + "/".join(map(str, e.path)) + ": " + e.message[:160])
    else:
        if not isinstance(data, dict) or not isinstance(data.get("records"), list):
            out.append("schema: top level must be an object with a `records` list (jsonschema not installed: structural check only)")
    # the rule jsonschema also checks, kept here so it holds without the library
    for i, r in enumerate(data.get("records", []) if isinstance(data, dict) else []):
        if not isinstance(r, dict):
            continue
        loc = r.get("location") if isinstance(r.get("location"), dict) else {}
        if loc.get("type") == "code" and "value" not in r and jsonschema is None:
            out.append(f"schema: /records/{i}: `value` is required for a code location")
        if loc.get("type") == "json" and "value" in r and jsonschema is None:
            out.append(f"schema: /records/{i}: `value` is forbidden for a json location")
    return out


# ------------------------------------------------------------------ auto-index of the rules
def _review_state(review: dict, point):
    if not point:
        return None
    rec = review.get(point)
    return rec.get("status") if isinstance(rec, dict) else "pending"


def auto_rules(root: Path, review: dict) -> list:
    """Rules indexed from their own fields: [{id, engine, norm, edition, clause, page, verification, review_point, review, file, title}]."""
    out = []
    for path in sorted(root.glob(AEA_RULES)):
        if path.name.startswith("_"):
            continue
        rel = path.relative_to(root).as_posix()
        for r in load_json(path).get("reglas", []):
            src = r.get("fuente", {})
            uid = "rule:" + slug(f"{src.get('norma', '?')} {src.get('edicion', '')}")
            point = f"{uid}|{r['id']}"
            ver = src.get("verificacion")
            ver = ver if ver in ("text", "ocr", "visual", "from_memory", "unverified") else "text"
            out.append({"id": "aea90364.rule." + slug(r["id"]), "engine": "aea90364", "norm": src.get("norma"), "edition": src.get("edicion"), "clause": src.get("clausula"),
                        "page": {"printed": src.get("pagina_impresa"), "pdf": src.get("pagina_pdf")}, "verification": ver, "review_point": point,
                        "review": _review_state(review, point), "file": rel, "title": r.get("tema", r["id"])})
    for path in sorted(root.glob(LIGHTING_RULES)):
        data = load_json(path)
        rel = path.relative_to(root).as_posix()
        for r in data.get("rules", []):
            point = "lighting-rule:" + slug(data.get("norm")) + "|" + r["id"]
            out.append({"id": "lighting.rule." + slug(r["id"]), "engine": "lighting", "norm": r.get("norm", data.get("norm")), "edition": data.get("edition"), "clause": r.get("clause"),
                        "page": {"printed": r.get("page"), "pdf": None}, "verification": "unverified", "review_point": point,
                        "review": _review_state(review, point), "file": rel, "title": r.get("summary", r["id"])})
    return out


# ------------------------------------------------------------------ validation
class Register:
    def __init__(self, root: Path, schema: Path = None):
        self.root = Path(root)
        self.schema = Path(schema) if schema else self.root / SCHEMA
        self.errors, self.warnings = [], []
        self.files = []          # [(rel path, data)]
        self.records = []        # [(rel path, record)]
        self.auto = []
        self._docs = {}
        rv = self.root / REVIEW
        self.review = load_json(rv).get("points", {}) if rv.exists() else {}
        self.load()
        self.validate()
        self.auto = auto_rules(self.root, self.review)
        self.check_auto_ids()

    def err(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"{where}: {msg}")

    def load(self):
        for path in sorted((p for g in REGISTER_GLOBS for p in self.root.glob(g)), key=lambda p: p.parts[_src_index(p.parts) - 1:]):
            rel = path.relative_to(self.root).as_posix()
            try:
                data = load_json(path)
            except (ValueError, OSError) as e:
                self.err(rel, f"cannot read JSON: {e}")
                continue
            for m in schema_errors(data, self.schema):
                self.err(rel, m)
            if not isinstance(data, dict) or not isinstance(data.get("records"), list):
                continue
            self.files.append((rel, data))
            parts = path.parts
            pkg_dir = parts[_src_index(parts) - 1] if "src" in parts else None
            if pkg_dir and data.get("engine") != pkg_dir:
                self.err(rel, f"`engine` is {data.get('engine')!r} but the file is in {P.ENGINE_FOLDERS_REL.get(pkg_dir, pkg_dir)}")
            if data.get("topic") != path.stem:
                self.err(rel, f"`topic` is {data.get('topic')!r} but the file is called {path.name}")
            self.records += [(rel, r) for r in data["records"] if isinstance(r, dict)]

    def doc(self, rel: str):
        if rel not in self._docs:
            self._docs[rel] = load_json(self.root / rel)
        return self._docs[rel]

    def validate(self):
        seen, targets = {}, {}
        for rel, r in self.records:
            rid = r.get("id")
            where = f"{rel} [{rid}]"
            if rid in seen:
                self.err(where, f"duplicate id (also in {seen[rid]})")
            seen.setdefault(rid, rel)
            rp = r.get("review_point")
            if rp and not REVIEW_POINT.match(rp):
                self.err(where, f"review_point {rp!r} does not follow the backend format <unit>|<key>")
            if r.get("status") == "verified" and not r.get("verified_by"):
                self.err(where, "status verified without verified_by")
            loc = r.get("location")
            if not isinstance(loc, dict):
                continue
            key = (loc.get("type"), loc.get("file"), loc.get("pointer", loc.get("symbol")))
            if key[2] is not None:
                if key in targets:
                    self.err(where, f"same location as {targets[key]}")
                targets.setdefault(key, rid)
            f = loc.get("file")
            if not isinstance(f, str) or not (self.root / f).is_file():
                self.err(where, f"location file not found: {f}")
                continue
            if loc.get("type") == "json":
                self.check_json(where, loc)
            elif loc.get("type") == "code":
                self.check_code(where, r, loc)
        ids = set(seen)
        for rel, r in self.records:
            for issue in r.get("issues", []) if isinstance(r.get("issues"), list) else []:
                m = re.match(r"conflicts with ([a-z0-9_.-]+)", issue)
                if m and m.group(1) not in ids:
                    self.warn(f"{rel} [{r.get('id')}]", f"issue mentions unknown record id {m.group(1)}")

    def check_json(self, where, loc):
        try:
            ok, got = resolve_pointer(self.doc(loc["file"]), loc["pointer"])
        except (ValueError, OSError) as e:
            self.err(where, f"cannot read {loc['file']}: {e}")
            return
        if not ok:
            self.err(where, f"pointer {loc['pointer']!r} does not resolve in {loc['file']}: {got}")

    def check_code(self, where, r, loc):
        path = self.root / loc["file"]
        text = path.read_bytes().decode("utf-8-sig")
        total = len(text.splitlines())
        if loc["line"] > total:
            self.err(where, f"line {loc['line']} is beyond the end of {loc['file']} ({total} lines)")
        sym = loc.get("symbol")
        if not sym:
            return
        try:
            node = module_assignment(text, sym)
        except SyntaxError as e:
            self.err(where, f"cannot parse {loc['file']}: {e}")
            return
        if node is None:
            self.err(where, f"no module-level assignment of {sym} in {loc['file']}")
            return
        if node.lineno != loc["line"]:
            self.warn(where, f"{sym} is at line {node.lineno} of {loc['file']}, record says {loc['line']}")
        if "value" not in r:
            return
        try:
            actual = ast.literal_eval(node.value)
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            self.warn(where, f"{sym} is not a plain literal: value not compared")
            return
        if _plain(actual) != _plain(r["value"]):
            self.err(where, f"value differs from the code: {sym} = {json.dumps(_plain(actual), ensure_ascii=False)[:100]}")

    def check_auto_ids(self):
        taken = {r.get("id") for _, r in self.records}
        for a in self.auto:
            if a["id"] in taken:
                self.err(a["file"], f"auto-indexed rule id {a['id']} collides with a hand record")
            taken.add(a["id"])

    # ------------------------------------------------------------------ views
    def all_issues(self):
        return [(rel, r, i) for rel, r in self.records for i in (r.get("issues") or [])]

    def no_clause(self):
        hand = [(r["id"], r.get("norm"), "hand") for _, r in self.records if not r.get("clause")]
        auto = [(a["id"], a["norm"], "auto") for a in self.auto if not a["clause"]]
        return hand + auto


# ------------------------------------------------------------------ report
def _cell(x) -> str:
    return "-" if x in (None, "") else str(x).replace(PIPE, "\\|").replace("\n", " ")


def _page(p) -> str:
    if not isinstance(p, dict):
        return "-"
    parts = []
    if p.get("printed") not in (None, ""):
        parts.append(f"p. {p['printed']}")
    if p.get("pdf") is not None:
        parts.append(f"PDF {p['pdf']}")
    return " / ".join(parts) or "-"


def _where(r) -> str:
    loc = r.get("location", {})
    if loc.get("type") == "code":
        v = json.dumps(r.get("value"), ensure_ascii=False)
        return "`" + (v if len(v) <= 60 else v[:57] + "...") + "`"
    return f"`{loc.get('file', '?').split('/')[-1]}#{loc.get('pointer', '')}`"


def _review_cell(reg, r) -> str:
    st = _review_state(reg.review, r.get("review_point"))
    return f"{r.get('status')}" + (f" (revision: {st})" if st and st != "pending" else "")


def report(reg: Register) -> str:
    L = ["# Registro de normas", "",
         "Generado por `python harness/tools/build/norm_register.py --report`; no se edita a mano. Lista cada valor de norma con su cláusula, página y fuente, para que el dueño lo verifique contra la norma oficial. "
         "Solo el dueño cambia el estado (`pending` -> `verified`/`rejected`). Los datos viven en un solo lugar: los registros con ubicación JSON solo apuntan al archivo.", ""]
    recs = [r for _, r in reg.records]
    L += ["## Resumen", "", f"- Registros a mano: **{len(recs)}** en {len(reg.files)} archivos.", f"- Reglas indexadas automáticamente: **{len(reg.auto)}**.",
          f"- Sin cláusula: **{len(reg.no_clause())}**.", f"- Conflictos o duplicados señalados: **{sum(1 for _, _, i in reg.all_issues() if CONFLICT.match(i))}**.", ""]
    by_engine = defaultdict(Counter)
    for rel, r in reg.records:
        by_engine[rel.split("/")[1]][(r["provenance"], r["status"])] += 1
    L += ["### Registros a mano por motor, procedencia y estado", "", "| Motor | Procedencia | Estado | Registros |", "|---|---|---|---:|"]
    for eng in sorted(by_engine):
        for (prov, st), n in sorted(by_engine[eng].items()):
            L.append(f"| {eng} | {prov} | {st} | {n} |")
    if not recs:
        L.append("| - | - | - | 0 |")
    L += ["", "### Reglas indexadas por motor", "", "| Motor | Reglas | Con revisión aprobada |", "|---|---:|---:|"]
    ae = Counter(a["engine"] for a in reg.auto)
    ap = Counter(a["engine"] for a in reg.auto if a["review"] == "approved")
    for eng in sorted(ae):
        L.append(f"| {eng} | {ae[eng]} | {ap[eng]} |")
    L += [""]
    for rel, data in reg.files:
        L += [f"## {data['engine']} / {data['topic']}", "", f"Archivo: `{rel}` ({len(data['records'])} registros)", "",
              "| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in data["records"]:
            norm = " ".join(x for x in (r.get("norm"), f"({r['edition']})" if r.get("edition") else "") if x)
            L.append("| " + " | ".join([f"`{r['id']}`", _cell(norm), _cell(r.get("clause")), _page(r.get("page")), _where(r), _cell(r.get("unit")), r["provenance"], r["confidence"],
                                        _cell(_review_cell(reg, r)), _cell("; ".join(r.get("issues") or []))]) + " |")
        L.append("")
    L += ["## Sin cláusula", ""]
    nc = reg.no_clause()
    L += ([f"- `{i}` ({_cell(n)}; {k})" for i, n, k in sorted(nc, key=lambda t: t[0])] if nc else ["Ninguno."])
    L += ["", "## Conflictos", ""]
    cf = [(r["id"], i) for _, r, i in reg.all_issues() if CONFLICT.match(i)]
    L += ([f"- `{rid}`: {i}" for rid, i in sorted(cf)] if cf else ["Ninguno."])
    L += ["", "## Reglas indexadas automáticamente", "",
          "Salen de los campos propios de cada regla (id, norma, edición, cláusula, página). No tienen registro a mano.", ""]
    groups = defaultdict(list)
    for a in reg.auto:
        groups[(a["norm"], a["edition"])].append(a)
    for (norm, ed), items in sorted(groups.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        L += [f"### {_cell(norm)} ({_cell(ed)}): {len(items)} reglas", "", "| id | cláusula | página | verificación | revisión |", "|---|---|---|---|---|"]
        for a in sorted(items, key=lambda a: a["id"]):
            L.append(f"| `{a['id']}` | {_cell(a['clause'])} | {_page(a['page'])} | {a['verification']} | {_cell(a['review'])} |")
        L.append("")
    return "\n".join(L).rstrip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 on errors (with --report: also when the report is out of date)")
    ap.add_argument("--report", action="store_true", help="write harness/docs/NORM_REGISTER.md")
    ap.add_argument("--root", default=str(REPO), help="repository root (tests use a temp dir)")
    ap.add_argument("--schema", default=None, help="schema file (default: <root>/harness/schemas/norm-register.schema.json)")
    args = ap.parse_args(argv)
    root = Path(args.root)
    reg = Register(root, Path(args.schema) if args.schema else None)
    for w in reg.warnings:
        print("WARN ", w)
    for e in reg.errors:
        print("ERROR", e)
    print(f"norm register: {len(reg.records)} records in {len(reg.files)} files, {len(reg.auto)} auto-indexed rules, {len(reg.errors)} errors, {len(reg.warnings)} warnings")
    rc = 1 if (args.check and reg.errors) else 0
    if args.report:
        target = root / TARGET
        new = report(reg)
        if args.check:
            old = target.read_bytes().decode("utf-8").replace("\r\n", "\n") if target.exists() else ""
            if old != new:
                print(f"{TARGET} is out of date: run `python harness/tools/build/norm_register.py --report`")
                rc = 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(new, encoding="utf-8", newline="\n")
            print(f"wrote {TARGET}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
