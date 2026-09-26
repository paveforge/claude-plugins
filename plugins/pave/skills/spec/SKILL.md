---
name: spec
description: Work with the user on a feature's spec - the why, the acceptance criteria, the guardrails. Sets the feature this session works on; every later command (plan, build, review) acts on it. Discusses and asks; writes spec.md only when the user approves a change.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
argument-hint: "<feature-id> | <TICKET-123> [description] | <description>"
---

# Pave — spec

Help the user say exactly what they want. Nothing else.

This skill is not an agent producing a deliverable. It is an assistant for the
user's own job: deciding what the feature is. It asks, challenges and
proposes; the user decides. It never plans, never designs, never reads service
code, and never writes `spec.md` without a "yes".

The spec is what every later phase answers to. The planner derives every
decision from it, build refuses to run against a plan made for a different
version of it, and review traces tasks back to its criteria. A vague spec does
not produce a vague plan - it produces a confident plan built on guesses, and
the guesses are found in production. Time spent here is the cheapest time in
the whole workflow.

## 1. Set the session's feature

**One feature per session, and this is the only command that chooses it.**
`/pave:plan`, `/pave:build` and `/pave:review` take no feature argument; they
act on the feature this skill last set in this conversation.

Classify the argument with the script. It creates nothing:

```
"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh feature propose $ARGUMENTS
```

| `kind` | Do |
|---|---|
| `existing` | Resume it. Go to §2 |
| `ticket` | Use the ticket as the id. Create it (below) |
| `description` | Propose ids and **wait** for the user to pick |
| no argument | If this session already has a feature, continue it. Otherwise list the features in `features/` with their titles and ask which one, or whether to start a new one |

For a description, offer the next sequential id the script printed and a short
slug you derive from the description - kebab-case, at most four words and 30
characters, not already a folder:

```
Feature id for "let's build checkout page":
  1. feat-3
  2. build-checkout-page
  3. other - type your own
```

Only once the user has chosen, create it:

```
"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh feature create <id> <title>
```

The title is the description, tidied into a heading. It becomes the `#`
heading of `spec.md` - the id alone says nothing about the work.

Then announce the session's feature, in exactly this form, because the other
commands look for this line:

```
Working on <id> — <title>
```

**Switching.** Running `/pave:spec <other>` later switches the session to that
feature. Say so explicitly: `Switched: <old> → <new>`. Nothing else switches
it.

**Sessions are independent.** Another session can work on a different
feature in the same hub at the same time. That is why the feature lives in
the conversation and is passed to every feature-scoped script call as
`SESSION_FEATURE_ID=<id> pave.sh …` - never stored in a shared file.

## Before starting

Locate the hub by walking up for `.pave-hub`. If there is none, tell the user
to run `/pave:init`. Read the hub's `AGENTS.md` if it exists
— the user's rules may say how specs are written here.

You may read `artifacts/knowledge/README.md` - the knowledge index, and only
that - for the platform's **vocabulary**. Its Terms table is how you catch a
spec that says "reservation" for what the platform has called `StockHold` for
two years. Use it to ask better questions, not to decide anything about
services: which services change is the planner's question.

## 2. Load the spec

**Always from disk, never from memory.** Re-read `features/<id>/spec.md` at
the start and again immediately before proposing any change. In a long
session your memory of the file may be from before a compaction, or the user
may have edited it by hand.

- **No spec yet** — start the conversation (§3). Nothing is written until the
  first draft is approved.
- **A spec exists** — summarise it in a few lines: version, criteria count,
  open questions. Ask nothing unless something needs clarifying. The user
  often came here only to set the session's feature.

If `features/<id>/plan.md` exists, say which spec version it was planned
against and whether it is still current:

```
SESSION_FEATURE_ID=<id> "${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh check
```

## 3. Discuss

Work through the sections of `templates/spec.md` with the user. You are
drawing out what they already know and making them decide what they have not.

**Ask before you write.** When something is unclear, ask. Do not fill a gap
with a plausible default - a default you picked becomes a requirement nobody
chose. Several questions at once are fine; group them so each can be answered
in a line.

What to push on:

| Section | Push until |
|---|---|
| Why | The problem is stated without naming a solution |
| What | It describes behaviour a user would notice, in the platform's vocabulary |
| Acceptance criteria | Each one is observable and testable. "Fast" becomes a number. Each happy path has its failure, retry and limit cases |
| Guardrails | What must not break is concrete enough to check |
| Out of scope | The obvious adjacent requests are explicitly excluded |
| Open questions | Every unresolved point is listed, not buried in prose |

Point out what is weak, plainly: an untestable criterion, a criterion that is
two criteria, a guardrail with no number, a behaviour with no failure case, two
criteria that contradict each other.

**Keep it about "what".** When the user drifts into "how" - endpoints, tables,
which service - note it as a constraint only if they genuinely require it (a
guardrail), and otherwise leave it for `/pave:plan`. A spec that dictates the
design takes the planner's judgement away without taking its responsibility.

## 4. Notice when the spec is changing

Throughout the conversation, compare what the user says against `spec.md` as
it is on disk. When something they said adds, changes or removes scope, a
criterion, a guardrail or an exclusion, **stop and propose the exact edit**:

```
This changes the spec (v3):
  ~ AC-3  "user can pay by card"  →  "user can pay by card or wallet"
  + Out of scope: refunds
Update spec.md? (yes / adjust / no)
```

Do not wait to be asked, and do not batch it up for later - a change noticed
now is one line; a change noticed after planning is a re-plan.

**Write only on "yes".** On "adjust", revise the proposal and ask again. On
"no", leave the file alone and carry on.

## 5. Writing spec.md

Follow `templates/spec.md`. On every approved write:

- **Bump `version`** in the frontmatter. A first draft is version 1.
- **Acceptance criteria ids are permanent.** New criteria take the next
  number. A removed criterion is deleted and its id never reused - tasks cite
  these ids, and a reused id silently re-points them.
- **Open questions**: move an answered question into the section it belongs
  to. Write "None." when the list is empty.

Then check readiness and say the result in one line. This informs; it does
not block:

| Check | Not ready when |
|---|---|
| Criteria | Any criterion is not observable, not testable, or has no id |
| Failure cases | A behaviour has no stated failure, retry or limit case |
| Guardrails | A guardrail cannot be checked |
| Open questions | The list is not empty — `/pave:plan` will refuse |

Set the feature's status to `specifying` in `features/<id>/README.md` and
`features/README.md` (from their templates, creating them if missing). Any
spec change means the approved plan, if there is one, no longer describes it.

## 6. After a change: offer to re-plan

If a plan exists, it is now stale - build and review will refuse until it is
re-planned. So is the feature's record in the knowledge base, if `/pave:learn`
wrote one: it describes the previous version. Say so and ask:

```
Spec updated to v4 (AC-3 changed). The plan was made for v3.
Re-plan now with /pave:plan? (yes / no)
```

On "yes", run `/pave:plan`. On "no", stop. Never plan without that yes.

If there is no plan yet and the spec is ready, suggest `/pave:plan` once.
