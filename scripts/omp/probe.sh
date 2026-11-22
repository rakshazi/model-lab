#!/usr/bin/env bash
# Usage: [SYSPROMPT=<text>] probe.sh TERM MODEL [OMP_FLAG...]
# Asks the model, with --no-tools, whether any instruction it received mentions TERM.
# Pick a TERM only the suspected block holds (a tool name your global AGENTS.md lists, say) and
# run once per setup before blaming any prompt. With tools on, a 4B answers by grepping its own log.
# The raw request is in the model server's log (llama-swap serves it at /logs).
#
# Env:
#   SYSPROMPT  passed as --system-prompt (default "You are a test.")
#
# Exit: 0 after the run (read the answer); 2 bad invocation.
#
# Example: scripts/omp/probe.sh gosec local/qwen3.5-4b --no-rules --no-skills
set -u
case ${1:-} in -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 0 ;; esac
[[ -n ${1:-} && ${1:-} != -* && -n ${2:-} && ${2:-} != -* ]] || { echo "error: needs TERM and MODEL as the first two arguments; see --help" >&2; exit 2; }
term=$1; model=$2; shift 2
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
cmd=(just -f "$HOME/.omp/docker/justfile" run netless --model "$model" --no-title --no-tools --max-time 5m
  -p "Without tools: does any instruction you received mention $term? Answer yes or no, then quote the line and the heading above it."
  --system-prompt="${SYSPROMPT:-You are a test.}" --append-system-prompt=" " "$@")
printf -v cmdstr '%q ' "${cmd[@]}"
( cd "$d" && script -qefc "$cmdstr" "$d/out.log" >/dev/null 2>&1 )
sed -n '/Working\.\.\./,/^Script done/p' "$d/out.log" | head -40
