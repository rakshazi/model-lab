# Maintaining a skill

For a pass over a skill that already works: a dedupe, a split into references, a rewrite, a merge of several skills into one, a port from a private skill to a public one. Measured on five such passes (a dedupe of an image-prompting skill, a restructure of this skill, a README-to-skill migration, three skills merged into one public skill, a project skill cut down to a wrapper over that one), each closed by cold audits. Every pass dropped something its author had already reviewed, and every audit ran against a green lint. Each bullet is the rule, then the run that taught it.

## Procedure

1. **Copy the tree before the first edit:** `cp -a <skill-dir> /tmp/<skill>-old`, to a path that does not exist yet (onto an existing directory `cp` nests the copy inside it), once per source skill in a merge. A pass that is already finished has no copy: take the last commit before it with `git -C <skill-dir> worktree add /tmp/<skill>-old <commit>`, and send the loss brief with `none` as its judged list. You MUST do this even in a git repo: `HEAD` lacks whatever was uncommitted when the pass began (one audit brief had to quote such a bullet by hand), and it stops being the old tree when the owner commits between two rounds, which happened in that same restructure. Keep the copy outside every skills directory. A backup left beside the live skill is still scanned, under a `name` that no longer matches its directory.
2. **For a merge or a port, a cold reviewer SHOULD attack the plan first.** One did, before any edit, and found that the source disagreed with itself (two scripts in one skill defaulted to different VAE files, and the reference being ported warned against one of them) and that nothing on the author's machine had ever run the public default path. Reconcile two copies before porting either: the one you would have picked can be the stale one.
3. **Write the moves file as you cut,** at `/tmp/<skill>-old.moves.md` (in a merge, named after the skill that survives): one row per removed fact, command, table row or file, written while the old text is still open.
   ```
   | old place | what it said | now |
   |---|---|---|
   | references/setup.md, "Ports" | the health check answers 200 while the queue is down | references/install.md, "Verify" |
   | SKILL.md, "Models" | the two private checkpoint file names | private: the host skill, "Inventory" |
   | references/batching.md, "Resume" | the state file that lets a batch resume | dropped: the owner asked, batches are short now |
   ```
   `now` is a file and section in the new tree or in a named neighbouring skill, `private: <where it stays>`, or `dropped: <what replaced it, or who asked>`. The file pays three times. A home that already existed adds no line to a diff, and the owner of the dedupe answered "it is covered" with: where is the new home for each removed thing? A compaction failed in the middle of the merge and the owner had to retype the scope from memory. And the `private` and `dropped` rows are the judged list in the loss brief. The auditor checks every one of them, because a status the author can type without proof is the escape hatch of `references/prompts.md`, "Rules that do not bind" (read when a ledger gains a status that ends a row).
