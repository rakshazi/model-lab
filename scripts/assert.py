#!/usr/bin/env python3
"""Grade one lab run against the assertions in LAB/evals.json; writes RUNDIR/grading.json."""
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile

HELP = """Usage: assert.py RUNDIR [--eval ID] [--no-judge]

Grades the run's outputs against one eval of LAB/evals.json (LAB is three levels above
RUNDIR) and writes RUNDIR/grading.json in the Agent Skills shape:
{"assertion_results": [{"text", "passed", "evidence"}], "summary": {...}}.

evals.json follows the spec (skill_name, evals[].id, prompt, expected_output, assertions)
plus two lab keys: "outputs", files in RUNDIR/repo to grade (default ["AGENTS.md"]), and
"context", files from the fixture the judge reads as ground truth (e.g. ["Makefile"]).
An assertion is a string (graded by the judge model) or an object graded by script:
  {"text": "...", "grep": "literal"}    passes when an output contains the literal
  {"text": "...", "absent": "literal"}  passes when no output contains it
  {"text": "...", "regex": "pattern"}   passes when an output matches (Python re, multiline)
  {"text": "...", "cmd": "shell"}       passes on exit 0, run in RUNDIR/repo

Options:
  --eval ID   eval id to grade (default: the first eval)
  --no-judge  record judge assertions as failed with evidence "not judged"

Env:
  JUDGE  command that reads the judge prompt on stdin and prints the answer
         (default: claude --safe-mode -p --model haiku, run from a temp dir, where claude is
         CLAUDE_BIN or the first non-script claude on PATH)

Exit: 0 graded (any pass rate); 1 the judge answer could not be parsed; 2 bad invocation.

Example: python3 -I scripts/assert.py /tmp/x-lab/runs/v1/1"""

JUDGE_PROMPT = """You grade one output of an AI agent against assertions.
Require concrete evidence for a PASS: quote or point at the output. A heading with nothing
real under it is a FAIL. If the output does not show it, it is a FAIL.

Expected output, in the test author's words:
{expected}

Assertions, numbered:
{assertions}

Ground truth from the repository the agent worked in (may be empty), each between ##### markers:
{context}

The output files follow, each between ===== markers.
{outputs}

Answer with ONLY a JSON array, one object per assertion in the same order:
[{{"n": 1, "passed": true, "evidence": "<quote or pointer, under 200 chars>"}}]"""


def fail(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def claude_bin():
    """CLAUDE_BIN, else the first `claude` on PATH that is a binary: a wrapper script can carry a
    --system-prompt-file that --safe-mode keeps, and the judge would grade in that voice."""
    if os.environ.get("CLAUDE_BIN"):
        return os.environ["CLAUDE_BIN"]
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = os.path.join(d, "claude")
        if os.access(p, os.X_OK):
            with open(p, "rb") as f:
                if f.read(2) != b"#!":
                    return p
    return "claude"


def judge(expected, items, outputs, context):
    listing = "\n".join(f"{i}. {a}" for i, a in enumerate(items, 1))
    files = "\n".join(f"===== {name}\n{body[:60000]}\n=====" for name, body in outputs.items())
    truth = "\n".join(f"##### {name}\n{body[:60000]}\n#####" for name, body in context.items())
    prompt = JUDGE_PROMPT.format(expected=expected or "(none given)", assertions=listing,
                                 context=truth or "(none)", outputs=files)
    cmd = shlex.split(os.environ.get("JUDGE", f"{claude_bin()} --safe-mode -p --model haiku"))
    with tempfile.TemporaryDirectory() as cwd:
        res = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=cwd, timeout=600)
    match = re.search(r"\[.*\]", res.stdout, re.S)
    if res.returncode != 0 or not match:
        fail(f"judge gave no JSON array (exit {res.returncode}): {(res.stdout or res.stderr)[:300]}", 1)
    try:
        verdicts = {v["n"]: v for v in json.loads(match.group(0))}
    except (ValueError, KeyError, TypeError) as err:
        fail(f"judge answer is no verdict list: {err}", 1)
    return [
        {"text": a, "passed": bool(verdicts.get(i, {}).get("passed")),
         "evidence": str(verdicts.get(i, {}).get("evidence", "judge gave no verdict"))}
        for i, a in enumerate(items, 1)
    ]


