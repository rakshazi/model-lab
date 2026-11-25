# The skill as a file tree

What the Agent Skills format ([agentskills.io](https://agentskills.io)) fixes, what its authoring guides recommend, and where this lab's runs sharpen or contradict them. The format is the same for a 4B and a frontier model. The calibration differs, and each section says where.

## Frontmatter and layout

A skill is a directory. `SKILL.md` is the only required file; `scripts/` holds code the agent runs, `references/` holds docs it opens on demand, `assets/` holds templates and data. Subdirectories are fine: this skill keeps one page per harness under `references/agents/`.

| Field | Required | Constraint |
|---|---|---|
| `name` | yes | 1 to 64 characters, lowercase letters, digits and single hyphens, no hyphen at either end, equal to the directory name |
| `description` | yes | 1 to 1024 characters: what the skill does and when to use it |
| `license` | no | a license name, or the name of a bundled license file |
| `compatibility` | no | up to 500 characters, only for a real requirement (product, packages, network) |
| `metadata` | no | a string-to-string map for everything the format does not define (`version`, `author`) |
| `allowed-tools` | no | space-separated pre-approved tools; experimental, support varies by client |

- **A field outside this set goes under `metadata`.** Clients ignore unknown top-level keys, so a key placed there does nothing.
- **Paths are relative to the skill root, in `SKILL.md` and in every reference alike.** The agent runs commands from the root, so `scripts/seal.sh` means the same thing wherever it is written.
- **Validate with `skills-ref validate ./my-skill`** when the tool is installed. It checks the frontmatter and the naming rules, and nothing about whether the skill works.

## Description and triggering

- **The description carries the whole activation.** At startup an agent loads `name` and `description` for every installed skill, about 100 tokens each, and nothing else. A vague one ("helps with PDFs") never fires.
- **Write it as an instruction about the user's intent.** "Use when the user ..." beats "This skill does ...". Name the asks that never mention the domain ("even when the user only says ..."). A few sentences are enough; every installed skill pays for a long one.
- **A skill fires on tasks the agent cannot do alone.** A one-step request may skip a matching skill because basic tools cover it. Test with tasks that need the knowledge.
- **Test it with about 20 labelled queries.** Eight to ten that should trigger, varied in phrasing, explicitness, detail and complexity, and eight to ten that should stay silent. The useful negatives are near-misses that share keywords and need something else. Write them the way users type: file paths, personal context, typos. `evals/trigger-queries.json` in this skill is the shape.
- **Three runs per query, a rate per query.** A should-trigger query passes above 0.5, a should-not below it.
- **Split 60/40 and tune on the 60.** Revise the description from the train failures only, by widening or narrowing the concept; a keyword copied from a failed query is overfitting. Keep the version with the best validation rate, which may be an earlier one. Five rounds are usually enough; past that, suspect the queries.
- **A small model reads the description as input too.** A 1.7B titling a session copied the description's sample ask as the title: `references/prompts.md`, "Input" (read when a skill's own description shows up in a small model's output).
- **A project skill needs an order in the always-loaded file.** One repo's image runbook moved from a README into a project skill beside a clean per-item data directory. With the skill in the index and a soft pointer in `AGENTS.md` ("the skill holds the pipeline"), a 26B opened `SKILL.md` in 2 of 3 runs; the third listed the data directory, read two neighbouring items and copied their older shape, scoring 7 of 19. Changing that line to "before creating or editing anything under `<dir>/`, MUST read `<path>/SKILL.md`" got 9 of 9 runs to open it. Every run that read no doc scored 7, with the old README and with the skill alike. A tidy tree makes the examples easier to find than the instructions, so the order sits where every session reads it.

## Body and references

- **Three tiers.** Metadata loads always, the body loads on activation, everything else loads when the agent opens it. Keep the body under 500 lines and 5000 tokens.
- **In a project skill, write paths from the repo root.** The format asks for paths relative to the skill root, and a model that opens `SKILL.md` with a plain read resolves them against its working directory. A body naming `assets/<file>.json` got a failed read as the second call of 3 of 3 runs, then two to four `ls` and `find` calls, and one run wrote the full skill path into a field that wanted the short form. The full repo-relative path in the body removed the hunt: 4 to 7 tool calls against 7 to 13, and 58K mean tokens against 137K.
- **The body holds what every run needs:** the procedure, and the gotchas (facts that defy a reasonable assumption). A gotcha in a reference needs the agent to recognise its trigger first, which is the thing a gotcha defeats.
- **Add what the agent lacks.** Per line: would the agent get this wrong without it? If the agent does the whole task well with no skill, the skill adds nothing, and only a no-skill baseline shows that.
- **One coherent unit.** Too narrow and several skills load for one task; too broad and the description cannot fire precisely.
- **Every reference link says when to read it.** "Read `api-errors.md` if the API returns a non-200" loads on demand; "see references/" loads never. This lab adds: the trigger names a failure the reader can see, because a trigger that is true for every item gets read for none of them: `references/prompts.md`, "Input" (read when a reference is opened too early, or never).
- **Cross-reference the references.** A file that touches another file's topic names that file and its section, with its own read-when. An image-prompting skill with a dozen references gave each finding one home and pointed the files at each other by section. A 27B then scored 9 of 9, including the one assertion whose fact lived only in a reference, because the run followed the pointer to that file. Three runs on another brief each opened the three references the pointers name, where an interactive session before the change had opened two in 793 messages. Knowledge that sits one file away without a pointer is skipped, and nothing in the output says so.
- **One home per fact, and a pointer everywhere else.** A rule written into the body and again into a reference drifts: one copy gets edited and the model meets both. The intended pair is a one-line rule in the body with its receipt in a reference; two copies of the receipt, or two references explaining the same thing, is the duplicate. `scripts/dups.py <skill-dir>` lists the candidate pairs by shared phrase, measured number and backticked literal. Read each pair: on its first run against the image-prompting skill it found one block of over twenty words pasted into four reference files.
- **A cross-reference is a second door, never the only one.** The format asks for references one level deep with no nested chains: every file stays linked from `SKILL.md`, and a pointer between two references adds a route for the reader who is already inside one of them.
- **Reads cost context.** In the same runs, four or five references opened meant 92K to 101K input tokens against 32K to 53K for one or two. A pointer with a narrow trigger is how the right file gets read and the others stay closed.
- **Alternatives get a page each.** One harness of three, one provider, one output target: the body names them in a single table with each page's read-when and keeps its procedure neutral. The "Agents" table in this skill is the example.
- **Maintenance rules live in `AGENTS.md`,** with a one-line pointer at the foot of `SKILL.md`. Where a new lesson goes and what the lint checks serve the agent that edits the skill; in the body, every user of the skill pays for them. A harness injects `AGENTS.md` from the working directory, and the edit usually starts in some other repo, which is why the pointer sits in the file the editor opens first.
- **Lint the tree.** A body budget, every link target and anchor, a trigger on every reference link, every script named: `evals/lint.py` in this skill does those four in a hundred lines.

## Instruction patterns

- **Match specificity to fragility.** Exact commands and a fixed order where one wrong flag breaks the task; the reason and some room where several approaches work.
- **A default, with the alternative in a clause.** A list of equal options makes the agent try several.
- **Teach the approach.** "Read the schema, join on the `_id` columns, filter, aggregate" serves every query; the answer to one query serves one.
- **A template for a fixed output shape.** Short ones inline, long or rarely needed ones in `assets/`.
- **A checklist for steps with dependencies, and a validation loop:** do the work, run the validator, fix, repeat until it passes.
- **Plan, validate, execute** for batch or destructive work: a structured plan file, a script that checks it against the source of truth, then the run. The validator's error names what is wrong and what is allowed.
- **Bundle what the agent reinvents.** When several traces show the same helper being rewritten, write it once in `scripts/`.
- **Calibrate to the model.** The guides find that an explained reason beats a rigid directive and that lean skills beat exhaustive ones; both hold for large models. For a small one this lab measured the other half: RFC 2119 words, the exact command, one complete example, and every rule a script can hold moved into the script. `references/prompts.md`, "Before writing a rule" (read when one skill has to serve a 4B and a frontier model).

## Scripts

- **List every script in `SKILL.md`** with one line on when to use it, and call it by its path from the skill root.
- **Self-contained.** Declare dependencies inline (PEP 723 with `uv run`, `npx pkg@version`, `deno run npm:pkg@version`) and pin versions. State what the host must have in `compatibility`.
- **No prompts, ever.** An agent's shell is non-interactive, and a script that waits for input hangs the run. Take input through flags, environment and stdin.
- **`--help` is the interface.** A short description, the flags, one example. It lands in the agent's context, so keep it short.
- **An error says what went wrong, what was expected and what to try.** This lab's version is stricter: one line naming the next action, because a 4B read 40 lines of usage as a puzzle. `references/agentic.md`, "Gates and the loop surface" (read when a run loops on a script's error).
- **Data on stdout, diagnostics on stderr,** in a format tools can parse (JSON, TSV).
- **Safe to retry.** Idempotent where possible, a `--dry-run` for anything destructive, distinct exit codes documented in `--help`.
- **Bounded output.** Harnesses truncate tool output somewhere between 10K and 30K characters: print a summary by default and offer a flag for the rest.
- **A script is also where a rule binds.** What the guides call bundling, this lab treats as the main control surface for a small model: `references/agentic.md`, "Scripts over prose" (read when writing the checker for a skill).

## Evals in the spec's shape

- **`evals/evals.json` ships with the skill:** `skill_name` and a list of `evals`, each with `id`, `prompt` (what a user would type), `expected_output` (success in plain words), optional `files`, and `assertions`.
- **Start with two or three cases** and write the assertions after the first outputs exist. A good one is specific and observable; "the output is good" grades nothing and an exact phrase fails correct answers.
- **Run each case with the skill and without it,** or against a snapshot of the previous version, each from a clean context.
- **The workspace:** `iteration-N/<eval>/{with_skill,without_skill}/` holding `outputs/`, `timing.json` (`total_tokens`, `duration_ms`) and `grading.json` (`assertion_results` with `text`, `passed`, `evidence`, plus a `summary`), and one `benchmark.json` per iteration with mean, stddev and the delta.
- **A PASS needs quoted evidence.** A heading with one vague sentence under it fails "includes a summary".
- **Replace an assertion that passes in both arms,** and investigate one that fails in both. The ones that pass only with the skill show what the skill adds.
- **Compare versions blind** when both pass every assertion, and have a human read the outputs: assertions check only what someone thought to write down.
- **This lab keeps the file shapes and changes the layout.** `$LAB/evals.json` adds `outputs` and `context`, runs live in `runs/<variant>/<n>/`, `scripts/assert.py` writes the spec's `grading.json`, `scripts/summary.py` writes `benchmark.json`, and `NOSKILL=1` is the `without_skill` arm. What the spec leaves out is the spread: three runs of one variant differ by more than two variants do, and `SKILL.md`, "Reading the numbers", is where that is handled.
