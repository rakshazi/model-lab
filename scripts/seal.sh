#!/usr/bin/env bash
# Usage: [PREP=<cmd>] [KEEP="<dir> ..."] seal.sh SRC_REPO LAB [EXCLUDE_PATH...]
# Builds LAB/base: the tracked files of SRC_REPO minus the excluded paths, as ONE fresh commit,
# so no model (or its subagent) can read the answer key out of `git show HEAD~1:AGENTS.md`.
# The commit carries a throwaway author, is unsigned and skips hooks: your git config stays out of it.
#
# Env:
#   PREP      command run in LAB/base before the commit, e.g. "go mod vendor" (the sandbox has no network)
#   KEEP      dirs force-added past .gitignore after PREP, e.g. "vendor"
#
# An EXCLUDE_PATH is a file or a directory prefix.
# Exit: 0 sealed; 1 an excluded path survived; 2 bad invocation or LAB/base already exists.
#
# Example: PREP='go mod vendor' KEEP=vendor scripts/seal.sh ~/src/app /tmp/app-lab AGENTS.md CLAUDE.md
set -euo pipefail
case ${1:-} in -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 0 ;; esac
[[ $# -ge 2 ]] || { echo "error: needs SRC_REPO and LAB; see --help" >&2; exit 2; }
src=$1; lab=$2; shift 2
git -C "$src" rev-parse --git-dir >/dev/null 2>&1 || { echo "error: $src is no git repository" >&2; exit 2; }
[[ -e $lab/base ]] && { echo "error: $lab/base exists; remove it first" >&2; exit 2; }
mkdir -p "$lab/base"
git -C "$src" ls-files | awk -v ex="$*" '
  BEGIN { n = split(ex, x, " ") }
  { for (i = 1; i <= n; i++) if ($0 == x[i] || index($0, x[i] "/") == 1) next; print }' > "$lab/files.txt"
# a tracked file deleted in the worktree is absent from the fixture, the same as the worktree shows it
rsync -a --ignore-missing-args --files-from="$lab/files.txt" "$src/" "$lab/base/"
[[ -n ${PREP:-} ]] && ( cd "$lab/base" && eval "$PREP" )
git -C "$lab/base" init -q
git -C "$lab/base" add .
for d in ${KEEP:-}; do git -C "$lab/base" add -f -- "$d"; done
git -C "$lab/base" -c user.name=lab -c user.email=lab@localhost -c commit.gpgsign=false -c core.hooksPath=/dev/null \
  commit -qm "initial import"
for p in "$@"; do [[ -e $lab/base/$p ]] && { echo "error: excluded path still present: $p" >&2; exit 1; }; done
echo "sealed $(git -C "$lab/base" ls-files | wc -l) files into $lab/base; excluded: $*"