def scripted(a, outputs, repo):
    blob = "\n".join(outputs.values())
    if "grep" in a:
        ok = a["grep"] in blob
        return ok, f"{'found' if ok else 'missing'}: {a['grep']}"
    if "absent" in a:
        ok = a["absent"] not in blob
        return ok, f"{'absent' if ok else 'present'}: {a['absent']}"
    if "regex" in a:
        m = re.search(a["regex"], blob, re.M)
        return bool(m), f"matched: {m.group(0)[:150]}" if m else f"no match: {a['regex']}"
    if "cmd" in a:
        r = subprocess.run(["bash", "-c", a["cmd"]], cwd=repo, capture_output=True, text=True, timeout=300)
        last = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
        return r.returncode == 0, f"exit {r.returncode}: {last[0][:150]}"
    fail(f"assertion object needs grep, absent, regex or cmd: {a}")


def main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(HELP)
        return
    if not args or not os.path.isdir(args[0]):
        fail("RUNDIR is required and must exist; see --help")
    run = os.path.abspath(args[0])
    lab = os.path.abspath(os.path.join(run, "..", "..", ".."))
    path = os.path.join(lab, "evals.json")
    if not os.path.isfile(path):
        fail(f"no {path}; write one (see --help)")
    try:
        evals = json.load(open(path))["evals"]
    except (ValueError, KeyError) as err:
        fail(f"{path} is no evals file: {err}")
    want = args[args.index("--eval") + 1] if "--eval" in args else None
    ev = next((e for e in evals if want is None or str(e.get("id")) == want), None)
    if not ev:
        fail(f"no eval with id {want} in {path}")

    repo = os.path.join(run, "repo")
    outputs = {}
    for name in ev.get("outputs", ["AGENTS.md"]):
        p = os.path.join(repo, name)
        outputs[name] = open(p, errors="replace").read() if os.path.isfile(p) else ""
    results, judged = [], []
    for a in ev.get("assertions", []):
        if not any(outputs.values()):
            # an absent-check on a file that was never written proves nothing
            results.append({"text": a if isinstance(a, str) else a["text"], "passed": False,
                            "evidence": "no output written"})
        elif isinstance(a, str):
            judged.append(a)
            results.append(None)
        else:
            ok, why = scripted(a, outputs, repo)
            results.append({"text": a["text"], "passed": ok, "evidence": why})
    if judged:
        if "--no-judge" in args:
            verdicts = [{"text": a, "passed": False, "evidence": "not judged"} for a in judged]
        else:
            base = os.path.join(lab, "base")
            context = {n: open(os.path.join(base, n), errors="replace").read()
                       for n in ev.get("context", []) if os.path.isfile(os.path.join(base, n))}
            verdicts = judge(ev.get("expected_output"), judged, outputs, context)
        it = iter(verdicts)
        results = [r if r is not None else next(it) for r in results]

    passed = sum(r["passed"] for r in results)
    total = len(results)
    grading = {
        "eval_id": ev.get("id"),
        "assertion_results": results,
        "summary": {"passed": passed, "failed": total - passed, "total": total,
                    "pass_rate": round(passed / total, 3) if total else 0.0},
    }
    with open(os.path.join(run, "grading.json"), "w") as fh:
        json.dump(grading, fh, indent=2)
    for r in results:
        print(f"{'PASS' if r['passed'] else 'FAIL'}  {r['text']}  [{r['evidence']}]")
    print(f"ASSERT {passed}/{total}")


if __name__ == "__main__":
    main()
