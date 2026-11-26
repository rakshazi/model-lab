#!/usr/bin/env bash
# Usage: LAB=<dir> TASK=<file> SKILLSRC=<dir> run.sh VARIANT N [MODEL]
# One cold headless Claude Code run of a skill on a fresh clone of the fixture repo: the real
# binary under --safe-mode (no CLAUDE.md, memory, plugins, hooks or user skills), the skill sent
# the way a slash command sends it.
#
# Env:
#   LAB         lab dir (required)
#   TASK        file with the user's request: becomes <command-args> and replaces $ARGUMENTS (required)
#   SKILLSRC    dir holding SKILL.md (required unless NOSKILL=1); frozen per VARIANT on first use
#   PLUGIN      plugin name: the wrapper says /PLUGIN:SKILL like an installed plugin skill
#   NOSKILL=1   baseline: the prompt is the task alone
#   REPO        repo cloned per run (default $LAB/base); BRANCH (default its current branch)
#   SYSTEM      file for --append-system-prompt (default assets/claude-code/system.txt)
#   ALLOW       permission rules, one per line (default assets/claude-code/allow.txt)
#   CCPATH      dir prepended to PATH, for a tool the skill expects there
#   POST        shell command run in the clone after the run, into post.txt (e.g. "go build ./...")
#   MAXTIME     timeout (default 45m)
#   CLAUDE_BIN  the claude ELF binary (default: the first `claude` on PATH that is not a wrapper script)
#
# After the run, when present: $LAB/check.sh RUN RUN/repo, its output in check.txt.
# Out: $LAB/runs/VARIANT/N/{repo,session/,session.txt,prompt.txt,result.json,stderr.txt,status.txt,
#      diff.patch,post.txt,check.txt}. Snapshots: $LAB/snap/VARIANT. During a run the clone and this
#      variant's skill sit alone in a fresh $LAB-run.XXXXXX, removed after.
# Exit: 0 after any run (the run's own exit is in status.txt); 2 on bad invocation.
#
# Example: LAB=/tmp/widget-lab TASK=/tmp/widget-lab/task.txt SKILLSRC=~/skills/widget POST='go build ./...' \
#            scripts/claude-code/run.sh v1 1 sonnet
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
case ${1:-} in -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 0 ;; esac
[[ -n ${LAB:-} && -n ${TASK:-} && $# -ge 2 ]] || { echo "error: needs LAB=, TASK= and VARIANT N; see --help" >&2; exit 2; }
[[ -f $TASK ]] || { echo "error: TASK $TASK is not a file; write the user's request into it" >&2; exit 2; }
[[ -n ${NOSKILL:-} || -f ${SKILLSRC:-}/SKILL.md ]] || { echo "error: no SKILL.md in SKILLSRC; set it or NOSKILL=1" >&2; exit 2; }
VARIANT=$1 N=$2 MODEL=${3:-sonnet}
REPO=${REPO:-$LAB/base}
git -C "$REPO" rev-parse -q --verify HEAD >/dev/null || { echo "error: $REPO is not a git repo; build it with scripts/seal.sh or set REPO" >&2; exit 2; }
BRANCH=${BRANCH:-$(git -C "$REPO" branch --show-current)}
if [[ -z ${CLAUDE_BIN:-} ]]; then
	for c in $(type -ap claude); do file -L "$c" | grep -q -E 'ELF|Mach-O' && { CLAUDE_BIN=$c; break; }; done
fi
[[ -x ${CLAUDE_BIN:-} ]] || { echo "error: no claude binary found; set CLAUDE_BIN" >&2; exit 2; }

SNAP=$LAB/snap/$VARIANT
if [[ -z ${NOSKILL:-} && ! -d $SNAP ]]; then mkdir -p "$SNAP"; cp -r "$SKILLSRC/." "$SNAP/"; rm -rf "$SNAP/.git"; fi

# a model that lists its skill's base dir or its cwd's parent must find only this run
RUN=$LAB/runs/$VARIANT/$N STAGE=$(mktemp -d "$LAB-run.XXXXXX")
W=$STAGE/repo BASE=$STAGE/skill
rm -rf "$RUN"; mkdir -p "$RUN"
[[ -z ${NOSKILL:-} ]] && cp -r "$SNAP" "$BASE"
git clone -q --shared ${BRANCH:+--branch "$BRANCH"} "$REPO" "$W"
git -C "$W" remote set-url origin /nonexistent/origin.git

if [[ -n ${NOSKILL:-} ]]; then
	cp "$TASK" "$RUN/prompt.txt"
else
	python3 -I - "$BASE/SKILL.md" "$BASE" "$TASK" "${PLUGIN:-}" >"$RUN/prompt.txt" <<'EOF'
import re, sys
skill, base, task, plugin = sys.argv[1], sys.argv[2], open(sys.argv[3]).read().strip(), sys.argv[4]
text = open(skill).read()
name = re.search(r"^name:\s*(\S+)", text, re.M).group(1)
body = text.split("---", 2)[2].lstrip("\n").replace("$ARGUMENTS", task)
cmd = f"/{plugin}:{name}" if plugin else f"/{name}"
print(f"<command-message>{name}</command-message>\n<command-name>{cmd}</command-name>\n"
      f"<command-args>{task}</command-args>\n\nBase directory for this skill: {base}\n\n{body}")
EOF
fi

allow=()
while IFS= read -r l; do [[ -n $l && $l != \#* ]] && allow+=("$l"); done <"${ALLOW:-$here/assets/claude-code/allow.txt}"
# the staged path is new every run, so no allow file can name it: grant the skill's own dir here
dirs=()
if [[ -z ${NOSKILL:-} ]]; then
	dirs=(--add-dir "$BASE")
	allow+=("Bash($BASE/*)" "Bash(bash $BASE/*)" "Bash(sh $BASE/*)" "Bash(python3 $BASE/*)" "Bash(python3 -I $BASE/*)")
fi
[[ -n ${CCPATH:-} ]] && export PATH=$CCPATH:$PATH
start=$(date +%s)
# the prompt goes on stdin: --allowedTools is variadic and swallows a trailing prompt argument
(cd "$W" && timeout "${MAXTIME:-45m}" "$CLAUDE_BIN" --safe-mode -p --model "$MODEL" --output-format json \
	--permission-mode acceptEdits "${dirs[@]}" --allowedTools "${allow[@]}" \
	--append-system-prompt "$(cat "${SYSTEM:-$here/assets/claude-code/system.txt}")" \
	<"$RUN/prompt.txt" >"$RUN/result.json" 2>"$RUN/stderr.txt")
rc=$?
sid=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("session_id",""))' "$RUN/result.json" 2>/dev/null)
mv "$W" "$RUN/repo"; rm -rf "$STAGE"; W=$RUN/repo
# the project dir is named after the one-off staging path, so the transcript moves into the run
proj=$HOME/.claude/projects/$(sed 's#[^a-zA-Z0-9]#-#g' <<<"$STAGE/repo")
mkdir -p "$RUN/session"; [[ -n $sid && -f $proj/$sid.jsonl ]] && cp "$proj/$sid.jsonl" "$RUN/session/" && echo "$RUN/session/$sid.jsonl" >"$RUN/session.txt"
rm -rf "$proj"
{
	echo "exit=$rc wall=$(($(date +%s) - start))s model=$MODEL"
	echo "transcript=$RUN/session/$sid.jsonl"
} >"$RUN/status.txt"
git -C "$W" add -N . 2>/dev/null
git -C "$W" diff >"$RUN/diff.patch"
git -C "$W" diff --stat >>"$RUN/status.txt"
if [[ -n ${POST:-} ]]; then (cd "$W" && eval "$POST") >"$RUN/post.txt" 2>&1; echo "post_exit=$?" >>"$RUN/status.txt"; fi
if [[ -x $LAB/check.sh ]]; then "$LAB/check.sh" "$RUN" "$W" >"$RUN/check.txt" 2>&1; echo "check_exit=$?" >>"$RUN/status.txt"; fi
exit 0
