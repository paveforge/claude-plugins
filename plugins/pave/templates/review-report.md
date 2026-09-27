---
feature: <feature-id>
reviewed_at: <timestamp>
spec_hash: <spec_hash from plan.md - the plan this review checked against>
verdict: <passed | failed>
tasks: { total: 0, passed: 0, failed: 0, unreviewed: 0 }
# plan.md's hash of every task reviewed: the document each was checked against.
reviewed:
  "<NN>": <task hash>
---

# Review — <feature>

**<PASSED | FAILED>** · <n> tasks · <n> passed · <n> failed · <n> unreviewed

Next: `<the one command to run>`

<!--
  Written for a person deciding whether this is mergeable - they read the
  header, the Failed section, and stop. No builder reads this report: a
  re-run builder gets only its task document, where the failed items are
  unticked. Each subsection names its task file, its repo, and quotes items
  verbatim, so the reader can find them.

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

**Contract** — `<contract file>` (<producer | consumer>)

<How this side diverges from the frozen contract. Say whether the generated
stubs match the contract file, so it is clear whether the implementation
diverged or the codegen is stale.>

---

## Passed

- `<NN-task-slug>` · <service> · <n> items verified, contract OK

## Cleaned up

<!-- Only after a successful review, and only if the user said yes. What
     `pave.sh prune-obsoleted-tasks` printed, verbatim. Omit when nothing was
     removed. -->

- pruned: `<NN-slug>.md` (obsolete) · `<NN-slug>.md` (revert)

## Not reviewed

- `<NN-task-slug>` · <service> · <why - reviewer returned nothing, errored,
  repo unavailable>. **This task was not checked.** Status unchanged.

<!--
  Never omit this section when it applies. A task with no section reads as
  a pass, and silence must never mean approval.
-->

---

## Comments — non-blocking

Not deviations. Nothing here fails a task, and no builder reads it.

- **<service>** <An improvement. The agent followed the plan; this is what
  you might do differently, noted only.>

- **Plan gap** <Something the plan does not cover. Not a deviation, because
  the plan never asked for it. If the spec requires it: `/pave:plan`. If the
  spec does not say: `/pave:spec` first - it is the user's decision.>

<!--
  This separation is load-bearing. Suggestions must never reach a builder:
  its authority is the task document, not a reviewer's opinion. The approved
  plan is the only thing that gets built; a suggestion worth doing goes
  through /pave:spec or /pave:plan.
-->
