#!/usr/bin/env python3
"""Shuffle scripts/claude-code/run.sh runs into an anonymous bundle for a judge, keeping the key outside it."""
import json
import os
import random
import re
import shutil
import sys

HELP = """Usage: blind.py LAB OUT VARIANT/N [VARIANT/N...] [--redact REGEX]... [--seed N]

Copies each run's final reply (result.json "result") to OUT/R<i>/reply.md and its
diff.patch, post.txt and check.txt next to it, in shuffled order. Every --redact REGEX
(a tool or file name only one variant would mention) becomes "[redacted]". The key goes
to LAB/blind-key-<seed>.json, outside OUT: point the judge at OUT and nothing else.

Re-grade an unchanged variant in a second bundle with a new seed and a fresh judge: the
score moves between two judges are the noise floor for every delta you report.
Exit: 0 written; 2 bad invocation or a missing run."""


def main(argv):
    if len(argv) < 3 or argv[0] in ("-h", "--help"):
        print(HELP)
        return 0 if argv and argv[0] in ("-h", "--help") else 2
    redact, seed = [], 1
    while "--redact" in argv:
        i = argv.index("--redact"); redact.append(argv[i + 1]); del argv[i:i + 2]
    if "--seed" in argv:
        i = argv.index("--seed"); seed = int(argv[i + 1]); del argv[i:i + 2]
    lab, out, runs = argv[0], argv[1], argv[2:]
    for r in runs:
        if not os.path.isfile(f"{lab}/runs/{r}/result.json"):
            print(f"error: no {lab}/runs/{r}/result.json; name runs as VARIANT/N", file=sys.stderr)
            return 2
    if os.path.abspath(out).startswith(os.path.abspath(lab) + "/runs"):
        print("error: OUT inside LAB/runs would sit next to the labelled runs; pick another dir", file=sys.stderr)
        return 2
    random.Random(seed).shuffle(runs)
    shutil.rmtree(out, ignore_errors=True)
    key = {}
    for i, r in enumerate(runs, 1):
        lab_id, d = f"R{i}", f"{out}/R{i}"
        os.makedirs(d)
        key[lab_id] = r
        files = {"reply.md": json.load(open(f"{lab}/runs/{r}/result.json")).get("result", "")}
        status = open(f"{lab}/runs/{r}/status.txt").read() if os.path.isfile(f"{lab}/runs/{r}/status.txt") else ""
        for f, key_ in (("diff.patch", None), ("post.txt", "post_exit"), ("check.txt", "check_exit")):
            p = f"{lab}/runs/{r}/{f}"
            if os.path.isfile(p):
                body = open(p, encoding="utf-8", errors="replace").read()
                m = re.search(rf"{key_}=(\d+)", status) if key_ else None
                # a passing build prints nothing; the exit code is the evidence
                files[f] = (f"exit {m.group(1)}\n" if m else "") + body
        for f, body in files.items():
            for rx in redact:
                body = re.sub(rx, "[redacted]", body)
            open(f"{d}/{f}", "w").write(body)
    json.dump(key, open(f"{lab}/blind-key-{seed}.json", "w"), indent=1)
    print(f"{len(runs)} runs in {out}; key in {lab}/blind-key-{seed}.json")
    return 0


sys.exit(main(sys.argv[1:]))
