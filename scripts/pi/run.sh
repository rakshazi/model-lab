#!/usr/bin/env bash
# Usage: SKILL=<name> [LAB=<dir>] run.sh VARIANT N MODEL
# One Pi print-mode run of a skill in the netless sandbox, on a fresh clone of $LAB/base.
# The sandbox is github.com/rakshazi/IISD-sandbox set up for Pi at ~/.pi/docker.
# MODEL is the id your Pi models.json gives the model, e.g. llama-swap/qwen3.5-4b.
#
# Env:
#   SKILL      skill dir name under ~/.pi/agent/skills (required)
#   LAB        lab dir holding base/ (default /tmp/$SKILL-lab)
#   MAXTIME    wall limit as 90s, 20m or 2h (default 20m); Pi has no --max-time, so the watchdog
#              kills the container from the host and result.txt says timeout=1
#   SYSPROMPT  replaces Pi's preamble section only; tools, rules, docs, skills and cwd still arrive
#   APPEND=1   keeps ~/.pi/agent/APPEND_SYSTEM.md; by default a blank --append-system-prompt replaces it
#   CONTEXT=1  keeps AGENTS.md and CLAUDE.md discovery; by default -nc drops it
#   TOOLS      pi --tools allowlist (default read,bash,edit,write, which is Pi's own default set)
#   EXT        extensions to load, as paths under ~/.pi/agent, space-separated; by default none (-ne)
#   THINKING   pi --thinking level (default: whatever settings.json says)
#   ARGS       user text after /skill:NAME (the whole prompt under NOSKILL=1)
#   NOSKILL=1  baseline without the skill: the prompt is ARGS alone; check.sh still gets the snapshot
#   PIFLAGS    extra pi flags, word-split
#   COLLECT    files copied out of the run's repo, e.g. "AGENTS.md"
#   SKILLSNAP  reuse another variant's snapshot; SKILLSRC overrides the skill source dir
#
# After the run, when present: $LAB/check.sh RUN SNAP, $LAB/grade.sh RUN SESSDIR,
# and scripts/assert.py RUN when $LAB/evals.json exists.
# Out: $LAB/runs/VARIANT/N/{repo,prompt.txt,session.log,session.txt,result.txt,status.txt,trace.json,
#      timing.json,COLLECT files,check.txt,grade.txt,grading.json}
# Sessions: ~/.pi/lab/sessions/VARIANT/N (under ~/.pi because the container mounts it).
# Exit: 0 after any run (the run's own exit is in result.txt); 2 on bad invocation.
#
# Example: SKILL=my-skill ARGS='add a --json flag to the list command' TOOLS=read,bash,edit,write,Agent \
#   EXT='npm/node_modules/@tintinweb/pi-subagents' \
#   scripts/pi/run.sh v1 1 llama-swap/qwen3.5-4b
set -u
case ${1:-} in -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 0 ;; esac
[[ -n ${SKILL:-} && $# -ge 3 ]] || { echo "error: needs SKILL=<name> and VARIANT N MODEL; see --help" >&2; exit 2; }
LAB=${LAB:-/tmp/$SKILL-lab}
[[ -d $LAB/base ]] || { echo "error: no fixture at $LAB/base; build it with scripts/seal.sh" >&2; exit 2; }
VARIANT=$1; N=$2; MODEL=$3
[[ -z ${NOSKILL:-} || -n ${ARGS:-} ]] || { echo "error: NOSKILL=1 needs ARGS, the task as a user would type it" >&2; exit 2; }
SRC=${SKILLSRC:-$HOME/.pi/agent/skills/$SKILL}
[[ -f $SRC/SKILL.md ]] || { echo "error: no SKILL.md in $SRC; set SKILL or SKILLSRC" >&2; exit 2; }
MAXTIME=${MAXTIME:-20m}
case $MAXTIME in
  *s) secs=${MAXTIME%s} ;; *m) secs=$(( ${MAXTIME%m} * 60 )) ;; *h) secs=$(( ${MAXTIME%h} * 3600 )) ;;
  *) echo "error: MAXTIME=$MAXTIME is not 90s, 20m or 2h" >&2; exit 2 ;;
esac
# the snapshot keeps the skill's own dir name, because Pi wants name: to match the parent dir
SNAP=$HOME/.pi/lab/skills/${SKILLSNAP:-$VARIANT}/$SKILL
[[ -d $SNAP ]] || { mkdir -p "$SNAP"; cp -r "$SRC/." "$SNAP/"; rm -rf "$SNAP/.git"; }
CSNAP=/home/agent/.pi/lab/skills/${SKILLSNAP:-$VARIANT}/$SKILL
HSESS=$HOME/.pi/lab/sessions/$VARIANT/$N
RUN=$LAB/runs/$VARIANT/$N
rm -rf "$RUN" "$HSESS"; mkdir -p "$RUN"
git clone -q "$LAB/base" "$RUN/repo" && git -C "$RUN/repo" remote remove origin

