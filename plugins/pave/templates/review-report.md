---
feature: <feature-id>
reviewed_at: <timestamp>
commit: <head sha of the feature branch when reviewed>
verdict: <passed | failed>
tasks: { total: 0, passed: 0, failed: 0, unreviewed: 0 }
---

# Review — <feature>

**<PASSED | FAILED>** · <n> tasks · <n> passed · <n> failed · <n> unreviewed

Next: `<the one command to run>`

<!--
  Two readers, and the structure serves both:

  A person deciding whether this is mergeable - reads the header, the
  Failed section, and stops.

  A re-run builder - reads ONLY its own subsection under Failed. It sees
  nothing else, exactly as it sees only its own task document. So each
  subsection names its task file, its repo, and quotes items verbatim.

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

## Not reviewed

- `<NN-task-slug>` · <service> · <why - reviewer returned nothing, errored,
  repo unavailable>. **This task was not checked.** Status unchanged.

<!--
  Never omit this section when it applies. A task with no section reads as
  a pass, and silence must never mean approval.
-->

---

## Comments — non-blocking

Not deviations. Nothing here fails a task, and no re-run agent reads this
section.

- **<service>** <An improvement. The agent followed the plan; this is what
  you might do differently, noted only.>

- **Plan gap** <Something the plan does not cover. Not a deviation, because
  the plan never asked for it. To cover it:
  `/pave:design <feature-id>` - re-designs the whole feature.>

<!--
  This separation is load-bearing. Suggestions must never reach a re-run
  builder: its authority is the task document, not a reviewer's opinion.
  Putting improvements in a section builders do not read is what keeps the
  approved plan the only thing that gets built.
-->
