#!/usr/bin/env python3
"""Maintenance lint: body budget, link targets, read-when triggers, script and asset coverage, leaks.

usage: lint.py [SKILL_DIR] [--stats]
exit 0 clean, 1 findings, 2 bad input. One finding per line.
"""
import re
import sys
from pathlib import Path

BODY_MAX = 19800  # bytes; the spec budget is 5000 tokens, about 4 bytes per token on this body
LINK = re.compile(r"\]\(([^)#\s]+)(?:#([^)\s]+))?\)")
# generic kinds only; private names go one regex per line into the gitignored evals/leaks.local
LEAK = [r"/home/(?!agent\b)\w", r"this box", r"127\.0\.0\.1", r"localhost:\d"]


def slug(heading):
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading.strip().lower()))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--help" in sys.argv or len(args) > 1:
        print(__doc__.strip())
        return 0 if "--help" in sys.argv else 2
    root = Path(args[0]) if args else Path(__file__).resolve().parent.parent
    skill = root / "SKILL.md"
    if not skill.is_file():
        print(f"error: no SKILL.md in {root}")
        return 2
    refs = sorted((root / "references").rglob("*.md"))
    text = {p: p.read_text() for p in [skill, *refs]}
    out = []

    body = text[skill].split("---", 2)[2]
    size = len(body.encode())
    if size > BODY_MAX:
        out.append(f"SKILL.md body is {size} bytes, budget {BODY_MAX}: move receipts to their reference")

    for p in refs:
        if f"]({p.relative_to(root)}" not in text[skill]:
            out.append(f"{p.relative_to(root)} is never linked from SKILL.md, so nothing loads it")

    for p, t in text.items():
        name = p.relative_to(root)
        for n, line in enumerate(t.splitlines(), 1):
            for path, anchor in LINK.findall(line):
                if "://" in path:
                    continue
                target = root / path
                if not target.is_file():
                    out.append(f"{name}:{n} links {path}, which does not exist")
                elif anchor and anchor not in {slug(h) for h in re.findall(r"^#+ (.+)$", target.read_text(), re.M)}:
                    out.append(f"{name}:{n} links {path}#{anchor}: no such heading")
                if p == skill and path.startswith("references/"):
                    cells = [c for c in line.split("|") if c.strip()]
                    row = line.startswith("|") and len(cells) >= 2
                    if not row and not re.search(r"\b(when|before)\b", line, re.I):
                        out.append(f"SKILL.md:{n} links {path} with no read-when trigger on the line")

    # inside a reference a pointer is `references/x.md`, "Section" (read when ...), from the skill root
    for p in refs:
        for n, line in enumerate(text[p].splitlines(), 1):
            for path, head in re.findall(r'`(references/[\w./-]+\.md)`(?:, "([^"]+)")?', line):
                where = f"{p.relative_to(root)}:{n}"
                target = root / path
                if not target.is_file():
                    out.append(f"{where} points at {path}, which does not exist")
                elif head and not re.search(rf"^#+ {re.escape(head)}$", target.read_text(), re.M):
                    out.append(f'{where} points at "{head}" in {path}: no such heading')
                if not re.search(r"\b(when|before)\b", line[line.index(path):], re.I):
                    out.append(f"{where} points at {path} with no read-when trigger after it")

    # a path with a prefix (~/.pi/.../scripts/x.sh, $SNAP/scripts/x) belongs to another skill
    docs = "\n".join(text.values())
    for rel in sorted(set(re.findall(r"(?<![\w/~$.-])((?:scripts|assets)/[\w./-]+\.\w+)", docs))):
        if not (root / rel).is_file():
            out.append(f"{rel} is named in the docs and does not exist")
    files = [f for d in ("scripts", "assets") for f in sorted((root / d).rglob("*")) if f.is_file()]
    for f in files:
        rel = str(f.relative_to(root))
        if rel not in text[skill] and f"{f.parent.relative_to(root)}/`" not in text[skill]:
            out.append(f"{rel} is never named in SKILL.md, so no agent knows it exists")
        if f.suffix in (".sh", ".py") and "--help" not in f.read_text():
            out.append(f"{rel} has no --help branch")

    local = root / "evals" / "leaks.local"
    extra = [l.strip() for l in local.read_text().splitlines() if l.strip() and not l.startswith("#")] if local.is_file() else []
    leak = re.compile("|".join(LEAK + extra), re.I)
    scanned = [root / "AGENTS.md", root / "README.md", *text, *files, *sorted((root / "evals").glob("*.json")), Path(__file__)]
    for f in scanned:
        if not f.is_file():
            continue
        for n, line in enumerate(f.read_text().splitlines(), 1):
            m = None if f == Path(__file__) and line.startswith("LEAK = ") else leak.search(line)
            if m:
                out.append(f"{f.relative_to(root)}:{n} leaks a machine or employer detail: {m.group(0)!r}")

    if "--stats" in sys.argv:
        total = sum(len(t.encode()) for t in text.values())
        print(f"body {size} B of {BODY_MAX}, references {total - len(text[skill].encode())} B in {len(refs)} files")
    print("\n".join(out), end="\n" if out else "")
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main())
