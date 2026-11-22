#!/usr/bin/env bash
# Usage: check.sh RUNDIR SNAPDIR   (copy to LAB/check.sh and set the two defaults; the runner calls it after every run)
# Example LAB/check.sh: the skill's own checker, run from the variant's snapshot on the run's repo,
# so every variant is judged by the checker it shipped with.
#
# Env:
#   OUT      the file the skill writes, relative to the repo (default AGENTS.md)
#   CHECKER  the checker inside the skill, relative to its root (default scripts/check.sh)
#
# Exit: the checker's exit; 0 when OUT was not written; 2 bad invocation.
case ${1:-} in -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 0 ;; esac
[[ -d ${1:-}/repo && -d ${2:-} ]] || { echo "error: needs RUNDIR (with repo/) and SNAPDIR; see --help" >&2; exit 2; }
RUN=$1; SNAP=$2; OUT=${OUT:-AGENTS.md}; CHECKER=${CHECKER:-scripts/check.sh}
[[ -f $SNAP/$CHECKER ]] || { echo "error: no $CHECKER in $SNAP; set CHECKER" >&2; exit 2; }
cd "$RUN/repo" || exit 2
[[ -f $OUT ]] || { echo "NO $OUT"; exit 0; }
bash "$SNAP/$CHECKER" "$OUT"