4. **Run the mechanical checks after the last edit:** the skill's own lint and tests, `python3 -I scripts/dups.py <skill-dir>`, `--help` on every script, and `git status` for a file the tree now needs and git does not track. They clear the form. All of them passed on every tree in "What a pass loses".
5. **Then two audits, in parallel, each in a fresh context that saw none of the session, both read-only.** One compares the old tree with the new ("The loss audit"). One reads the new tree against this skill's rules ("The rules audit"). They read different things: in the merge the two reports had four findings in common and about twenty-five apart. A harness with no subagents runs each brief as its own new session. The auditors report and the author fixes: a second writer on files the first one just rewrote is the next loss.
6. **Fix, and reopen each cited line before the fix:** a finding is a claim. Add the restored rows to the moves file. Run the loss audit again when the fixes moved or rewrote text, because the fix is one more edit: the dedupe took three passes (the author's and two cold ones) and each found losses the others missed. Rerun the rules audit on the files a fix touched, for the same reason: in a split of this skill's own body, round 2 found its only WEAKENED row in a pointer that a round 1 fix had written, and five rules findings in text the fixes had added. Round 1 is the first cold loss audit. After each round append one line to the moves file, `round <n>: <n> LOST, <n> WEAKENED` (the verdicts the loss brief defines), so the count survives a compaction. Stop at the first round with no LOST or WEAKENED row; when the file holds a `round 3` line, the open rows go to the owner.
7. **Hand over the map.** The last message of the pass:
   ```
   maintenance: <skill>
   old tree: /tmp/<skill>-old
   moves: /tmp/<skill>-old.moves.md (<n> moved, <n> private, <n> dropped)
   loss audit: <n> rounds; last round <n> LOST, <n> WEAKENED
   rules audit: <n> findings, <n> fixed
   declined: <finding>: <why>
   open rows: <old place>: <what is still missing>
   not checked: <what no audit, test or run covered>
   ```
   The three counts come from `grep -c '| private:'`, `grep -c '| dropped:'` and the row total of the moves file. `declined` and `open rows` take one line per item, or the word `none`.

## The loss audit

Send each brief on this page with every slot replaced by a real value, and by the word `none` where there is nothing to name. Give one agent each of the files with the most removed lines in `diff -ru /tmp/<skill>-old <skill-dir>` and one agent the rest, and split dense prose at about 150 lines: a 300-line source went to two agents at line 152, and one agent handed the diffs of six files ran into truncated output and reread them in parts.

```
Loss audit of a skill restructure. Read-only: edit, create and delete nothing, commit nothing.

OLD tree: /tmp/<skill>-old
NEW tree: <skill-dir>
Your slice of OLD: <file, or file and line range>
A fact may now live in: <other files of NEW; a named neighbouring skill; code and data: a script's --help text, its defaults and error messages, a JSON asset>
Judged by the author. Check each row: does the named replacement or private home hold the fact, and does anything in NEW still use the dropped thing? Report every row that fails either check:
<the private and dropped rows of the moves file, or none>

Method:
1. Read your slice of OLD in full. A diff hides the paragraph around a removed line.
2. Split it into facts: a rule, a number or threshold, a command, a flag or default, a path, a quoted phrase, a condition or exception, a symptom, a cause, a fix, the run behind a rule.
3. Find each fact in NEW by its distinctive words and numbers, then read both versions. A literal match alone proves nothing, and a missing literal alone proves nothing.
4. In a troubleshooting row the symptom, the cause and the fix are three facts.
5. Verdict per fact: KEPT, WEAKENED (vaguer, a number or condition gone, or reachable only through a pointer whose target lacks it), LOST.
6. Open the target of every pointer in NEW and confirm it holds what the pointing sentence promises.
7. Run every script NEW names with --help and with its dry-run flag, and compare the result with what the docs say it does.

Report WEAKENED and LOST only:
| old place | old text, quoted | verdict | what is missing | nearest surviving text |
Then, apart: CONTRADICTIONS (a command the scripts reject, a path that does not exist, a default the docs and the code state differently, a file still named after its deletion) and CHANGED MEANING (a flag, key or path that kept its name and now does something else).
Last line: how many old passages you read.
```

For a merge or a port, add:

```
Sources: <each old tree>. The author's claim: ported <list>; left out on purpose <list>; kept private <list>.
Classify every script, reference, asset and rule of every source: published (where), private (why), or MISSED. An item on none of the three lists is a finding.
Leaks in NEW, quoted with file and line: <the private names, paths and ids to grep for>.
```

## The rules audit

```
Rules audit of a skill. Read-only: edit, create and delete nothing, commit nothing.

SKILL under audit: <skill-dir> (when the change is staged, read the staged files with git show :<path>)
RULES: <absolute path of this skill's directory>. Read SKILL.md in full, and the AGENTS.md of the skill under audit when it has one. Then every section of references/skill-format.md; in references/prompts.md "Output shape", "Input", "Examples and templates" and "Rules that do not bind"; in references/agentic.md "Scripts over prose" and "Gates and the loop surface".
What this pass changed: <what moved in, what moved out, which neighbouring skills now hold the rest>

Go rule group by rule group and answer PASS, FAIL or N/A with file:line: frontmatter and description; body budget (measure lines and bytes); body against references; one home per fact; instruction wording; examples and placeholders; scripts; gates and tests; evals and trigger queries.

A maintenance pass breaks a skill in these places, so also:
- Follow every copyable command and example as written. Does the file it opens exist after the step above it? Does the example obey the rule above it?
- Run every script with --help. Does each flag the docs use exist, and does each error name a fix?
- Run python3 -I <this skill's directory>/scripts/dups.py <skill-dir>. Then read <the neighbouring skills, or none> for the same tables and rules restated: quote both sides of each pair and say whether they agree.
- Read the evals and the trigger queries against what the skill does now. Which still assert the old behaviour? Which should-not-trigger queries now fall inside the scope?
- For each test and each lint, name one edit that breaks the skill and leaves the check green.

Report only what the files prove. A rule that does not apply gets one line saying why. Each finding: the rule, file:line, the quote, the smallest fix, ranked by how likely it is to break a run. Do not rewrite the skill.
```

## What a pass loses

- **A score sees only the facts its tasks reach for.** During the dedupe one run on the cut tree scored 6 of 6 without opening the reference that had lost the most, because its task never needed that file. The lab compares behaviour on the tasks it has. The loss audit compares text.
- **A read-when trigger goes when its table gets shorter.** The restructure of this skill kept every fact on its three agent pages and dropped five reopen-triggers from the body's table, so nothing sent the reader to them.
- **A merge keeps the rule and trims the receipt.** Merging two bullets cut "missed by every run", the two cells a sweep had accepted, and the model size and task behind a timing. A number that lost its condition still reads as evidence.
- **A fix outlives its symptom and its cause.** A failure table is a second door into its file: rows cut because the fix was stated above kept the cure and deleted how to recognise the failure. In the dedupe one cut row was the check for stacked quality adjectives, in the skill written to stop them, and another vanished by hand inside a block replace.
- **A rule changes sides.** "A pass can come from an edited repo" was a rule for reading results and came back as a rule for writing gates. The reader's symptom was gone from the section a reader opens.
- **A body line loses the pointer to its receipt.** The body kept the claim (perfect citations for twice the wall time) without its numbers and without a link to the bullet that held them.
- **Defaults live in the files you delete.** Three graph assets were removed as duplicates of a builder script. Each carried a sampler value of 1.15 and the model file names; the builder defaults to 4.0 and to the public models. 77 of 78 tracked scenes set no value, so every re-render would have differed from the shipped image with no line of prose removed, and the commands in two references lost their model files the same way.
- **A port carries the flag and loses the wiring.** In the merge the render script parsed `--ref` and `--negative` and never read them, overwrote a scene's own width and height, and uploaded a mask it then discarded. 27 tests passed: they called the builder functions and never `main`. The auditor found the first with `--dry-run` and the other two by reading `main`.
- **An item on no list.** The author listed what was ported and what was left out on purpose. A character-matting script was on neither list and was missed, with nine other publishable pieces: a LoRA wiring rule, an upload cache, the layout keys two shipped scripts accept and no page documents.
- **Pointers into deleted files survive outside the diff.** The reduced source skill still named two removed scripts, an error message sent the user to an example asset that never shipped, and notes inside tracked data files outside the skill named a deleted script. Grep the name of every deleted file across the project, the neighbouring skills and the script sources.
- **A deliberate drop can still have users.** A one-render branch was cut from a body as obsolete while a tracked data file still depended on it. The loss audit passed over it and the rules audit caught it, which is the case for running both.
- **Prose outlives the step it describes.** After an example checker was generalised, its page still told the reader to drop a state file the script no longer touched.
- **The new file is untracked.** Five rewritten scripts imported a helper module that `git status` showed as `??`. A commit of the tracked changes would have shipped a skill that fails on import.

## What a pass adds

- **An example older than the rule above it.** The only complete example in one body kept the previous style sentence and a truncated character description, under two copy-exactly rules. The lint checked one word of it and printed `ok`. The same rule for commands: `references/agentic.md`, "Scripts over prose" (read when a snippet sits above or below the rule it must obey).
- **A snippet whose steps no longer fit.** Three commands in a row: the third opened an output named after a prefix the second never set.
- **A placeholder in a new command.** `export VAR=...` is valid shell. It set the model name to three dots, the script took that as an override, and the dry run exited 0. The rule and its other runs: `references/prompts.md`, "Examples and templates" (read when a new command or example enters the body).
- **Evals and trigger queries with the old scope.** After a prompt-only skill learned to render, one eval still graded "claims no render happened" as the correct answer, and three should-not-trigger queries described the new feature.
- **A second table.** A new reference brought its own size table beside the one the body pointed at, and two values in the older table failed the new script's own check.
- **A duplicate across the skill boundary.** `scripts/dups.py` printed 0 pairs for a project skill whose layer table was a near copy of the neighbour's, and the two copies already disagreed on how two keys resolve. The tool reads one directory, so the neighbour needs a reader. Why two copies drift: `references/skill-format.md`, "Body and references" (read when a cut leaves a pointer to another skill).
- **A green lint read as one home.** One skill's lint compared backticked spans of five or more words, so a table of one-word file names could sit in two files unseen. Find out what a check cannot see before citing it as proof.
