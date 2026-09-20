# <Feature Name> - Architecture

<!--
  Every task is derived from this file, sometimes in a fresh context that
  remembers none of the reasoning behind it.

  Sufficiency test: could someone write every task document from this file
  alone, without asking a question? Write down the reasoning, not only the
  conclusion - a decision whose rationale is missing gets quietly re-derived,
  and the option you ruled out comes back.

  Use stable headings. Tasks cite architecture.md#<section> in derives_from,
  and an uncitable decision cannot be checked.
-->

## Approach
<The cross-service design in a few paragraphs.>

## Decisions

### <decision-anchor>
**Decided:** <what>
**Why:** <the reasoning>
**Rejected:** <the alternative, and why not - this is the line that stops a
task-writer quietly re-deriving the option you ruled out>

## Flow
<Step by step: which service does what, in order, and what it emits.>

| # | Service | Does | Emits |
|---|---|---|---|
| 1 | <service> | <action> | <event or response> |

## State ownership
| State | Owner | Who may read it |
|---|---|---|
| <thing> | <service> | <services> |

## Contracts
| Contract | Producer | Consumers | Compatibility |
|---|---|---|---|
| <name> | <service> | <services> | additive-only / versioned path / new topic |

## Unhappy paths

<!--
  Section 5 projects this into per-item failure behaviour in the tasks. If a
  case is not here, tasks cannot state it, and four builders will each invent
  something sensible in their own repo and none of them will agree.
-->

| When this fails | Retry | Compensates | Left inconsistent | Caller sees |
|---|---|---|---|---|
| <step> | <yes/no, how> | <what undoes it> | <what, for how long> | <what> |

## Assumptions
<Stated plainly, so gate 1 can challenge them.>

## Rollout considerations
<Anything that must ship in a particular order, and why.>
