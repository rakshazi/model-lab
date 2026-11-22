#!/usr/bin/env bash
# Usage: check.sh RUN SNAP   (copy to LAB/check.sh and set the two defaults; the runner calls it after every run)
# Example LAB/check.sh for a skill whose output lands outside the repo. Moves the files this run wrote
# from OUTDIR into RUN/outside (the next run would otherwise find them and treat them as existing work),
# then runs the skill's own checker on each from the run's repo.
#
# Env:
#   OUTDIR   where the skill writes (default ~/.pi/plans)
#   CHECKER  the checker inside the skill, relative to its root (default scripts/check.sh)
#
# Exit: 0 every file passes; 1 no file or a failing one; 2 bad invocation.
set -u
case ${1:-} in -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 0 ;; esac
[[ $# -eq 2 && -d $1/repo && -d $2 ]] || { echo "error: needs RUN (with repo/) and SNAP; see --help" >&2; exit 2; }
run=$(cd "$1" && pwd); snap=$2; rc=0
OUTDIR=${OUTDIR:-$HOME/.pi/plans}; CHECKER=${CHECKER:-scripts/check.sh}
[[ -f $snap/$CHECKER ]] || { echo "error: no $CHECKER in $snap; set CHECKER" >&2; exit 2; }
mkdir -p "$run/outside"
find "$OUTDIR" -maxdepth 1 -type f -newer "$run/prompt.txt" -exec mv -t "$run/outside" {} + 2>/dev/null
files=("$run"/outside/*)
[[ -f ${files[0]} ]] || { echo "NO OUTPUT: the run wrote no file into $OUTDIR"; exit 1; }
for f in "${files[@]}"; do
  echo "== $(basename "$f"): $(wc -l < "$f") lines"
  ( cd "$run/repo" && bash "$snap/$CHECKER" "$f" ) || rc=1
done
echo "== tree: $(wc -l < "$run/status.txt") changed paths"
cat "$run/status.txt"
exit $rc
