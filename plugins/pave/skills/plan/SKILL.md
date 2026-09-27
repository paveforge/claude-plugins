---
name: plan
description: Turn the session's spec into a plan - the services touched and untouched, the frozen contracts, and one self-contained task document per unit of work. Detects whether an existing plan still matches the spec and re-plans only what changed. One approval gate. Always runs the planner agent.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, SendMessage
---

# Pave — plan

Forecast what must change for the spec to become true, and cut it into tasks
that can be built, rebuilt and reviewed one at a time.

Everything downstream executes what is decided here; nothing downstream is
allowed to redesign it. And nothing here is allowed to decide what the spec
did not: every plan decision serves an acceptance criterion or a guardrail,
and a question about *what* goes back to the user through `/pave:spec`.

This skill orchestrates. It owns the conversation, the knowledge checks and
the gate. The `planner` agent does the thinking and writes the files.

## 0. The session's feature

This command takes no argument. It acts on the feature `/pave:spec` set in
this conversation - the latest `Working on <id> — <title>` or
`Switched: … → <id>` line. If there is none, or you cannot find it, stop:

```
No feature in this session. Run /pave:spec <feature-id> first.
```

Never guess the feature, and never take one from a file or another session.
Say `Working on <id> — <title>` before continuing.

**Every feature-scoped `pave.sh` call names the session's feature in its
environment**, never as an argument: `SESSION_FEATURE_ID=<id> pave.sh …`.
The script refuses without it, and prints `feature: <id>` first - check that
line matches the feature you announced before trusting anything after it.
Another session may be working on a different feature in the same hub at
the same moment; the variable is what keeps each call on this session's.

## Before starting

Locate the hub by walking up for `.pave-hub`. Read the hub's config file
(`config.yaml`, `config.yml` or `config.toml`) and `workspace.yaml`; if either
is missing, stop and tell the user to run `/pave:init`. If the config lacks a setting this command uses, stop: name the setting and
tell the user to run `/pave:init`. Never assume a value. Note the absolute
paths of the hub's `AGENTS.md`, if it exists - the planner
reads them.

## 1. Is a (re-)plan needed?

Read `features/<id>/spec.md` **from disk**, never from memory. Then:

```
SESSION_FEATURE_ID=<id> "${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh check
```

| Result | Meaning | Mode |
|---|---|---|
| `no-plan` / `unsealed` | Never planned, or a previous planning never reached approval | `initial` (or continue the unapproved `plan.md`) |
| `spec.md changed` | The spec moved on since approval | `replan` |
| `… edited outside /pave:plan` | Someone changed a task by hand | `replan` - the planner restores or re-derives it, and says which at the gate |
| `ok` | The plan is current | Say so: `Plan is current with spec v<n>.` and ask whether to re-plan anyway. Stop on "no" |

The user usually runs this command because they mean it; the check is cheap,
and it is what lets a fresh session plan without trusting anyone's memory.

**Refuse while the spec has open questions.** If its Open questions section
lists anything, stop and send the user to `/pave:spec`. A planner facing an
open question would have to answer it, and answering "what" is the user's
job.

Set the feature's status to `planning` in both roll-ups.

## 2. Knowledge — the service candidates

The planner decides the service map. It does it from the knowledge base, so
make sure the knowledge it will read exists and is current before spawning it.

**Initial plan.** Work out the candidate services, lightly:

| Stage | Load | Purpose |
|---|---|---|
| 1 | `artifacts/knowledge/README.md` — **only this** | Match the spec against capabilities, terms and events - including the On-demand section: feature records and current source findings |
| 2 | `knowledge/services/<candidate>/README.md` | Confirm or drop each candidate. ~50 lines each |

Stop there. The planner reads the deep files; opening them here reads each one
twice. Confirm against `consumes` edges in `workspace.yaml` - an import graph
will not tell you that checkout touches stock because reservations expire.

Report the candidates and ask:

```
"Build checkout page" appears to touch:
  order-service     orchestrates the flow                  confident
  stock-service     must reserve inventory                 confident
  notification-service  confirmation email                 likely
Missing anything?
```

A service the user adds here is worth more than three you inferred.

**Re-plan.** The services are already in `plan.md`'s service map. Only look
further if the spec change plainly reaches a capability none of them has.

**Staleness.** For every candidate, run `pave.sh stale <service>`. Spawn
`analyst` agents for anything missing or stale, with the `model` and `effort`
that `pave.sh agent analyst` prints and the required reading `/pave:analyse`
§3 gives them, and continue once they return. Say what you are doing in one
line; do not ask permission. Never plan against stale knowledge.

