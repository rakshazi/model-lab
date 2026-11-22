# Claude Code as the test stand

For a skill a cloud model will run (Sonnet, Haiku, Opus) the way a user's Claude Code session runs it: cold, with the skill arriving as a slash command. Measured on one A/B of a schema-migration skill, Sonnet, n=3 per arm, on a large Go service repo. Each bullet is the rule, then the run that taught it.

## Procedure

This replaces the local-model procedure in `SKILL.md`; the lab layout and the rules for reading a batch still apply. Script paths are relative to the skill root; each script takes `--help`.

1. **Task.** A request a user would type, still open in the repo (grep the schema history and the code first), and hard enough to separate the arms. Write it to `$LAB/task.txt`.
2. **Rubric** to `$LAB/rubric.md` before any run: 6 to 10 items scored 0/1, led by the user's outcome; cost is its own axis.
3. **Variants.** Old skill from git (`git show HEAD:path/SKILL.md` into a dir), the new one from the tree; `NOSKILL=1` for the bare baseline. `PLUGIN=<name>` when the skill ships in a plugin. A tool the skill calls goes on `CCPATH` and into a copy of `assets/claude-code/allow.txt` as both `Bash(tool)` and `Bash(tool *)`.
4. **Smoke** one tiny prompt that calls every lab tool bare and piped, under the same allow file, before spending a batch.
5. **Batch**, in the background, all arms at once:
   ```bash
   export LAB=/tmp/<skill>-lab TASK=/tmp/<skill>-lab/task.txt REPO=<repo> POST='<build command>' ALLOW=$LAB/allow.txt
   for v in old new; do for n in 1 2 3; do SKILLSRC=$LAB/src-$v bash scripts/claude-code/run.sh $v $n sonnet & sleep 3; done; done; wait
   ```
6. **Read** `python3 -I scripts/claude-code/summary.py $LAB old new --count '<tool>'` first. Any denial on a variant's own tool voids that arm: fix the allow file, rerun it.
7. **Grade blind:** `python3 -I scripts/claude-code/blind.py $LAB /tmp/<skill>-blind old/1 old/2 old/3 new/1 new/2 new/3 --redact '<tool>' --seed 1`, fill `assets/claude-code/judge.md`, give it to an Opus subagent. Then a second bundle with a new seed and a fresh judge over the same runs: the score moves between the two judges are the noise floor.
8. **Report** per arm: rubric mean and spread, both judges, cost, and the trace facts behind the difference.

## A cold model

- **Run the real binary under `--safe-mode -p`.** It drops CLAUDE.md, memory, plugins, hooks, user skills and output styles. It does not drop a system prompt passed on the command line, and a launcher wrapper that passes its own `--system-prompt-file` (a persona, house rules) survives it: the first "cold" Sonnet named that file in its context and answered in its voice. `scripts/claude-code/run.sh` picks the first `claude` on PATH that is an ELF or Mach-O binary. Probe once per machine: ask the model which CLAUDE.md, memory, persona or skill text it sees; the clean answer lists the stock built-in skills and nothing else.
- **Agent-tool subagents are not cold.** `general-purpose` and custom agents inherit the global CLAUDE.md and memory, and a builtin Explore or Plan agent picks up path-scoped rules on its first Read. A global CLAUDE.md that carries the house rules hands the baseline arm what the skill is supposed to add. Use them as judges, never as subjects.
- **Send the skill the way a slash command does:** `<command-message>`, `<command-name>/plugin:skill`, `<command-args>`, `Base directory for this skill: DIR`, then the body with `$ARGUMENTS` replaced. `run.sh` builds it from the frozen snapshot.
- **Keep the snapshot outside the lab dir.** A run ran `ls` on its skill's base directory, which sat inside the lab next to the other runs' output. `run.sh` freezes skills in `$LAB-skills/VARIANT`.
- **The user is unavailable; say so in the system text.** "Put the question in your final reply and continue with the choice you would recommend" (`assets/claude-code/system.txt`) keeps a run from stopping at the skill's first "ask the user", in every arm alike.

## Permissions

