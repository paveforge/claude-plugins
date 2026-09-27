---
service: <service-name>
feature: <feature-id>
priority: low              # low | high (reverts obsolete work) | critical (reserved)
status: pending            # pending | in-progress | done | reopened | failed | blocked | obsolete
depends_on: []
satisfies: []              # acceptance criteria from spec.md, e.g. [AC-1, AC-3]
derives_from:              # the plan this task projects. No source = invented.
  - plan.md#<section>
  - contracts/<file>
executed_hash:             # set by `pave.sh done` with status: done - the executed version's hash
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
  asking a question? The agent executing it has not seen the plan discussion
  and cannot read the other task documents.

  Everything above "## Build notes" is the planner's and is hashed at the plan
  gate; an edit anywhere else stops build and review. Builders change only the
  status and executed_hash (through `pave.sh done`), checkboxes, and the
  Build notes section.
-->

## Objective & Context
**Goal:** <1-2 sentences: what must be true here, and why>

## Out of scope
<!-- Behaviour as well as services. The most common autonomous failure is a
     correct change wrapped in three unrequested ones. -->
- Do not modify <service>, <service>. Agents are working in those repos now.
- Do not refactor <existing thing>; <why>.
- Do not upgrade dependencies or reformat files you did not otherwise change.

## Architecture & Data Contracts
**Data structures / schema:** <entities, migrations, DTOs>
**API contracts:** <path to the contract file>
**Contract status:** FROZEN at the plan gate. Do not edit the contract or its
generated files.

## Cross-Service Dependencies
| Direction | Service | Contract | Note |
|---|---|---|---|
| provides | <service> | <contract> | you own this |
| consumes | <service> | <contract> | stub landed; being built in parallel |

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
Build `<command>` · Test `<command>` · Lint `<command>`

**Done when:** <criteria visible by reading the repo. /pave:review runs
nothing, so anything that needs the app running cannot be checked here.>

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

## If the contract is wrong
Stop and report to the hub. Do not change the contract locally - other
services are building against it, and a local fix turns one contract error
into several divergent guesses.

## Build notes

<!-- The builder's section: what it did, decisions within scope, why it is
     blocked. Not hashed, not part of the specification. -->
