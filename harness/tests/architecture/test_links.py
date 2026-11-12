"""Every relative markdown link in harness/docs/ points to a file or folder that exists (code fences are ignored)."""
import re
import unittest
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parents[3]
DOCS = REPO / "harness" / "docs"
LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^\s*(```|~~~)")


def broken_links():
    out = []
    for md in sorted(DOCS.rglob("*.md")):
        in_fence = False
        for n, line in enumerate(md.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for target in LINK.findall(line):
                if re.match(r"^(https?:|mailto:|#|/)", target) or any(c in target for c in "<>") or "{{" in target:
                    continue
                path = unquote(target.split("#", 1)[0])
                if path and not (md.parent / path).exists():
                    out.append(f"{md.relative_to(REPO).as_posix()}:{n}: {target}")
    return out


class RelativeLinks(unittest.TestCase):
    def test_every_relative_link_resolves(self):
        self.assertEqual(broken_links(), [], "broken relative links in harness/docs")


if __name__ == "__main__":
    unittest.main()