Knowledge is where the planner starts, not where it stops: it reads the code
its plan depends on, and asks for what it needs explained (§4). So do not
read code here. An `uncertain:` entry on a candidate goes into the brief as
it is; the planner resolves the ones its plan rests on.

## 3. Write the plan brief

Write `features/<id>/artifacts/plan-brief.md` - the hand-off, so the planner
never redoes discovery:

- The feature id, title, and absolute paths to `spec.md` and the feature folder
- The mode: `initial` or `replan`
- The confirmed candidate services, each with its role, your confidence, and
  its repo path and `path` from `workspace.yaml` - the planner reads the code
  there - and any the user added or removed
- **The exact knowledge files to read**, by absolute path - for each
  candidate, the `domain.md` of services likely to change and the
  `integration.md` of services at the seam
- Any **on-demand knowledge** the index matched: the record of an earlier
  feature in the same area (what it added, and the decisions it rests on), and
  any source finding that is `current` and answers a question this plan
  depends on. Never a stale finding or a stale record - and never this
  feature's own record: on a re-plan it describes the version being replaced,
  and `plan.md` is the source
- Every `uncertain:` entry on a candidate that bears on the spec
- **The branch** every task builds on: `branch.pattern` from the config, with
  `{feature-id}` replaced by the feature id
- Anything `check` reported
- Absolute paths to the hub's `AGENTS.md`, if it exists

Facts and paths, not contents. On a re-plan, update the existing brief rather
than rewriting it.

## 4. The planner

**Always the `planner` agent**, with the `model` and `effort` printed by:

```
"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh agent planner
```

Never substitute your own judgement for the configured model, in either
direction. If it fails, the hub's config has no usable entry for that agent: stop,
pass its message on, and never choose a model yourself.

**Resume before you respawn.** The first `/pave:plan` in a session spawns the
planner. Every later one in the same session - a re-plan after a spec change,
the task-writing stage after the gate - **resumes that same agent** with
`SendMessage`. It still holds the spec, the knowledge and its own reasoning,
so a re-plan costs only the difference. Spawn fresh only when resuming is not
possible: no `SendMessage` tool, or the agent is gone. A fresh planner
recovers from disk (`plan.md`, `artifacts/spec.approved.md`,
`artifacts/planner-context.md`), which is exactly why those files exist.

Give it only:

- the absolute path to `plan-brief.md`
- the absolute path to `writing-rules.md`, next to this skill
- which stage to produce: **stage 1** (the plan)

Do not read `writing-rules.md` yourself; the planner reads it.

### Questions from the planner

The planner returns questions it cannot answer from the spec, the knowledge
and its own look at the code. Each is marked as one of three kinds:

| Kind | Example | Do |
|---|---|---|
| **code** | how does stock-service expire holds today? | Not for the user. Have it answered from the code - below |
| **how** | synchronous call or event? which service owns the hold? | Ask the user. Resume the planner with the answer; it records the decision in `plan.md`, citing the criterion it serves |
| **what** | the answer would change behaviour, scope, a criterion or a guardrail | **Stop.** Tell the user: `This is a spec decision: <question>. Settle it with /pave:spec, then re-plan.` Do not answer it, and do not let the planner pick |

Every plan decision must be traceable to something written in the spec. A
"how" answer that quietly changes what the user gets is a "what" answer - if
in doubt, it goes to `/pave:spec`.

### Code questions

The planner looks up what it can itself - a definition, every place a value
appears. A **code question** is what it needs explained: how a flow or a
subsystem works. It hands those back rather than reading its way through
them on the strongest model; you have them answered by cheaper agents, and
the answers stay in the knowledge base for the next plan.

For each code question, exactly as `/pave:query` §2 does it:

- choose the finding's file, `artifacts/knowledge/on-demand/source/<slug>.md`,
  reusing a stale finding's file if it answers the same question
- spawn one `analyst` in question mode, with the `model` and `effort`
  `pave.sh agent analyst` prints, given the question verbatim, the services it
  concerns with their repo path, `path` and current commit, their knowledge
  files as a map, the finding's path, `templates/knowledge-finding.md`, and
  the hub's `AGENTS.md` if it exists

Run them in parallel, up to `execution.max_parallel`. Then rebuild the
index's On-demand section (`/pave:query` §3) and resume the planner with the
finding paths - and, for any question the analyst could not answer, what it
could not determine. Repeat until the planner returns no code questions. It
may raise them in stage 2 too; handle them the same way.

