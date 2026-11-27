# Evaluating a skill

A lab answers one question: what does THIS model do with THIS skill on THIS repo. Everything below exists because a run once measured something other than that.

The agents and the scripts are the "Agents" and "Scripts" tables in `SKILL.md`. Pick the agent there and read its page before the first run.

## Layout

```
$LAB/                          # /tmp/<skill>-lab
  base/                        # sealed fixture: one commit, no answer key (scripts/seal.sh)
  evals.json                   # spec-shaped eval: prompt, expected_output, assertions (scripts/assert.py)
  literals.txt                 # optional: fixed strings from the reference output, for grade.sh
  check.sh  RUN SNAP           # optional: the skill's own checker on the output (exec bit)
  grade.sh  RUN SESSDIR        # optional: copy or symlink scripts/grade.sh (exec bit)
  snap/<variant>/              # the skill frozen on first use of a variant name
  runs/<variant>/<n>/          # repo/, session/, session.txt, prompt.txt, session.log, result.txt,
                               #   status.txt, outputs, trace.json, timing.json, grading.json
  runs/<variant>/benchmark.json  # scripts/summary.py: mean/stddev, delta against the baseline
```

## Procedure

1. **Fixture.** `PREP='go mod vendor' KEEP=vendor scripts/seal.sh <src-repo> $LAB AGENTS.md CLAUDE.md`. Exclude the reference output and anything that leaks it. One fresh commit, because a cloud subagent once scored 31 of 32 by running `git show HEAD~1:AGENTS.md`. The sandbox has no network, so dependencies come in through PREP.
2. **Evals and graders.** Write `$LAB/evals.json` from `assets/evals.example.json`: the user's prompt, the expected output in plain words, the `outputs` to grade, the `context` files the judge treats as truth, and five to ten assertions. Use a script assertion for anything a grep can settle (a command named, an invented target absent, no scaffolding left) and a sentence for judgment ("warns that db-reset wipes the local database"). A good assertion separates a good draft from a bad one: one that passes in every run, skill or no skill, measures nothing, so replace it. Literals in `literals.txt` stay as the smoke alarm, and the skill's own checker goes in `check.sh`.
3. **Probe** what the model receives, once per setup, before blaming any prompt. The agent's page has the command.
4. **Baselines**: three runs with `NOSKILL=1` (the bare task, same `ARGS`), which shows what the skill adds at all. Then the current skill, three runs. Then **one change per variant**, three runs each. A snapshot is taken on first use of a variant name, so the live skill can be edited while a batch runs, unless it calls its own script by installed path: that executes the live file.
5. **Run** in the background, one batch at a time, from the skill root, with the agent's runner: `bash scripts/<agent>/run.sh <variant> <n> <model>`. The model id is required and comes from your harness config.
6. **Read** the batch: `python3 -I scripts/summary.py $LAB noskill v1 v2 --signal '<done signal text>'` gives the table and the deltas. Then, per run that stands out: `status.txt` (did it edit the repo?), `check.txt`, `grading.json` (the evidence behind each FAIL), and `python3 -I scripts/trace.py <session.jsonl> --after '<signal>'` for what the model did once it was told it had finished. Read the drafts against the reference last, and read them yourself.
7. **File the lesson**: the rule, then the run that taught it, as one bullet in the reference section it belongs to. This skill's own `AGENTS.md` has the filing rules.

## Reading the numbers

- **n=3 spreads 0 to 15 within one variant.** That is wider than any difference between two variants, so a literal score is a smoke alarm, never the verdict. A zero is usually a timeout or an output cap: read the trace before reading the score.
- **An output cap is a tax on the batch.** Thinking-mode sampling (temp 0.6, top-p 0.95, top-k 20, no presence penalty; Qwen recommends the penalty for instruct mode only) leaves runaway generations in. Roughly one run in five spends 11 to 13 silent minutes on one tool call that hits the 32768-token output cap (`stopReason: length`), and then times out. `trace.py` prints `OUTPUT CAP` for it, and it says nothing about the skill.
- **A pass/fail cell at five runs cannot tell 40% from 75%.** One tool description scored 1 of 5 in a batch and 15 of 20 on the cell alone. Four stray tool calls in 75 runs against zero for the baseline vanished at 60 runs per arm, where the baseline produced the only one. When one cell carries the verdict, rerun that cell at 20 and leave the batch alone.
- **Repeat before believing, one change at a time.** At temperature 0.1 a key term survived under one prompt and died under the next, with no rule touching it. A verdict needs the same input moved the same way twice. Two review suggestions applied together graded as a gain (83 to 97 facts) and hid that one of them was an example leak; split into two variants, one was kept and the other refused.
- **A fix proves itself in the trace.** The question is whether the mechanism changed (the warning gone, the loop shorter, the minutes after the done signal), and a batch average can't answer it.
- **Grade the content, never the shape.** Headers, sections and markers all appeared while the inside carried fabricated paths and dropped the final request. Grep every literal (path, identifier, test name) against the source, plus two or three literals per input that survive only if the pending request did.
- **Grade the outcome the user asked for.** Pick the outcome metric before the first variant and report proof quality as a separate axis: a skill can buy perfect citations for twice the wall time while the bugs found stay flat. The run that paid for it: `references/agentic.md`, "Gates and the loop surface" (read when proof work eats the budget).
- **A pass can come from an edited repo.** A gate that checks only the output gets passed by changing something else, and `status.txt` shows it.
- **A judge has a noise floor.** Grade blind, then regrade the unchanged arm with a second judge and a new seed: `references/agents/claude-code.md`, "Grading" (read before any model judges a batch).
- **Read where the time went.** A 27B never wrote the file: 45 minutes of reading, thinking blocks of 20 to 28k characters. A slow model's failure is often budget, and `trace.py` shows it.
- **Exit 0 proves nothing about existence.** Check a named target against the file that defines it.

## Pitfalls

- **Never edit a script a running batch executes.** Bash reads it as it goes, so the change lands mid-run. Wait for the batch, or edit a copy.
- **One netless session at a time** (a flock). The local runners sleep 8 s before starting so the previous container's lock has been released.
- `pgrep -f <pattern>` and `pkill -f` match their own command line, so anchor the pattern.
- Run real repositories only inside the sandbox. A host-side test of a "safe to run?" classifier ran a plugin installer and opened a browser tab.
- The skill under test is often its own git repo, and its owner commits. The lab never does.
