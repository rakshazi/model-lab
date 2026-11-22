#!/usr/bin/env python3
"""List places where a skill says the same thing twice, for a reader to judge."""
import re
import sys
from collections import defaultdict
from pathlib import Path

HELP = """Usage: dups.py [SKILL_DIR] [--words N]

Reads SKILL.md, AGENTS.md and every .md under references/ and prints one line per pair of
passages that share any of:
  phrase   a run of N or more identical words (default 8), outside code fences
  number   a measured value (48.8K, 26 of 29, 70.4%, 2x, 4h15m) that appears in both
  literal  a backticked string of four or more words
A passage is one bullet, table row or paragraph. Each line names both places, the kind of
pair (body+ref, ref+ref, same file, maintenance for AGENTS.md) and what they share, strongest first.

Not every pair is a defect: a one-line rule in SKILL.md whose receipt sits in a reference is
the intended shape. A pair is a duplicate when both sides carry the receipt, or when two
references each explain the same thing. Give the fact one home and point the other side at it.

Options:
  --words N  shortest shared word run reported as a phrase (default 8)

Exit: 0 printed (pairs or none); 2 bad invocation.

Example: python3 -I scripts/dups.py ~/skills/my-skill --words 10"""

NUMBER = re.compile(r"\b\d+(?:\.\d+)?(?:K|%|x\b| of \d+|/\d+|h\d+m)|\b\d+\.\d+\b")
LITERAL = re.compile(r"`([^`\n]+)`")


def passages(path, root):
    fenced, n0, buf = False, 0, []
    lines = path.read_text().splitlines() + [""]
    for n, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        start = re.match(r"\s*(?:[-*] |\d+\. |\|)", line)
        if buf and (not line.strip() or start or line.startswith("#")):
            yield f"{path.relative_to(root)}:{n0}", " ".join(buf)
            buf = []
        if fenced or not line.strip() or line.startswith("#") or re.fullmatch(r"\|[-| :]+\|", line.strip()):
            continue
        if not buf:
            n0 = n
        buf.append(line.strip())


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(HELP)
        return 0
    words = 8
    if "--words" in argv:
        i = argv.index("--words")
        if i + 1 >= len(argv) or not argv[i + 1].isdigit() or int(argv[i + 1]) < 3:
            print("error: --words needs a number of 3 or more; see --help", file=sys.stderr)
            return 2
        words = int(argv[i + 1])
        del argv[i : i + 2]
    if len(argv) > 1:
        print("error: one SKILL_DIR at most; see --help", file=sys.stderr)
        return 2
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    if not (root / "SKILL.md").is_file():
        print(f"error: no SKILL.md in {root}; pass the skill directory", file=sys.stderr)
        return 2
    files = [root / "SKILL.md", root / "AGENTS.md", *sorted((root / "references").rglob("*.md"))]
    units = [u for f in files if f.is_file() for u in passages(f, root)]

    seen = defaultdict(set)  # shared thing -> passages holding it
    grams = defaultdict(set)
    for where, text in units:
        for m in NUMBER.findall(text):
            seen[("number", m)].add(where)
        for m in LITERAL.findall(text):
            if len(m.split()) >= 4:
                seen[("literal", m)].add(where)
        toks = [t.strip(".,;:") for t in re.findall(r"[\w'.%/-]*\w[\w'.%/-]*", re.sub(r"[`*\"]", "", text).lower())]
        for i in range(len(toks) - words + 1):
            grams[" ".join(toks[i : i + words])].add(where)
    pairs = defaultdict(lambda: defaultdict(list))
    for (kind, what), places in seen.items():
        for a in sorted(places):
            for b in sorted(places):
                if a < b:
                    pairs[(a, b)][kind].append(what)
    for gram, places in grams.items():
        for a in sorted(places):
            for b in sorted(places):
                if a < b:
                    pairs[(a, b)]["phrase"].append(gram)

    def kind(a, b):
        fa, fb = a.rsplit(":", 1)[0], b.rsplit(":", 1)[0]
        if fa == fb:
            return "same file"
        return "maintenance" if "AGENTS.md" in (fa, fb) else "body+ref" if "SKILL.md" in (fa, fb) else "ref+ref"

    out = []
    for (a, b), shared in pairs.items():
        score = 3 * bool(shared["phrase"]) + len(shared["number"]) + len(shared["literal"])
        if score < 2 and not shared["phrase"]:
            continue  # one shared number alone is usually coincidence
        bits = []
        if shared["phrase"]:
            bits.append(f'phrase "{shared["phrase"][0]} ..." ({len(shared["phrase"]) + words - 1} words overlap)')
        for k in ("number", "literal"):
            if shared[k]:
                bits.append(f"{k} " + ", ".join(sorted(set(shared[k]))[:6]))
        out.append((score + len(shared["phrase"]), f"{a} <-> {b} [{kind(a, b)}] " + "; ".join(bits)))
    for _, line in sorted(out, reverse=True):
        print(line)
    print(f"{len(out)} pairs in {len(units)} passages of {len([f for f in files if f.is_file()])} files", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
