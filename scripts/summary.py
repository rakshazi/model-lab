#!/usr/bin/env python3
"""Tabulate model-lab runs per variant and write the spec-shaped benchmark.json."""
import glob
import json
import os
import re
import statistics
import subprocess
import sys

HELP = """Usage: summary.py LAB VARIANT [VARIANT...] [--signal TEXT] [--outputs "A B"]

One row per run (exit, wall, assertion pass rate, literal score, tokens, tool calls,
output caps, seconds after the done signal, repo files changed besides the outputs),
then mean and stddev per variant. Writes LAB/runs/<VARIANT>/benchmark.json for each
variant; with two or more, the first is the baseline and every later one gets a "delta".

Reads per run: result.txt, grading.json (scripts/assert.py), grade.txt (scripts/grade.sh),
status.txt, and the session through scripts/trace.py: the path in session.txt (scripts/pi/run.sh
writes it), else ~/.omp/lab/sessions/<VARIANT>/<N>/.

Options:
  --signal TEXT  tool-result text that means "done", for the after-signal column
  --outputs LIST deliverables left out of the changed column (default "AGENTS.md")

Exit: 0 printed; 2 bad invocation or a variant with no runs.

Example: python3 -I scripts/summary.py /tmp/x-lab noskill v1 --signal 'the work is done'"""

TRACE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trace.py")


def fail(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def read(path):
    return open(path, errors="replace").read() if os.path.isfile(path) else ""


def run_row(rundir, variant, n, signal, outputs):
    res = read(os.path.join(rundir, "result.txt"))
    m = re.search(r"exit=(\d+) wall=(\d+)s", res)
    row = {"run": n, "exit": int(m.group(1)) if m else None, "wall_s": int(m.group(2)) if m else None}
    g = os.path.join(rundir, "grading.json")
    row["pass_rate"] = json.load(open(g))["summary"]["pass_rate"] if os.path.isfile(g) else None
    lit = re.search(r"SCORE hits=(\d+)/(\d+)", read(os.path.join(rundir, "grade.txt")))
    row["literals"] = f"{lit.group(1)}/{lit.group(2)}" if lit else "-"
    status = [l[3:] for l in read(os.path.join(rundir, "status.txt")).splitlines() if l.strip()]
    row["changed"] = [p for p in status if p not in outputs]
    sess = read(os.path.join(rundir, "session.txt")).split("\n")[:1]
    sess = [s for s in sess if s] or glob.glob(os.path.expanduser(f"~/.omp/lab/sessions/{variant}/{n}/*.jsonl"))
    if sess:
        cmd = [sys.executable, "-I", TRACE, sess[0], "--json"] + (["--after", signal] if signal else [])
        out = subprocess.run(cmd, capture_output=True, text=True)
        t = json.loads(out.stdout) if out.returncode == 0 else {}
        row.update(tokens=t.get("total_tokens"), calls=t.get("tool_calls"),
                   caps=len(t.get("output_caps", [])), after_s=t.get("after_s"))
    return row


def stat(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return {"mean": round(statistics.mean(vals), 3), "stddev": round(statistics.pstdev(vals), 3)}


def main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(HELP)
        return
    signal, outputs = None, ["AGENTS.md"]
    if "--outputs" in args:
        i = args.index("--outputs")
        if i + 1 >= len(args):
            fail("--outputs needs a list")
        outputs = args[i + 1].split()
        del args[i:i + 2]
    if "--signal" in args:
        i = args.index("--signal")
        if i + 1 >= len(args):
            fail("--signal needs TEXT")
        signal = args[i + 1]
        del args[i:i + 2]
    if len(args) < 2 or not os.path.isdir(os.path.join(args[0], "runs")):
        fail("needs LAB (with runs/) and at least one VARIANT; see --help")
    lab, variants = args[0], args[1:]

    cols = ["run", "exit", "wall_s", "pass_rate", "literals", "tokens", "calls", "caps", "after_s", "changed"]
    benches = {}
    for v in variants:
        dirs = sorted(glob.glob(os.path.join(lab, "runs", v, "[0-9]*")), key=lambda p: int(os.path.basename(p)))
        if not dirs:
            fail(f"no runs in {os.path.join(lab, 'runs', v)}")
        rows = [run_row(d, v, os.path.basename(d), signal, outputs) for d in dirs]
        print(f"\n## {v}\n")
        print("| " + " | ".join(cols) + " |")
        print("|" + "---|" * len(cols))
        for r in rows:
            cells = [", ".join(r[c]) if isinstance(r.get(c), list) else r.get(c) for c in cols]
            print("| " + " | ".join("-" if c in (None, "") else str(c) for c in cells) + " |")
        bench = {"pass_rate": stat([r["pass_rate"] for r in rows]),
                 "time_seconds": stat([r["wall_s"] for r in rows]),
                 "tokens": stat([r.get("tokens") for r in rows]),
                 "runs": len(rows)}
        benches[v] = bench
        print(f"\nmean pass_rate {bench['pass_rate']}  time {bench['time_seconds']}  tokens {bench['tokens']}")

    base = variants[0]
    for v in variants:
        out = {"run_summary": {v: benches[v]}}
        if v != base:
            out["run_summary"][base] = benches[base]
            out["run_summary"]["delta"] = {
                k: round(benches[v][k]["mean"] - benches[base][k]["mean"], 3)
                for k in ("pass_rate", "time_seconds", "tokens") if benches[v][k] and benches[base][k]
            }
            print(f"delta {v} vs {base}: {out['run_summary']['delta']}")
        with open(os.path.join(lab, "runs", v, "benchmark.json"), "w") as fh:
            json.dump(out, fh, indent=2)


if __name__ == "__main__":
    main()
