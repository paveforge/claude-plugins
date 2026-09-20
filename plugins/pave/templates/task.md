---
service: <service-name>
feature: <feature-slug>
status: pending            # pending | in-progress | done | blocked | failed
depends_on: []
branch: feature/<feature-slug>
derives_from:              # the design this task projects. No source = invented.
  - architecture.md#<section>
  - contracts/<file>
---

# <What this task achieves, as an outcome>

<!--
  One coherent unit of work in one service, that could be committed on its
  own. Split by natural seam - the API and the sweeper that expires its rows
  are two tasks. Never split by architectural layer.

  This document is a projection of the design, not a second act of it.
  Nothing here should be true for the first time; everything traces to a
  decision listed in derives_from.

  The test for every line below: could a competent stranger do this without
  asking a question? The agent executing it has not seen the design
  discussion and cannot read the other task documents.
-->

## Objective & Context
**Goal:** <1-2 sentences: what we are building here, and why>

## Out of scope
<!-- Behaviour as well as services. The most common autonomous failure is a
     correct change wrapped in three unrequested ones. -->
- Do not modify <service>, <service>. Agents are working in those repos now.
- Do not refactor <existing thing>; <why>.
- Do not upgrade dependencies or reformat files you did not otherwise change.

## Architecture & Data Contracts
**Data structures / schema:** <entities, migrations, DTOs>
**API contracts:** <path to the contract file>
**Contract status:** FROZEN at gate 2. Stubs generated and committed in <sha>.
Do not edit the contract or its generated files.

## Cross-Service Dependencies
| Direction | Service | Contract | Note |
|---|---|---|---|
| provides | <service> | <contract> | you own this |
| consumes | <service> | <contract> | stub landed; being built in parallel |

## Tasks

<!--
  An item is one focused change, stateable in one sentence without "and".
  Name the existing code it extends. Under any item that changes behaviour,
  nest what happens when it fails, repeats, or hits a boundary - that is
  where an agent would otherwise invent, and review cannot catch an invention
  the plan never ruled out.
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
