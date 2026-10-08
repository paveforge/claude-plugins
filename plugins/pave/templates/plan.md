---
feature: <feature-id>
spec_version: <n>        # the spec version this plan answers
next_task: 1             # the next task number to allocate. Numbers are never reused
# spec_hash is written by `pave.sh seal` at the gate. Never by hand.
---

# <Feature Name> - Plan

<!--
  The forecast of what must change for spec.md to become true, and the index
  every task is cut from. Written by the planner, approved at the plan gate.

  This file and spec.md are the feature's only sources of truth. The task
  documents are projections of it and can be thrown away and written again
  from it, so every change goes here first - a change that lives only in a
  task is lost when the tasks are rebuilt.

  Every decision here serves an acceptance criterion or a guardrail in
  spec.md, and says which. A decision that serves none is invented scope. A
  question whose answer would change behaviour, scope or a criterion is not a
  plan decision - it goes back to /pave:spec.

  Sufficiency test: could someone write every task document from this file
  alone, and the code, without asking a question? Write down the reasoning,
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

## Interfaces

<!-- Every interface between services this feature adds or changes, exactly:
     what a producer task writes and a consumer task reads, field by field.
     Only what this feature defines - not the whole API. Tasks quote these
     rows into their items; builders never read this file, so a field that is
     not projected into a task is not built. A schema file it lives in is
     named by its path in the producer's repo, as workspace.yaml records it.
     After a clean review those files are copied into artifacts/contracts/
     as a record; nothing is built against the copy. -->

| Interface | Element | Field | Type | Wire name / No. | Producer | Consumers | Compatibility |
|---|---|---|---|---|---|---|---|
| `proto/order/v1/order.proto` | `OrderResponse` | tracking_url | string, optional | `tracking_url` = 3 | order-service | billing-service | additive-only |

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
     describes the end state. `Reverts` names the obsolete tasks whose work a
     task removes; /pave:review's clean-up reads it, and the task document
     never carries it. -->

| # | Task | Service | Priority | Size | Satisfies | Depends on | Reverts | Change |
|---|---|---|---|---|---|---|---|---|
| 01 | <outcome> | <service> | low | S | AC-1 | - | - | obsolete |
| 02 | <outcome> | <service> | high | S | - | - | 01 | new |

## Build order

<!-- Derived from the table. Build decides nothing: it runs every task whose
     `Depends on` are done, in parallel - in one service as well as across
     services. So `Depends on` is the only thing that keeps two tasks apart:
     give one wherever two tasks name the same place, or one needs the
     other's result, and say why each one exists. -->

- Wave 1: <tasks> - parallel
- Wave 2: <task> - after <task>: <both change internal/api/order.go>
