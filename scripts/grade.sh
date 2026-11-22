#!/usr/bin/env bash
# Usage: [OUT=<file>] [LITS=<file>] grade.sh RUNDIR [SESSIONDIR]
# Literal hits of RUNDIR/OUT against a literals file (one fixed string per line, picked from
# the reference output). Copy or symlink to LAB/grade.sh and run.sh calls it after every run.
# A smoke alarm: three runs of one variant spread wider than two variants differ. Read the drafts.
#
# Env:
#   OUT   output file name inside RUNDIR (default AGENTS.md)
#   LITS  literals file (default LAB/literals.txt, three levels above RUNDIR)
#
# Prints: misses, size, repo changes besides OUT, tool-call counts, and a last line "SCORE hits=H/T".
# Exit: 0 graded or no output; 2 bad invocation.
set -u
case ${1:-} in -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 0 ;; esac
[[ -d ${1:-} ]] || { echo "error: RUNDIR is required and must exist; see --help" >&2; exit 2; }
RUN=$1; SESS=${2:-}; OUT=${OUT:-AGENTS.md}; f=$RUN/$OUT
LITS=${LITS:-$(cd "$RUN/../../.." && pwd)/literals.txt}
[[ -f $LITS ]] || { echo "error: no literals file at $LITS; set LITS" >&2; exit 2; }
[[ -f $f ]] || { echo "NO $OUT"; echo "SCORE hits=0/0"; exit 0; }
hits=0; total=0
while IFS= read -r lit; do
  [[ -z $lit ]] && continue
  total=$((total + 1))
  if grep -qF -- "$lit" "$f"; then hits=$((hits + 1)); else echo "  miss: $lit"; fi
done < "$LITS"
echo "LINES $(wc -l < "$f")  BYTES $(wc -c < "$f")  SECTIONS $(grep -cE '^## ' "$f")"
echo "STATUS (changed besides $OUT):"; grep -vF "$OUT" "$RUN/status.txt"
[[ -n $SESS ]] && echo "TOOLCALLS $(cat "$SESS"/*.jsonl 2>/dev/null | grep -o '"toolName":"[a-z_]*"' | sort | uniq -c | sort -rn | tr '\n' ' ')"
echo "SCORE hits=$hits/$total"