- **Feed the prompt on stdin.** `--allowedTools` is variadic and swallowed a trailing prompt argument: `Input must be provided either through stdin or as a prompt argument`.
- **`Bash(x:*)` does not cover a bare `x`.** The arm whose skill names a checker tool had it allowed as `Bash(tool:*)`; every run called it bare, got "requires approval" 5 or 6 times, never saw one line of its output, and graded as the skill's prose alone. List `Bash(x)` and `Bash(x *)` (`assets/claude-code/allow.txt`), pass the rules as an array, and before a batch run one tiny prompt that calls each lab tool in its bare and piped form.
- **A denial is a harness bug until the trace says otherwise.** Read `denied` in `summary.py` before any score. A denial on the variant's own tool means the lab is broken: fix it and rerun that arm. A residual one (a compound `grep -v "a\|b"`, a `cat >` heredoc where Write was the tool, `go list`) is friction both arms meet.
- **The allowlist is no fence.** Claude Code auto-allows commands it classes as read-only, and under `acceptEdits` a `tr ... > f.tmp && mv f.tmp f` rewrote a file with neither command listed. The fence is the throwaway `--shared` clone, `origin` pointed at a dead path, and the system text (no database, no deploy, no commits). `--safe-mode` also turns off the host's own guard hooks, so nothing else stands between a run and the machine.
- **A tool the skill expects on PATH goes in `CCPATH`.** A plugin's `bin/` is on PATH in real use and absent under `--safe-mode`.

## Building the fixture in your own session

- **Your session's guard hooks fire on scratch repos too.** A throwaway repo under `/tmp` was refused `git add .`, a push to a protected branch, a branch name and a commit subject off the house format, and `git checkout`/`stash` between cases. Make the base ref with `git update-ref refs/remotes/origin/<branch> HEAD` (and `git symbolic-ref refs/remotes/origin/HEAD ...`) instead of pushing, name branches and commits to the format, and copy one fixture per case instead of resetting one.
- **Check the task is still open before you hand it out.** The first candidate task, dropping three cost columns from a big table, had already shipped 160 migrations earlier; every run would have been graded on fixing a solved problem. Grep the schema history for the columns and the model for the fields first.
- **Pick a task that trips the hard parts.** The useful one moved two columns with live data off a hot table: backfill, dual write, a read switch, locks, and a column list passed as strings that no tag scan sees. A one-release task scores every arm the same.

## Grading

- **Write the rubric to disk before the first run.** Lead with the outcome the user cares about (would this branch, deployed next to the old pods, break production or lose data) and keep cost (wall, turns, USD from `summary.py`) as its own axis.
- **Run the skill's own checker on every arm afterwards** (`$LAB/check.sh RUN CLONE`). A tool only one arm could call becomes the same measuring stick for all; so does `POST='go build ./...'`.
- **Grade blind with a fresh agent.** `blind.py` shuffles the runs into `R1..Rn`, redacts names only one arm would use, and keeps the key out of the bundle; fill `assets/claude-code/judge.md` and give it to an Opus subagent with read access to the repo, so it verifies every citation itself. Redaction leaves a trace ("`[redacted]` passed" says some tool existed); report the judge as partly blind when it does.
- **Re-grade the unchanged arm with a second judge and a new seed.** The scores that move between two judges on the same runs are the noise floor; a delta smaller than that is no result.
- **Give the judge exit codes.** A passing `go build` prints nothing, the bundle carried an empty `post.txt`, and the judge scored "builds" from reading the diff. `blind.py` now writes `exit N` at the top of `post.txt` and `check.txt`.
- **Two judges disagree on single items.** On the same unchanged runs, one judge moved one run by a point (mean 8.3 to 8.7). A defect one judge traced through the code (a `NOT NULL DEFAULT 0` column plus `use_zero` that a full-row update overwrites with 0) went unscored by the other on the same pattern. Report per-item scores next to totals.
- **A green checker ends the search.** With its checker locked out, the rewritten skill's runs spent 45 turns and covered both write paths of the moved data in 3 of 3 runs. With the checker working, they spent 27 turns, read "0 fails", and covered both in 1 of 3. The checker judged rollout safety, which every run already had, and stayed silent on the writers it cannot see, so its pass read as "done". A checker that passes must also print what it did not check, with the sites to look at. The next variant printed, after the verdict table, every base line that named a touched column as a string or set its Go field, ending "N sites to account for in the report (this list prints on every run, it never clears)", and the skill asked for a covered/other/missing verdict per site. Coverage of both writers went from 1 of 3 to 3 of 3, two fresh judges scored it 9.3 and 10.0 against the old skill's 8.3 and 7.7, the runs called the checker 2 or 3 times each (no loop on the list that never clears), and cost rose from $0.44 to $0.57 a run.
- **Read the traces too.** The runs whose tool was locked out still beat the baseline 9.7 to 8.3 on the rubric, on prose alone, and the trace showed why their tool counts were twice the baseline's: they kept trying the locked door. Transcripts repeat each `tool_use` across streamed lines, so count by id: the raw count said ten checker calls where there were five.
