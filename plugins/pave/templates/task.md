---
service: <service-name>
feature: <feature-id>
priority: low              # low | high (reverts obsolete work) | critical (reserved)
status: pending            # pending | in-progress | done | reopened | failed | blocked | obsolete
depends_on: []
satisfies: []              # acceptance criteria from spec.md, e.g. [AC-1, AC-3]
derives_from:              # the plan this task projects. No source = invented.
  - plan.md#<section>
  - plan.md#interfaces
---

# <What this task achieves, as an outcome>

<!--
  One coherent unit of work in one service, that could be built and
  reviewed on its own. Split by natural seam - the API and the sweeper that expires its rows
  are two tasks. Never split by architectural layer.

  This document describes the END STATE, never a change from a previous
  version. When the spec changes, the planner rewrites it in place to say what
  must be true now. A builder reading it cannot tell - and must not need to
  know - what it said before.

  The test for every line below: could a competent stranger do this without
  asking a question? The agent executing it reads this document and nothing
  else - not plan.md, not the spec, not the other task documents.

  This document is a projection of plan.md and can be written again from it.
  Everything above "## Build notes" is the planner's and is hashed into the
  seal at the plan gate; an edit anywhere else stops build and review.
  Builders change only the status, checkboxes, and the Build notes section.
-->

## Objective & Context
**Goal:** <1-2 sentences: what must be true here, and why>

## Out of scope
<!-- Behaviour as well as services. The most common autonomous failure is a
     correct change wrapped in three unrequested ones. -->
- Do not modify <service>, <service>. Agents are working in those repos now.
- Do not refactor <existing thing>; <why>.
- Do not upgrade dependencies or reformat files you did not otherwise change.

## Architecture
**Data structures / schema:** <entities, migrations, DTOs>

## Interfaces
<!-- Every field this task provides to, or reads from, another service -
     exactly as the plan fixed it. The other side is built from the same
     values, possibly at the same time, so these are not yours to change.
     Write the schema file itself as an item under Tasks when this task
     provides it. -->
| Direction | Service | Element | Field | Type | Wire name / No. |
|---|---|---|---|---|---|
| provides | <consumer service> | `OrderResponse` (proto/order/v1/order.proto) | tracking_url | string, optional | `tracking_url` = 3 |
| consumes | <producer service> | <element> | <field> | <type> | <wire name> |

## Tasks

<!--
  An item is one focused change, stateable in one sentence without "and".
  Name the existing code it extends. Under any item that changes behaviour,
  nest what happens when it fails, repeats, or hits a boundary.

  Name every place in the code the behaviour lives, one item each - the
  builder changes only what the items name. What must be gone is an item
  too, stated as what must be true: "no route `/x` exists", "`y.go` does not
  exist". Anything that cannot be reversed was settled with the user at the
  plan gate; write the agreed handling here.
-->

- [ ] <Extend `Type` (path/to/file) with ...>
      - <replay / duplicate → what happens>
      - <invalid input → which error, and what is not left behind>
      - <boundary or already-applied case → what happens>
- [ ] <Migration `name` + the constraint that enforces the rule above>
- [ ] Test: <what it must prove, stated as a property>

## Verification
<!-- The builder runs none of these: it only writes code. /pave:review runs
     the service's codegen, build, test and lint once every task in it is
     built. -->
Build `<command>` · Test `<command>` · Lint `<command>`

**Done when:** <criteria visible by reading the repo, or in the output of the
commands above. Anything that needs the app running cannot be checked here.>

## If something is not specified

**This document is the complete specification. If it does not say, it was not
decided - so stop, do not infer.**

A missing error case or an unstated boundary has an answer that looks
obviously right from inside this repo, and picking it feels like doing the job
well. Nothing downstream will catch it: review checks only whether you did
what this document said, and if it said nothing, your invention passes and
ships unexamined.

Set `status: blocked`, say which item is underspecified and what this document
would need to say, and return.

## If an interface is wrong
Stop and report to the hub. Do not change a field locally - the other side is
being built from the same values, and a local fix turns one interface error
into several divergent guesses.

## Build notes

<!-- The builder's section: what it did, decisions within scope, why it is
     blocked. /pave:review adds its findings here when the task fails, under
     "### Review findings - <reviewed_at>". Not hashed, not part of the
     specification. -->
