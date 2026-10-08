---
feature: <feature-id>
reviewed_at: <timestamp>
spec_hash: <spec_hash from plan.md - the plan this review checked against>
verdict: <passed | failed>
tasks: { total: 0, passed: 0, failed: 0, unreviewed: 0 }
plan_gaps: 0          # gate 2 failures no single task explains
# The seal's hash of every task reviewed: the document each was checked against.
reviewed:
  "<NN>": <task hash>
---

# Review — <feature>

**<PASSED | FAILED>** · <n> tasks · <n> passed · <n> failed · <n> unreviewed

Gate 1 (tasks vs code): <passed | n failed> · Gate 2 (build, test, lint): <passed | n failed | waiting>

Next: `<the one command to run>`

<!--
  Written for a person deciding whether this is mergeable - they read the
  header, the Failed section, and stop. No builder reads this report: a
  re-run builder gets only its task document, where gate 1's failed items
  are unticked and every finding of both gates is written into Build notes. Each subsection
  names its task file, its repo, and quotes items verbatim, so the reader can
  find them.

  Record what the reviewers reported. Do not soften a finding and do not
  add one - the orchestrator did not read the code.
-->

---

## Failed

### <NN-task-slug> · <service>
`tasks/<NN-task-slug>.md` · `<repo path>`

**Missing** — claimed, not found in the code

> - [x] <the checkbox item, quoted exactly as written in the task>

<Where you looked and what was there instead, with file and line. Enough
that the fix does not start with a search.>

**Different** — exists, but not what the task specified

> - [x] <the checkbox item, quoted exactly>

<What it does instead, with file and line. This class matters more than
Missing: the code is there, so it is easy to skim past.>

**Interface** — `<element>` (<provides | consumes>)

<How this side diverges from the fields its task's Interfaces table gives.>

**Gate 2** — `<command>` failed in a file only this task names

> <file>:<line>: <the error, quoted>

---

## Plan gaps

<!-- Gate 2 failures no single task explains: a file no task names, or one
     several tasks name. Not a task failure - the plan did not cover it.
     The next command is /pave:plan, and it is the user's call. -->

### <service> · `<command>`
`<file>` · <unnamed | shared by NN, NN>

> <file>:<line>: <the error, quoted>

Suggested: `/pave:plan <scoped | full>` - <why, in one line>

## Gate 2

| Service | codegen | build | test | lint |
|---|---|---|---|---|
| <service> | <pass/fail/-> | <pass/fail> | <pass/fail (n tests)> | <pass/fail> |

<!-- A service waiting for gate 2 - an unfinished, failed or unreviewed task
     - is listed under Not reviewed, never here. An environment failure (no
     file named) is written here, with its output. -->

## Contracts

<!-- Only after a clean review of a finished feature: what
     `pave.sh contracts` printed, verbatim. -->

- copied: <service> `<path>` (<kind>)

---

## Passed

- `<NN-task-slug>` · <service> · <n> items verified, interfaces OK

## Cleaned up

<!-- Only after a successful review, and only if the user said yes. What
     `pave.sh prune-obsoleted-tasks` printed, verbatim. Omit when nothing was
     removed. -->

- pruned: `<NN-slug>.md` (obsolete) · `<NN-slug>.md` (revert)

## Not reviewed

- `<NN-task-slug>` · <service> · <why - reviewer returned nothing, errored,
  repo unavailable>. **This task was not checked.** Status unchanged.
- **<service>** · gate 2 waited · <which tasks are not done or did not pass
  gate 1>. **This service was not built or tested.**

<!--
  Never omit this section when it applies. A task with no section reads as
  a pass, and silence must never mean approval.
-->

---

## Comments — non-blocking

Not deviations. Nothing here fails a task, and no builder reads it.

- **<service>** <An improvement. The agent followed the plan; this is what
  you might do differently, noted only.>

- **Plan gap** <Something a reviewer noticed the plan does not cover. Not a
  deviation, because the plan never asked for it. If the spec requires it:
  `/pave:plan`. If the spec does not say: `/pave:spec` first - it is the
  user's decision.>

<!--
  This separation is load-bearing. Suggestions must never reach a builder:
  its authority is the task document, not a reviewer's opinion. The approved
  plan is the only thing that gets built; a suggestion worth doing goes
  through /pave:spec or /pave:plan.
-->
