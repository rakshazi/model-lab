#!/usr/bin/env python3
"""Summarise one omp session JSONL for a model-lab run."""
import json
import sys
from collections import Counter
from datetime import datetime

HELP = """Usage: trace.py SESSION.jsonl [--after TEXT] [--calls] [--json] [--system [--has TEXT]]

Prints the span, tool-call counts, token totals, output-cap hits (stopReason=length:
an idle model in the tool log) and the three longest gaps.

Options:
  --system      Pi sessions only: print what the model received instead of the summary,
                as one line per system prompt section (name, chars, opening text) and
                the declared tool names
  --has TEXT    with --system: name every section and tool schema that contains TEXT,
                and exit 1 when none does
  --after TEXT  seconds from the first tool result containing TEXT to the end (a done
                signal, say); in text mode also prints every step after it
  --calls       print every thinking line and tool call (text mode)
  --json        one JSON object on stdout: span_s, after_s, tools, tool_calls,
                output_caps, input_tokens, output_tokens, total_tokens, gaps

Exit: 0 summarised; 2 bad invocation or unreadable file.

Example: python3 -I scripts/trace.py ~/.omp/lab/sessions/v1/1/*.jsonl --after 'the work is done'"""


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fail(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def system(events, has):
    """Print the system prompt sections and tool names a Pi session recorded."""
    found = []
    for m in (e.get("message") or {} for e in events):
        if m.get("role") != "system":
            continue
        parts = dict(m.get("sections") or {})
        parts.update({f"tool:{t['name']}": json.dumps(t) for t in m.get("toolsAdded") or []})
        for name, text in parts.items():
            if has is None and not name.startswith("tool:"):
                print(f"{name:10} {len(text):6}  {' '.join(text.split())[:90]}")
            elif has is not None and has in text:
                found.append(name)
        if has is None:
            print("tools     ", " ".join(n[5:] for n in parts if n.startswith("tool:")) or "(none)")
    if has is not None:
        print(f"{has!r} in: {' '.join(found) or 'nothing the session recorded'}")
        sys.exit(0 if found else 1)


def main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(HELP)
        return
    if not args or args[0].startswith("-"):
        fail("SESSION.jsonl is the first argument; see --help")
    path, after = args[0], None
    calls, as_json = "--calls" in args, "--json" in args
    if "--after" in args:
        i = args.index("--after") + 1
        if i >= len(args):
            fail("--after needs TEXT")
        after = args[i]
    try:
        events = [json.loads(line) for line in open(path)]
    except (OSError, ValueError) as err:
        fail(f"cannot read {path} as a session JSONL: {err}")
    if "--system" in args:
        i = args.index("--has") + 1 if "--has" in args else 0
        if i >= len(args):
            fail("--has needs TEXT")
        return system(events, args[i] if i else None)

    tools, caps, gaps, steps = Counter(), [], [], []
    tok_in = tok_out = 0
    after_at = prev = None
    for e in events:
        t = e.get("timestamp")
        m = e.get("message") or {}
        if t and prev:
            gaps.append(((ts(t) - ts(prev)).total_seconds(), prev))
        prev = t or prev
        if m.get("role") == "toolResult" and after and not after_at and after in json.dumps(m):
            after_at = t
            steps.append(f"--- {after!r} at {t}")
            continue
        if m.get("role") != "assistant":
            continue
        usage = m.get("usage") or {}
        tok_in += usage.get("input", 0) + usage.get("cacheRead", 0)
        tok_out += usage.get("output", 0)
        if m.get("stopReason") == "length":
            caps.append({"at": t, "output_tokens": usage.get("output")})
        for c in m.get("content", []):
            if c.get("type") == "toolCall":
                tools[c["name"]] += 1
            if calls or after_at:
                if c.get("type") == "thinking":
                    steps.append(f"T {t[11:19]} {c['thinking'][:200]}".replace("\n", " "))
                if c.get("type") == "toolCall":
                    steps.append(f"C {t[11:19]} {c['name']} {json.dumps(c['arguments'])[:160]}")

    first = next((e["timestamp"] for e in events if e.get("timestamp")), None)
    if not first:
        fail(f"{path} has no timestamped events")
    stats = {
        "span_s": round((ts(prev) - ts(first)).total_seconds()),
        "after_s": round((ts(prev) - ts(after_at)).total_seconds()) if after_at else None,
        "tools": dict(tools.most_common()),
        "tool_calls": sum(tools.values()),
        "output_caps": caps,
        "input_tokens": tok_in,
        "output_tokens": tok_out,
        "total_tokens": tok_in + tok_out,
        "gaps": [{"s": round(s), "after": at} for s, at in sorted(gaps, reverse=True)[:3]],
    }
    if as_json:
        print(json.dumps(stats))
        return
    print("\n".join(steps)) if steps else None
    print(f"span {first} -> {prev}  ({stats['span_s']}s)")
    if after_at:
        print(f"after signal: {stats['after_s']}s")
    print("tools", stats["tools"])
    print(f"tokens in {tok_in} out {tok_out}")
    for cap in caps:
        print(f"OUTPUT CAP at {cap['at']}: {cap['output_tokens']} tokens, stopReason=length")
    for g in stats["gaps"]:
        print(f"gap {g['s']}s after {g['after']}")


if __name__ == "__main__":
    main()
