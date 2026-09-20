---
feature: <feature-id>
built_at: <timestamp>
branch: <branch name, same in every repo>
verdict: <complete | partial | blocked>
tasks: { total: 0, done: 0, blocked: 0, failed: 0 }
needs_human: <true | false>
repos:
  - { service: <name>, repo: <path>, commit: <sha> }
---

# Build — <feature>

**<COMPLETE | PARTIAL | BLOCKED>** · <n> tasks · <n> done · <what, if anything, needs you>

<!--
  Triaged by who must act, not by service or chronology. Someone reading
  this should know within one line whether they are needed, and be able to
  stop there if they are not.

  The rule this template exists to enforce: do not ask a question the
  report can state as a fact. A judgement the agent made correctly and in
  scope is recorded under Decisions taken, where it can be skimmed. Only
  what genuinely cannot be resolved without a person goes under Needs you.
-->

---

## Needs you

<!--
  When empty, say so explicitly and in full:

    Nothing. All tasks completed and no decisions were deferred.

  An empty section is the point of the whole workflow. Make it visible
  rather than leaving a blank heading that reads as an oversight.
-->

### <n>. <The decision, stated as a decision>
`<task>` · <service> · task is `<blocked>`

<What the agent hit. Enough to decide here, without opening a file -
having to go and dig is the intervention this section exists to avoid.>

<Why it stopped instead of proceeding. For a contract: which services are
built against it and would break.>

**Decide:** <the actual choice, as options>
→ `<the exact command>`

---

## Landed

| Service | Repo | Commit | Tasks | Items |
|---|---|---|---|---|
| <service> | `<path>` | `<sha>` | <n> | <done>/<total> |

## Verification

<!--
  Load-bearing, not decoration. /pave:review reads code and runs nothing,
  so this is the only record that the commands ever passed.

  A failing command means the task is not done. If a row below says fail
  and its task says done, the report is wrong - go and find out which.
-->

| Service | build | test | lint |
|---|---|---|---|
| <service> | <pass/fail> | <pass/fail (n tests)> | <pass/fail> |

## Contracts landed

Copied from the hub by each builder into its own repo, as its first commit,
before any of its own work. Copied and never regenerated, so every service
built against the same bytes.

| Contract | Service | Codegen | Commit |
|---|---|---|---|
| `<contract file>` | <service> | <command> | `<sha>` |

## Decisions taken

<!--
  Judgements the agents made within scope. No action needed - this is here
  so a person can skim for anything that looks wrong without being asked
  anything. Surfacing beats asking: it keeps the workflow moving while
  leaving the work reviewable.

  Only in-scope choices belong here. Anything that changed the plan or the
  contract was an escalation and belongs under Needs you.
-->

- **<service>** <What was chosen, and what it was chosen over.>

## Blocked

- `<task>` · <service> · <why, in one line> → see Needs you #<n>
