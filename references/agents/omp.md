# omp as the test stand

Local models through omp in the netless sandbox ([IISD-sandbox](https://github.com/rakshazi/IISD-sandbox), cloned to `~/.omp/docker`). The lab procedure is in `SKILL.md`; this page is what omp adds to it. Each bullet is the fact, then what `scripts/omp/run.sh` does about it. Re-probe after an omp update.

## Running a batch

```bash
for n in 1 2 3; do SKILL=<skill> LAB=/tmp/<skill>-lab COLLECT="AGENTS.md" MAXTIME=20m \
  SYSPROMPT='You are a coding agent working in the repository in the current directory. Use the tools to read files and run commands. Do what the user message asks, then stop.' \
  bash scripts/omp/run.sh v1 $n local/qwen3.5-4b; done > /tmp/<skill>-lab/runs/v1.log 2>&1
```

- **The model id is the one your omp `models.yml` gives it**; `local/qwen3.5-4b` is an example.
- **The skill is read from `~/.omp/agent/skills/<skill>`** and frozen at `~/.omp/lab/skills/<variant>/` on first use of a variant name. Sessions land in `~/.omp/lab/sessions/<variant>/<n>/*.jsonl`. Both live under `~/.omp` because that is the only host dir the sandbox mounts besides the workspace.
- **Every knob is in `scripts/omp/run.sh --help`:** `ARGS`, `NOSKILL`, `CONTEXT`, `OMPFLAGS`, `TOOLS`, `LEAN=1`, `SKILLSNAP`, `SKILLSRC`.
- **Inside the container** `~/.omp` is `/home/agent/.omp`, and the cwd is `/home/agent/workspace/<cwd with / turned into ->`.
- **The sandbox traps are written up on the Pi page and hold here too:** container paths in the output, a skill that writes outside the repo, a skill that calls its script by installed path, two labs sharing a variant name. `references/agents/pi.md`, "Running a batch" (read when a host-side check cannot find a path the run cited, or a run starts from the previous run's file).

## Probing

- **Ask with tools off.** `scripts/omp/probe.sh <term> <model> [flags]` asks, with `--no-tools`, whether a block holding `<term>` reached the model. Pick a term only the suspected block holds. With tools on, a 4B answers by grepping its own `script` log.
- **The raw request is the ground truth.** It sits in the model server's request log (llama-swap serves it at `/logs`); read it when the model's own answer is suspect.

## What the model receives

- **Print mode does not expand `/skill:NAME`.** The literal text reaches the model, and a 4B spent 80 lines hunting for a skill file. `run.sh` rebuilds the wrapper the TUI sends (skill body with frontmatter stripped, plus the `[Skill directory: ...]` footer pointing at the container path of the snapshot).
- **A rollover re-sends the first user message verbatim; tool results may not survive.** The skill body injected into that message survives compaction, while a reference read later may not. Probe after a forced rollover when a rule seems to vanish.
- **`--system-prompt` replaces only omp's ~14 KB template.** Tool schemas, the workspace tree and the context files still arrive. `--system-prompt-template` takes a FILE path that has to exist inside the container, and it changes nothing about the context files either.
- **`~/.omp/agent/AGENTS.md` arrives in every run**, under every flag tried (`--system-prompt`, `--system-prompt-template`, `--no-rules --no-skills --no-extensions`). One that listed security scanners had a 4B treating the list as repo facts: `--version` sweeps over `gosec`/`trivy`/`grype`, `Semgrep` slots in drafts. `run.sh` passes `--no-context-files` by default, which drops it together with the repo's own AGENTS.md and CLAUDE.md. Set `CONTEXT=1` when the repo's context file is part of what the skill meets in real use, and then expect the global file back too. A named `--profile` is the other way out: it keeps the repo's files and drops every piece of user config, but it needs `models.yml` copied into the profile first.
- **`~/.omp/agent/APPEND_SYSTEM.md`** is discovered by default. A blank `--append-system-prompt=" "` overrides it, and `run.sh` sends one whenever `SYSPROMPT` is set.
- **No `task` tool.** A subagent runs on the cloud task role, so the measurement stops being the named model. The default `TOOLS` list leaves it out.
- **No `todo` tool either.** omp's `todo` fires `mid-run-todo-nudge` while items stay open: one audit run took 5 nudges and 13 `todo` calls for a 34-item list in 20 minutes, two of them mid-batch. `takeMidRunNudge` returns null when `todo` is absent from `--tools` (and when `todo.enabled` or `todo.reminders` is off), so the switch is the tool list: `run.sh` passes one without it, and a skill under test that needs the tool gets it back through `TOOLS`.
