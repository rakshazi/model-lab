#!/usr/bin/env bash
# Usage: SKILL=<name> [LAB=<dir>] run.sh VARIANT N MODEL
# One omp print-mode run of a skill in the netless sandbox, on a fresh clone of $LAB/base.
# The sandbox is github.com/rakshazi/IISD-sandbox cloned to ~/.omp/docker.
# MODEL is the id your omp models.yml gives the model, e.g. local/qwen3.5-4b.
#
# Env:
#   SKILL      skill dir name under ~/.omp/agent/skills (required)
#   LAB        lab dir holding base/ (default /tmp/$SKILL-lab)
#   MAXTIME    omp --max-time (default 20m)
#   SYSPROMPT  replaces omp's template prompt; also blanks APPEND_SYSTEM.md
#   LEAN=1     adds --no-skills --no-rules --no-extensions
#   CONTEXT=1  keeps context files; by default --no-context-files drops every AGENTS.md
#              and CLAUDE.md, the user's ~/.omp/agent/AGENTS.md and the repo's own alike
#   TOOLS      omp --tools list (default read,write,edit,bash,grep,glob,find,eval)
#              no `todo`: its mid-run nudge interrupts a batch, and the run records its own progress
#   ARGS       user text appended after the skill (the whole prompt under NOSKILL=1)
#   NOSKILL=1  baseline without the skill: the prompt is ARGS alone; check.sh still gets the snapshot
#   OMPFLAGS   extra omp flags, word-split
#   COLLECT    files copied out of the run's repo, e.g. "AGENTS.md"
#   SKILLSNAP  reuse another variant's snapshot; SKILLSRC overrides the skill source dir
#
# After the run, when present: $LAB/check.sh RUN SNAP, $LAB/grade.sh RUN SESSDIR,
# and scripts/assert.py RUN when $LAB/evals.json exists.
# Out: $LAB/runs/VARIANT/N/{repo,prompt.txt,session.log,result.txt,status.txt,trace.json,timing.json,
#      COLLECT files,check.txt,grade.txt,grading.json}
# Sessions: ~/.omp/lab/sessions/VARIANT/N (under ~/.omp because the container mounts it).
# Exit: 0 after any run (the run's own exit is in result.txt); 2 on bad invocation.
#
# Example: SKILL=my-skill COLLECT=AGENTS.md scripts/omp/run.sh v1 1 local/qwen3.5-4b
set -u
case ${1:-} in -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 0 ;; esac
[[ -n ${SKILL:-} && $# -ge 3 ]] || { echo "error: needs SKILL=<name> and VARIANT N MODEL; see --help" >&2; exit 2; }
LAB=${LAB:-/tmp/$SKILL-lab}
[[ -d $LAB/base ]] || { echo "error: no fixture at $LAB/base; build it with scripts/seal.sh" >&2; exit 2; }
VARIANT=$1; N=$2; MODEL=$3
[[ -z ${NOSKILL:-} || -n ${ARGS:-} ]] || { echo "error: NOSKILL=1 needs ARGS, the task as a user would type it" >&2; exit 2; }
SRC=${SKILLSRC:-$HOME/.omp/agent/skills/$SKILL}
[[ -f $SRC/SKILL.md ]] || { echo "error: no SKILL.md in $SRC; set SKILL or SKILLSRC" >&2; exit 2; }
# the snapshot freezes the skill per variant, so the live skill can be edited mid-batch
SNAP=$HOME/.omp/lab/skills/${SKILLSNAP:-$VARIANT}
[[ -d $SNAP ]] || { mkdir -p "$SNAP"; cp -r "$SRC/." "$SNAP/"; rm -rf "$SNAP/.git"; }
CSNAP=/home/agent/.omp/lab/skills/${SKILLSNAP:-$VARIANT}
SESS=/home/agent/.omp/lab/sessions/$VARIANT/$N
RUN=$LAB/runs/$VARIANT/$N
rm -rf "$RUN" "$HOME/.omp/lab/sessions/$VARIANT/$N"; mkdir -p "$RUN"
git clone -q "$LAB/base" "$RUN/repo" && git -C "$RUN/repo" remote remove origin

# print mode does not expand /skill:NAME; rebuild the wrapper the TUI would send
PROMPT="[IMPORTANT: User invoked the \"$SKILL\" skill; follow its instructions. Full skill below.]

$(awk '/^---[ \t]*$/ && n < 2 { n++; next } n >= 2' "$SNAP/SKILL.md")

---

[Skill directory: $CSNAP]
Resolve relative paths in this skill (e.g. \`scripts/foo.js\`, \`templates/config.yaml\`) against this absolute directory; read referenced assets and templates; run scripts with the terminal tool when skill instructions call for it."
[[ -n ${ARGS:-} ]] && PROMPT+=$'\n'"User: $ARGS"
[[ -n ${NOSKILL:-} ]] && PROMPT=$ARGS
printf '%s\n' "$PROMPT" > "$RUN/prompt.txt"

# no task/wait tools: a subagent runs on the cloud task role and the measurement is the named model alone
cmd=(just -f "$HOME/.omp/docker/justfile" run netless --model "$MODEL" -p "$PROMPT" --auto-approve --no-title --wait-async
  --max-time "${MAXTIME:-20m}" --tools="${TOOLS:-read,write,edit,bash,grep,glob,find,eval}" --session-dir "$SESS")
# SYSPROMPT replaces omp's ~14 KB template only; context files are a separate switch (CONTEXT above)
[[ -n ${SYSPROMPT:-} ]] && cmd+=(--system-prompt="$SYSPROMPT") && printf '%s\n' "$SYSPROMPT" > "$RUN/sysprompt.txt"
# a blank append overrides the discovered ~/.omp/agent/APPEND_SYSTEM.md
[[ -n ${SYSPROMPT:-} ]] && cmd+=(--append-system-prompt=" ")
# LEAN=1 drops the skills index, rules and extensions; the skill under test is inlined in the prompt anyway
[[ -n ${LEAN:-} ]] && cmd+=(--no-skills --no-rules --no-extensions)
# the user's global AGENTS.md otherwise rides into every run, and the 4B treats its tool lists as repo facts
[[ -z ${CONTEXT:-} ]] && cmd+=(--no-context-files)
# shellcheck disable=SC2206
[[ -n ${OMPFLAGS:-} ]] && cmd+=($OMPFLAGS)
printf -v cmdstr '%q ' "${cmd[@]}"

t0=$(date +%s)
# the netless flock is released a beat after the previous container exits
sleep 8
( cd "$RUN/repo" && script -qefc "$cmdstr" "$RUN/session.log" >/dev/null 2>&1 )
echo "exit=$? wall=$(( $(date +%s) - t0 ))s" > "$RUN/result.txt"

for f in ${COLLECT:-}; do [[ -f $RUN/repo/$f ]] && cp "$RUN/repo/$f" "$RUN/"; done
( cd "$RUN/repo" && git status --short ) > "$RUN/status.txt"
# per-lab hooks: check.sh RUN SNAP (the skill's own checker), grade.sh RUN SESSIONDIR (score vs reference)
[[ -x $LAB/check.sh ]] && "$LAB/check.sh" "$RUN" "$SNAP" > "$RUN/check.txt" 2>&1
[[ -x $LAB/grade.sh ]] && "$LAB/grade.sh" "$RUN" "$HOME/.omp/lab/sessions/$VARIANT/$N" > "$RUN/grade.txt" 2>&1
here=$(cd "$(dirname "$0")/.." && pwd)
sess=$(find "$HOME/.omp/lab/sessions/$VARIANT/$N" -maxdepth 1 -name '*.jsonl' -print -quit 2>/dev/null)
if [[ -n $sess ]] && python3 -I "$here/trace.py" "$sess" --json > "$RUN/trace.json" 2>/dev/null; then
  wall=$(sed -n 's/.*wall=\([0-9]*\)s.*/\1/p' "$RUN/result.txt")
  python3 -I -c 'import json,sys; t=json.load(open(sys.argv[1])); print(json.dumps({"total_tokens": t["total_tokens"], "duration_ms": int(sys.argv[2]) * 1000}))' \
    "$RUN/trace.json" "${wall:-0}" > "$RUN/timing.json"
fi
[[ -f $LAB/evals.json ]] && python3 -I "$here/assert.py" "$RUN" > "$RUN/assert.txt" 2>&1
cat "$RUN/result.txt"; [[ -f $RUN/grade.txt ]] && tail -1 "$RUN/grade.txt"; [[ -f $RUN/assert.txt ]] && tail -1 "$RUN/assert.txt"
exit 0
