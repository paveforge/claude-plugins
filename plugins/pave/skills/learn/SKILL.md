---
name: learn
description: Record the session's feature in the knowledge base once it has been built and passed review against its current plan - what it added, per service, linked back to its spec and plan. Refuses, saying why, if the feature is not finished. /pave:analyse never erases what it records.
allowed-tools: Bash, Read, Write, Glob, Grep
---

# Pave — learn

Turn a finished feature into knowledge the next feature can plan against.

The service analysis says what the code does; it does not say which feature
made it so, or why. After a feature ships, the next spec in the same area
needs to know what arrived, which decisions it rests on, and where the full
record is. This skill writes that down, once the feature has genuinely been
executed - and only then.

## 0. The session's feature

This command takes no argument. It acts on the feature `/pave:spec` set in
this conversation - the latest `Working on <id> — <title>` or
`Switched: … → <id>` line. If there is none, stop:

```
No feature in this session. Run /pave:spec <feature-id> first.
```

Say `Working on <id> — <title>` before continuing.

**Every feature-scoped `pave.sh` call names the session's feature in its
environment**, never as an argument: `SESSION_FEATURE_ID=<id> pave.sh …`.
The script prints `feature: <id>` first - check that line matches the feature
you announced before trusting anything after it.

## 1. Was it executed successfully?

Locate the hub. Every check below must pass. Collect every failure rather
than stopping at the first, then refuse with the full list and the command
that fixes each:

| Check | How | Fails → run |
|---|---|---|
| The plan is the one approved for this spec | `SESSION_FEATURE_ID=<id> "${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh check` prints `ok` | `/pave:plan` |
| Everything was built | Every task is `done`, or `obsolete` with its revert `done` | `/pave:build` |
| Every criterion was delivered | Every acceptance criterion in `spec.md` is in the `satisfies:` of at least one `done` build task | `/pave:plan` - the plan left it out |
| It passed review | `artifacts/review-report.md` exists with `verdict: passed` and `unreviewed: 0` | `/pave:review` |
| The review is of this build | The review's `reviewed_at` is later than the build report's `built_at` | `/pave:review` |

```
Not recorded - FEAT-8888 is not finished:
  task 07 is reopened                      → /pave:build
  review predates the last build           → /pave:review
```

Review checks that the code matches the plan; the criteria check is what
ties the plan back to the spec. Both are needed to call a feature executed.
This skill runs nothing and reads no service code: it trusts review for the
code and checks the paperwork for everything else.

## 2. Write the record

Write `artifacts/knowledge/on-demand/features/<id>.md` from
`templates/knowledge-feature.md`. If one exists - the feature was re-planned
and rebuilt since it was last recorded - replace it: the record describes the
feature as it now stands.

Set `spec_hash` to the `spec_hash` in `plan.md`. The check in §1 has just
proved it is the hash of the current `spec.md`, and it is what `pave.sh stale`
compares against: the moment the spec changes, this record is marked stale
and stops being used as an answer, until the feature is re-planned, rebuilt,
reviewed and learned again.

Build it from the feature folder only:

| From | Take |
|---|---|
| `spec.md` | Title, version, why and what, the acceptance criteria |
| task frontmatter | Per service: its `done` tasks; per criterion, the tasks that satisfy it; one line per task outcome |
| `plan.md` | The contracts, and the decisions a later feature is most likely to bump into - linked by anchor, not copied |
| `contracts/` | Events emitted and consumed |

`capabilities` are business phrases the feature added, the way someone would
ask for them in a later spec - the planner matches specs against them. Use the
platform's terms from the knowledge index.

Leave out obsolete tasks and the tasks that reverted them - the `Reverts`
column of `plan.md`'s task table names those: they describe work that no
longer exists.
Keep it within 100 lines. The record is an index into the feature folder, not
a copy of it.

## 3. Rebuild the index's On-demand section

Rebuild **only** the On-demand section of `artifacts/knowledge/README.md`,
from the frontmatter of every file under `on-demand/source/` and
`on-demand/features/`, with each file's state from
`"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh stale`. Leave every other section as
it is - those are `/pave:analyse`'s. If there is no index yet, write one from
`templates/knowledge-README.md` with only the On-demand section filled.

## 4. Report

One line: where the record was written, and the capabilities it added to the
index. Mention that `/pave:analyse` never rewrites or deletes it, and that it
goes stale when this feature's spec changes - `/pave:learn` again, after the
feature is rebuilt and reviewed, brings it back.