Say what you are doing in one line; do not ask the user. A code question the
code cannot answer is not a guess the planner may fill: it goes to the gate
as an open point.

### Nothing affected: re-seal instead of re-planning

On a re-plan, the planner may find the spec changed without affecting the
plan - a typo, a reworded sentence, a clarified example: no acceptance
criterion, guardrail, out-of-scope line or behaviour changed. It then returns
`verdict: unaffected` with the spec differences it compared, and writes
nothing.

This path is open **only** when `check` reported nothing but
`spec.md changed`. A task edited outside `/pave:plan` always needs the full
re-plan.

Show the differences and ask:

```
Spec changed (v3 → v4), but no criterion, guardrail or scope line did:
  ~ What: "checkout page" → "checkout flow"
  ~ AC-2: typo "recieve" → "receive"
The plan, contracts and tasks still hold. Re-seal without re-planning? (yes / no)
```

- **yes** — run `SESSION_FEATURE_ID=<id> "${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh seal`.
  It records the new spec hash and snapshot; task hashes are unchanged because
  no task was touched. Set the feature's status back to what its tasks say -
  the first match of: any task `blocked` → `blocked`; any task started or
  done but not all `done`/`obsolete` → `building`; every task
  `done`/`obsolete` → `done`; otherwise `ready` - and rewrite both roll-ups.
  Skip §5–§6. Mention that a feature record written by `/pave:learn` is now
  stale, and `/pave:learn` refreshes it without a rebuild if the feature is
  still reviewed and done.
- **no** — the user thinks the change matters. Continue with a full re-plan:
  resume the planner, tell it the user wants the plan revisited, and go on to
  the gate.

The judgement is the planner's and the decision is the user's; this skill
never re-seals on its own.

## 5. The gate — one approval

The planner's stage 1 writes `plan.md` (from `templates/plan.md`) and
`contracts/`. `plan.md` holds the whole plan in one place: the approach, the
service map, every decision with the criterion it serves, the contracts, and
the task table - every task in one line with its service, priority, size,
the criteria it satisfies and the tasks it reverts, plus what this revision
does to it.

Present a summary, not the files:

- the path of every file written, with one line on what it covers
- the service map: modify / read-only / untouched
- on a re-plan, what changed per task:

  ```
  03  reserve-hold        reopened   hold duration now 30 minutes (AC-3)
  05  hold-sweeper        obsolete   → 09 reverts it (high)
  06  wallet-payment      new        AC-7
  07  receipt-email       rewritten  not yet built
  ```
- the decisions, assumptions and "how" questions the user must rule on, and
  anything that cannot be reverted automatically (dropped data, a published
  event, a migration that already ran)

Do not read the files back into this session to present them. The user opens
the files; you open one only when they ask. Stop and wait.

**On approval the contracts are frozen.** From here they change only by
re-planning, never by an agent in a repo. A contract change on a re-plan
reopens every built task that provides or consumes it.

## 6. Task documents and readiness

After approval, resume the planner for **stage 2**: tell it the gate is
approved and which files the user changed, if any. It writes or rewrites the
task documents as a projection of the approved `plan.md` and runs the
readiness check in `writing-rules.md` §6.

The planner cannot delete files. Delete each task document it lists under
**Delete** - unbuilt tasks the plan dropped, which have nothing to revert -
and check each one really is unbuilt (`pending`, no `commit`) before removing
it. Anything else is a planner error: resume it rather than deleting.

A readiness failure is the planner's defect, not the user's decision: resume
it to fix the documents. Go back to the user only if a fix needs a decision -
and then the change goes through the gate again.

## 7. Seal

Once every task document passes readiness:

```
SESSION_FEATURE_ID=<id> "${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh seal
```

It records the spec's hash and every task document's hash in `plan.md`,
advances `next_task`, and snapshots the approved spec to
`artifacts/spec.approved.md` for the next re-plan to diff against. From here,
`/pave:build` and `/pave:review` run `pave.sh check` and refuse on any
mismatch.

**Seal after approval, never before.** A sealed plan is what build trusts.

## 8. Roll-ups

- `features/<id>/README.md` — from `templates/feature-README.md`, one row per
  task, built from task frontmatter
- `features/README.md` — from `templates/features-README.md`, one row per
  feature, status `ready`

Then say what to run next: `/pave:build`.
