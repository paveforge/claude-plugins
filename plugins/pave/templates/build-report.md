---
feature: <feature-id>
built_at: <timestamp>
spec_hash: <spec_hash from plan.md - the plan this build ran against>
verdict: <complete | partial | blocked>
tasks: { total: 0, done: 0, blocked: 0, failed: 0 }
needs_human: <true | false>
# The seal's hash of every task this run marked done: the text it was built from.
built:
  "<NN>": <task hash>
repos:
  - { service: <name>, repo: <path>, branch: <branch, or none - not under git>, commit: <made | asked, declined | not qualified - why | none> }
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

<Why it stopped instead of proceeding. For an interface: which tasks
provide or consume it and are at risk.>

**Decide:** <the actual choice, as options>
→ `<the exact command>`

---

## Landed

| Service | Repo | Branch | Tasks (in order) | Items |
|---|---|---|---|---|
| <service> | `<path>` | `<branch>` or — | <NN, NN, NN> | <done>/<total> |

## Not yet verified

Builders write code and run nothing: nothing above has been compiled, tested
or linted. `/pave:review` does that, service by service, once every task in a
service is built.

## Decisions taken

<!--
  Judgements the agents made within scope. No action needed - this is here
  so a person can skim for anything that looks wrong without being asked
  anything. Surfacing beats asking: it keeps the workflow moving while
  leaving the work reviewable.

  Only in-scope choices belong here. Anything that changed the plan or an
  interface was an escalation and belongs under Needs you.
-->

- **<service>** <What was chosen, and what it was chosen over.>

## Blocked

- `<task>` · <service> · <why, in one line> → see Needs you #<n>

## Skipped

- `<task>` · <done - frozen | obsolete, reverted by NN | depends on NN, not done>
