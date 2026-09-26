---
feature: <feature-id>
spec_version: <n>        # the spec version this plan answers
next_task: 1             # the next task number to allocate. Numbers are never reused
# spec_hash and tasks: are written by `pave.sh seal` at the gate. Never by hand.
---

# <Feature Name> - Plan

<!--
  The forecast of what must change for spec.md to become true, and the index
  every task is cut from. Written by the planner, approved at the plan gate.

  Every decision here serves an acceptance criterion or a guardrail in
  spec.md, and says which. A decision that serves none is invented scope. A
  question whose answer would change behaviour, scope or a criterion is not a
  plan decision - it goes back to /pave:spec.

  Sufficiency test: could someone write every task document from this file
  and the contracts alone, without asking a question? Write down the reasoning,
  not only the conclusion.

  Use stable headings. Tasks cite plan.md#<section> in derives_from.
-->

## Approach
<The cross-service design in a few paragraphs.>

## Service map

<!-- Every service the feature was considered against. `untouched` is recorded
     on purpose: it says the service was ruled out, not forgotten, and it
     becomes the "Out of scope" line of every task. -->

| Service | State | Role / why |
|---|---|---|
| <service> | modify | <what changes here> |
| <service> | read-only | <what it calls or reads; must not change> |
| <service> | untouched | <why it was ruled out> |

## Decisions

### <decision-anchor>
**Serves:** AC-<n>, <guardrail>
**Decided:** <what>
**Why:** <the reasoning>
**Rejected:** <the alternative, and why not - the line that stops a
task-writer quietly re-deriving the option you ruled out>

## Flow
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
| `contracts/<file>` | <service> | <services> | additive-only / versioned path / new topic |

## Unhappy paths

<!-- Projected into per-item failure behaviour in the tasks. If a case is not
     here, tasks cannot state it, and every builder invents its own. -->

| When this fails | Retry | Compensates | Left inconsistent | Caller sees |
|---|---|---|---|---|
| <step> | <yes/no, how> | <what undoes it> | <what, for how long> | <what> |

## Assumptions
<About the system as it is, not about what the user wants. An assumption about
what the user wants is an open question for /pave:spec.>

## Tasks

<!-- One row per task. The whole plan is approved from this table, before the
     task documents are written. `Change` says what this plan revision does to
     the task; it is not stored in the task document, which only ever
     describes the end state. -->

| # | Task | Service | Kind | Priority | Size | Satisfies | Depends on | Change |
|---|---|---|---|---|---|---|---|---|
| 01 | <outcome> | <service> | build | low | S | AC-1 | - | new |
| 02 | <outcome> | <service> | revert | high | S | - | - | reverts 01 |

## Build order

<!-- Derived from the table: which tasks can run at once, and why anything
     waits. More than one wave means real depends_on edges; say why each one
     exists. -->

- Wave 1: <tasks> - parallel, one builder per service
