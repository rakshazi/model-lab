Grading task: {{N}} anonymous attempts (R1..R{{N}}) at one job in the repository at {{REPO}}. Grade each against a fixed rubric. You are blind to how the attempts were produced; keep it that way.

The job every attempt received:

> {{TASK}}

Each attempt could not ask questions and was told to put questions in its final reply.

Read:
- Rubric: {{RUBRIC}}. Grade exactly its items, 0 or 1 each.
- Attempts: {{BUNDLE}}/R1..R{{N}}/, each with reply.md (final reply), diff.patch (the working-tree change) and, when present, post.txt (build or test output) and check.txt (the lab checker's output).
- Ground truth: {{REPO}} is at the commit the attempts started from. Verify every path, symbol and line an attempt cites against it, and read the code each rubric item names before scoring it.

Do NOT open anything outside {{BUNDLE}}, {{RUBRIC}} and {{REPO}}. Do not edit any file except your output.

Also record, per attempt, any defect outside the rubric that would block a real review (hand-edited generated files, wrong semantics, a code path the change misses), with file:line.

Write {{OUT}}: one table `attempt | item scores | total | one-line verdict`, then per attempt a short list: each 0 with its evidence (file:line or a reply quote), each extra defect with file:line. Then 3 to 5 lines on what separates the best attempts from the worst. Reply with just the table.
