# model-lab

Agent Skills repo: Markdown an agent reads before it writes, restructures or tests a skill, plus the bash and Python 3 lab scripts it runs. `SKILL.md` loads whole on every activation; a file under `references/` loads only when a task opens it.

## Commands

- Full check: `python3 -I evals/lint.py` # body budget, link targets and anchors, a trigger on every reference link, every script and asset named, the leak denylist
- Sizes: `python3 -I evals/lint.py --stats`
- Duplicate candidates: `python3 -I scripts/dups.py` # prints pairs to judge and always exits 0; run after adding or moving a lesson

## Conventions

- A new lesson gets one home: the topic section of the file it belongs to, as one bullet with the rule in bold and then the run that taught it. A section per experiment is how the old pile grew.
- A lesson that contradicts or refines a bullet already there edits that bullet.
- The mechanism is the lesson; the repo and the skill it was found in are details. Name them by kind ("one audit skill", "a Go service repo").
- Prompt and skill-text lessons go to `references/prompts.md`, checker, gate and loop lessons to `references/agentic.md`. What one harness does goes to its page under `references/agents/`, with its runner in `scripts/<agent>/` and its defaults in `assets/<agent>/`.
- `SKILL.md` stays harness-neutral: the "Agents" table is the only place an agent is named. A lesson that fires on most skills earns one line under "The rules that fire on almost every skill", and a rule for reading results goes under "Reading the numbers".
- `SKILL.md` links a reference as `[Section](references/file.md#anchor)` with the moment to read it on the same line. A trigger names a failure the reader can see; "read when writing X" fires on every item and never gets read.
- A reference that touches another file's topic points at it, in the form `references/file.md`, "Section" (read when ...). The receipt keeps its one home; the pointer is how a reader inside one file reaches it. The lint resolves that form and no other.
- What the Agent Skills format and its guides say goes to `references/skill-format.md`, with this lab's measurement next to the recommendation it sharpens or contradicts.
- A script takes `--help`, exits 2 with a one-line error on bad input, and never prompts. A new shared script or asset gets a row in the `SKILL.md` "Scripts" table.
- Model ids, hosts and ports are arguments or examples, never defaults.

## Boundaries

- Always: `python3 -I evals/lint.py` exits 0 before handoff.
- Never: details of one machine or employer (home paths, ports, company, project or ticket names, private skill names, personal rules or preferences). The lint checks the generic kinds and reads your private names from `evals/leaks.local`, one regex per line. That file is gitignored: a denylist committed to the repo is the leak.
- Never: edit a script while a batch that executes it is running; bash reads the file as it goes.

## Pointers

- `evals/evals.json` - what a correct answer contains, per request. Read when a lesson changes the expected answer.
- `evals/trigger-queries.json` - prompts that should and should not activate the skill. Read before changing `description`.