# Pi expands /skill:NAME in print mode itself, so the prompt is what a user types
PROMPT="/skill:$SKILL${ARGS:+ $ARGS}"
[[ -n ${NOSKILL:-} ]] && PROMPT=$ARGS
printf '%s\n' "$PROMPT" > "$RUN/prompt.txt"

cmd=(just -f "$HOME/.pi/docker/justfile" run netless --model "$MODEL" -p "$PROMPT" --offline -na -ns -ne
  --tools "${TOOLS:-read,bash,edit,write}" --session-dir "/home/agent/.pi/lab/sessions/$VARIANT/$N")
[[ -z ${NOSKILL:-} ]] && cmd+=(--skill "$CSNAP")
for e in ${EXT:-}; do cmd+=(-e "/home/agent/.pi/agent/$e"); done
[[ -n ${SYSPROMPT:-} ]] && cmd+=(--system-prompt "$SYSPROMPT") && printf '%s\n' "$SYSPROMPT" > "$RUN/sysprompt.txt"
# an explicit append replaces the discovered APPEND_SYSTEM.md (a persona, house rules)
[[ -z ${APPEND:-} ]] && cmd+=(--append-system-prompt " ")
[[ -z ${CONTEXT:-} ]] && cmd+=(-nc)
[[ -n ${THINKING:-} ]] && cmd+=(--thinking "$THINKING")
# shellcheck disable=SC2206
[[ -n ${PIFLAGS:-} ]] && cmd+=($PIFLAGS)
printf -v cmdstr '%q ' "${cmd[@]}"

# the sandbox mounts the cwd at this path, which makes it the handle for finding the container
mount=/home/agent/workspace/$(realpath -L "$RUN/repo" | tr / -)
watchdog() {
  sleep "$secs" & local sp=$!
  trap 'kill $sp 2>/dev/null; exit 0' TERM
  wait $sp
  echo 1 > "$RUN/timeout.txt"
  docker ps -q --filter "volume=$mount" | xargs -r docker kill >/dev/null 2>&1
}

t0=$(date +%s)
# the netless flock is released a beat after the previous container exits
sleep 8
watchdog & wd=$!
( cd "$RUN/repo" && script -qefc "$cmdstr" "$RUN/session.log" >/dev/null 2>&1 )
rc=$?
kill "$wd" 2>/dev/null
wall=$(( $(date +%s) - t0 ))
echo "exit=$rc wall=${wall}s timeout=$([[ -f $RUN/timeout.txt ]] && echo 1 || echo 0)" > "$RUN/result.txt"

for f in ${COLLECT:-}; do [[ -f $RUN/repo/$f ]] && cp "$RUN/repo/$f" "$RUN/"; done
( cd "$RUN/repo" && git status --short ) > "$RUN/status.txt"
# the parent session sorts first: a subagent's session starts later
sess=$(find "$HSESS" -name '*.jsonl' 2>/dev/null | sort | head -n 1)
[[ -n $sess ]] && echo "$sess" > "$RUN/session.txt"
# per-lab hooks: check.sh RUN SNAP (the skill's own checker), grade.sh RUN SESSIONDIR (score vs reference)
[[ -x $LAB/check.sh ]] && "$LAB/check.sh" "$RUN" "$SNAP" > "$RUN/check.txt" 2>&1
[[ -x $LAB/grade.sh ]] && "$LAB/grade.sh" "$RUN" "$HSESS" > "$RUN/grade.txt" 2>&1
here=$(cd "$(dirname "$0")/.." && pwd)
if [[ -n $sess ]] && python3 -I "$here/trace.py" "$sess" --json > "$RUN/trace.json" 2>/dev/null; then
  python3 -I -c 'import json,sys; t=json.load(open(sys.argv[1])); print(json.dumps({"total_tokens": t["total_tokens"], "duration_ms": int(sys.argv[2]) * 1000}))' \
    "$RUN/trace.json" "$wall" > "$RUN/timing.json"
fi
[[ -f $LAB/evals.json ]] && python3 -I "$here/assert.py" "$RUN" > "$RUN/assert.txt" 2>&1
cat "$RUN/result.txt"; [[ -f $RUN/grade.txt ]] && tail -1 "$RUN/grade.txt"; [[ -f $RUN/assert.txt ]] && tail -1 "$RUN/assert.txt"
exit 0
