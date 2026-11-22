#!/usr/bin/env python3
"""Tabulate scripts/claude-code/run.sh runs per variant from result.json, status.txt and the transcript."""
import collections
import glob
import json
import os
import re
import statistics
import sys

HELP = """Usage: summary.py LAB VARIANT [VARIANT...] [--count REGEX] [--seen REGEX]

One row per run: exit, wall, turns, USD, tool calls by name, permission denials,
post/check exits, and with --count the Bash calls whose command matches REGEX plus how
many of them returned output matching --seen (default: anything but a denial).
Then the mean per variant.

A denial is a harness bug until proven otherwise: the model spends turns on it and the
run stops measuring the skill. Fix the allow list and rerun before reading any score.

Transcripts repeat each tool_use across streamed lines, so calls are counted by id.
Exit: 0 printed; 2 bad invocation or a variant with no runs."""

DENIED = re.compile(r"requires approval|permission to use|was denied|not allowed", re.I)


def blocks(path):
    try:
        lines = open(path, encoding="utf-8")
    except OSError:
        return
    for line in lines:
        try:
            content = (json.loads(line).get("message") or {}).get("content")
        except ValueError:
            continue
        if isinstance(content, list):
            yield from (b for b in content if isinstance(b, dict))


def text(content):
    return content if isinstance(content, str) else " ".join(x.get("text", "") for x in content or [])


def trace(path, count, seen):
    calls, results, tools = {}, {}, collections.Counter()
    for b in blocks(path):
        if b.get("type") == "tool_use" and b["id"] not in calls:
            calls[b["id"]] = (b["name"], str((b.get("input") or {}).get("command", "")))
            tools[b["name"]] += 1
        elif b.get("type") == "tool_result" and b.get("tool_use_id") not in results:
            results[b["tool_use_id"]] = text(b.get("content"))
    denied = sum(1 for out in results.values() if DENIED.search(out))
    hits = [i for i, (n, cmd) in calls.items() if n == "Bash" and count and re.search(count, cmd)]
    ok = sum(1 for i in hits if not DENIED.search(results.get(i, "")) and
             (re.search(seen, results.get(i, "")) if seen else True))
    return tools, denied, len(hits), ok


def main(argv):
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print(HELP)
        return 0 if argv and argv[0] in ("-h", "--help") else 2
    count = seen = None
    if "--count" in argv:
        i = argv.index("--count"); count = argv[i + 1]; del argv[i:i + 2]
    if "--seen" in argv:
        i = argv.index("--seen"); seen = argv[i + 1]; del argv[i:i + 2]
    lab, variants = argv[0], argv[1:]
    for v in variants:
        runs = sorted(glob.glob(f"{lab}/runs/{v}/*/status.txt"))
        if not runs:
            print(f"error: no runs in {lab}/runs/{v}; run scripts/claude-code/run.sh first", file=sys.stderr)
            return 2
        print(f"## {v}\n| run | exit | wall | turns | usd | tools | denied | post | check |"
              + (" count | seen |" if count else "") + "\n|---|---|---|---|---|---|---|---|---|" + ("---|---|" if count else ""))
        agg = collections.defaultdict(list)
        for st in runs:
            d = os.path.dirname(st)
            s = open(st).read()
            g = lambda k: (re.search(rf"{k}=(\S+)", s) or [None, "-"])[1]
            try:
                r = json.load(open(f"{d}/result.json"))
            except (OSError, ValueError):
                r = {}
            tools, denied, n, ok = trace(g("transcript"), count, seen)
            wall = int(g("wall").rstrip("s")) if g("wall") != "-" else 0
            usd = r.get("total_cost_usd", 0) or 0
            for k, val in (("wall", wall), ("turns", r.get("num_turns", 0) or 0), ("usd", usd), ("denied", denied)):
                agg[k].append(val)
            tl = " ".join(f"{k}:{c}" for k, c in tools.most_common())
            print(f"| {os.path.basename(d)} | {g('exit')} | {wall}s | {r.get('num_turns', '-')} | {usd:.2f} | {tl} | "
                  f"{denied} | {g('post_exit')} | {g('check_exit')} |" + (f" {n} | {ok} |" if count else ""))
        print("mean: " + ", ".join(f"{k} {statistics.mean(x):.2f}" for k, x in agg.items()) + "\n")
    return 0


sys.exit(main(sys.argv[1:]))
