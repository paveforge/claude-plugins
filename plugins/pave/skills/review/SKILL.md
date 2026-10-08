---
name: review
description: Check the session feature's build in two gates - first that each builder did exactly what its task said (one reviewer per task), then that every service builds, tests and lints. Refuses if the spec or plan changed since approval. Marks tasks that deviate, or whose own files fail, as failed; reports failures no task explains as a gap in the plan; after a clean review records the built contracts and offers to clean up reverted obsolete tasks. Use on demand after /pave:build, before merging.
---

# Pave — review

Check what was built, in two gates.

Builders only write code: they compile nothing, test nothing, and tick their
own checkboxes. This phase is the independent check:

1. **Gate 1 - did each builder do what its task said?** One cheap reviewer
   per task compares the task document with the code.
2. **Gate 2 - does it build?** Each service's own `codegen`, `build`, `test`
   and `lint`, run once all its tasks are written.

This skill is an orchestrator. It spawns the reviewers, runs the commands,
and records the outcome. The comparing happens in the agents; sorting a
failure to a task happens in a script.

## What this phase is not

It does not judge whether the plan was right. That restraint is what makes it
cheap, and it has two consequences:

**A gap in the plan is not a task failure.** If the plan said A, B and C and
every builder did A, B and C, gate 1 passes - even if the feature needs D.
When gate 2 then fails somewhere no task is responsible for, that is the same
gap showing up: it is reported as a plan gap, with a re-plan suggested, and
**the user decides**. Never mark a task failed because the plan was wrong.

**Improvements never change status.** Note them, clearly marked non-blocking.

## 0. The session's feature

Read `${CLAUDE_PLUGIN_ROOT}/reference/session.md` and apply its session
feature rule before continuing.

## Before starting

```
SESSION_FEATURE_ID=<id> "${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh check
```

**Anything but `ok` is a refusal.** Print what it reported and stop. Review
compares code against task documents; if the spec moved on or a task cannot
be vouched for, there is no approved document to compare against - only
`/pave:plan` can make one.

Locate the hub. Read the hub's config file (`config.yaml`, `config.yml` or `config.toml`), `workspace.yaml`, `features/<id>/`,
and the hub's own `AGENTS.md` if it has one — the user's
rules for Pave's agents. Read it explicitly; Claude Code loads it by itself
only when you happen to be standing in the hub. If the config lacks a setting this command uses, stop: name the setting and
tell the user to run `/pave:init`. Never assume a value.

| Feature status | Review |
|---|---|
| `done` | Yes. The normal case. |
| `failed` | Yes — a re-review after `/pave:build` fixed the deviations. |
| `blocked` | Yes, but only the tasks that are `done`. Say plainly that the feature is incomplete. |
| `building` | Yes, only the `done` tasks. A partial run leaves work unfinished, not wrong. |
| `ready`, `planning`, `specifying` | Refuse. Nothing has been built against the current plan. |

**Only review tasks that are `done`.** A `pending` or `reopened` task has no
code that claims to match its document yet, so a reviewer would report items
missing — which is true and useless. `obsolete` tasks are never reviewed:
the task that reverts one is, like any other `done` task.

## 1. Gate 1 - one reviewer per task

Spawn a `reviewer` for **every `done` task** in the feature, in parallel up to
`execution.max_parallel`, passing the `model` and `effort` printed by
`"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh agent reviewer`.
If it fails, the hub's config has no usable entry for that agent: stop,
pass its message on, and never choose a model yourself.

Re-review checks every `done` task again, including ones that passed last
time. That is deliberate, not waste: a re-run builder fixing three items may
have touched code another task depends on, and a task that passed against the
old code is not known to pass against the new.

Review follows the hub's config exactly, like every phase. It never upgrades to
match a stronger session — comparing a document to code is not a phase that
gets better with a stronger model, and there is one reviewer per task, so the
cost multiplies.

Give each reviewer:

- Its **one** task document
- The repo path for that task's service
- The absolute path to the hub's `AGENTS.md`, if it exists —
  the user's rules

Nothing else about the feature. The user's rules say how this team wants a
review done; they are not feature context. A reviewer does not need the
spec, the plan, the other task documents, or any notion of the feature as a
whole. It is answering one narrow question about one document, and keeping
its input narrow is what keeps it accurate.

Those rules can add something to look for. They cannot add something to fail
on: a finding that comes from them is a non-blocking improvement. `failed`
means a builder claimed work it did not do, and §2 unchecks the specific
items a reviewer names — a finding with no ticked item behind it has nothing
to uncheck, and would send a builder back with nothing to act on.

Interfaces decompose the same way. Producer and consumer tasks carry the same
fields, projected from one table in the plan, so if each side conforms to its
task, they conform to each other — no reviewer needs to see both.

## 2. Record gate 1

**For each reviewer reporting a deviation:**

1. **Uncheck** the specific items it named, in that task document. The task
   document is the builder's whole brief: an unticked item is how it learns
   that item does not hold.
2. **Write the findings into its `## Build notes`**, under a heading
   `### Review findings - <reviewed_at>`, after anything already there: for
   each item, the item quoted exactly, Missing or Different, and what the
   reviewer found instead with file and line - plus any interface finding.
   Only the deviations: improvements stay in the report. An unticked item
   says that it does not hold; the finding says where and why, so the
   re-run builder does not judge the same code the same way twice. Build
   notes are not hashed, so this does not trip `pave.sh check`.
3. Set that task document to `status: failed`.
4. Leave conforming tasks untouched at `done`.

**If a reviewer returns nothing or errors**, that task is unreviewed, not
passed. Leave its status untouched, record it in the report, and say so in
your summary. Never let a missing result read as a clean one.

Record exactly what the reviewers reported. Do not soften a finding, and do
not add one of your own — you did not read the code.

## 3. Gate 2 - build, test, lint

A service goes through gate 2 when **every** task of it that is not
`obsolete` is `done` and passed gate 1. A service with an unfinished, failed
or unreviewed task waits: its code is not all written yet, and its failures
would say nothing. Name each service that waits, and why.

For each service that goes through, run its commands from `workspace.yaml`,
in its `path`, in this order, skipping any it does not have:

1. `codegen` - builders run none, so generated code is brought up to date here
2. `build`
3. `test`
4. `lint`

Run every command even when an earlier one fails, and keep each one's output.
Services in different repos may run at the same time. Services that share a
repo (`repo_root` in `workspace.yaml`) run one after another: two builds in
one checkout overwrite each other's output.

**A failure is sorted, never judged.** For every failing command, take the
files its output names, and ask which tasks name them:

```
SESSION_FEATURE_ID=<id> "${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh attribute <service> <file>...
```

It prints one line per file: the file, then `task` with the one task that
names it, `shared` with the tasks that all name it, or `unnamed`.

| Failure | Means | Do |
|---|---|---|
| In a file exactly one task names (`task`) | That builder's slip - a typo, a missing import, a broken test | Write it into that task's Build notes under `### Review findings - <reviewed_at>`: the command, the file and line, and the error, quoted. Set the task `failed`. Leave its ticks - which item the error belongs to is the builder's to find |
| In a file no task names (`unnamed`), or several do (`shared`) | The plan did not cover it: a place it did not name, a consumer it missed, two tasks it did not order | A plan gap. No task fails. Report it, and suggest `/pave:plan` - `scoped` or `full` if the last plan was `quick` and the failure lies beyond what it touched. The user decides |
| Naming no file at all | The environment: a database not running, a tool not installed | Report it, with the output. No task fails. Fix it and run `/pave:review` again |

A command that fails with no output to sort is the environment row.

## 4. Status

Set the feature status from both gates:

| Condition | Feature status |
|---|---|
| Any task `failed` (either gate), or any plan-gap or environment failure in gate 2 | `failed` |
| Otherwise | Unchanged |

A clean review confirms what was built; it does not finish what was not. A
`blocked` or `building` feature stays that way — say so rather than letting a
green review read as a complete feature.

## 5. Record the contracts

**Only after a clean review of a finished feature**: every task `done` or
`obsolete`, every `done` task passed gate 1, every service passed gate 2,
none unreviewed.

```
SESSION_FEATURE_ID=<id> "${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh contracts
```

It copies the `producer` contract files `workspace.yaml` records for every
service the plan modifies into `features/<id>/artifacts/contracts/` - the
schemas as they were actually built and verified. Nothing is built against
the copy; it is a record, and running the command again rebuilds it. Add what
it printed to the report.

## 6. Report

Write `features/<feature-id>/artifacts/review-report.md` from
`templates/review-report.md`. Record `spec_hash` from `plan.md` and the hash
the seal (`artifacts/seal.yaml`) holds for every task reviewed: the report is
tied to the documents it checked, not to a branch or a commit.

It is written for **a person** deciding whether this is mergeable: they read
the header and the Failed section, and stop. No builder reads it - a re-run
builder gets only its task document, where gate 1's failed items are
unticked and every finding of both gates is written into Build notes.

Four rules the template encodes, all of them load-bearing:

**Quote items exactly** as they appear in the task document, and name the
task file and repo, so the reader can find each one.

**Never omit the Not reviewed section** when a reviewer returned nothing or
errored, or a service waited for gate 2. A task with no section reads as a
pass, and silence must never mean approval.

**Keep plan gaps apart from task failures.** A gate 2 failure no task
explains is the plan's, and the next command is `/pave:plan`, not
`/pave:build`.

**Keep improvements apart from failures.** A suggestion is not a deviation;
mixed in with the failed items, it reads as one. The builder's authority is
the task document, not a reviewer's opinion.

Then summarise in the session: what failed, in which service, and the single
command to run next — `/pave:build` for task failures, `/pave:plan` for a
plan gap, or `/pave:spec` when what the feature must do needs to change.
Lead with what failed. When both task failures and plan gaps exist, name
the plan gap first: a re-plan may rewrite the failed tasks anyway.

## 7. Clean up reverted obsolete tasks

**Only after a successful review**: every `done` task reviewed, none failed,
none unreviewed, gate 2 clean. A failed or partial review never offers
clean-up.

An obsolete task whose revert is `done` and has just passed review describes
nothing left in the code - and neither does its revert. Both are noise in the
task list. Find them from `status: obsolete` in the task frontmatter, and the
task that reverts each in the `Reverts` column of `plan.md`'s task table. If
there are any, ask:

```
Review passed. 2 obsolete tasks have been reverted:
  03  reserve-hold (obsolete)  → reverted by 09
  05  hold-sweeper (obsolete)  → reverted by 10
Clean up? Removes 03, 05 and their reverts 09, 10. (yes / no)
```

Offer only pairs whose revert is `done` and passed this review. If none
qualify, say nothing.

On **no**, change nothing; the question comes back after the next successful
review. On **yes**:

```
SESSION_FEATURE_ID=<id> "${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh prune-obsoleted-tasks
```

It removes each obsolete task and its reverts, and drops their entries from
the seal. It leaves `spec_hash` and every other task's hash untouched, and
never lowers `next_task`, so numbers are still never reused. It refuses -
removing nothing - if any obsolete task's revert is not `done`.

Add what it printed to the review report under **Cleaned up**, then rewrite
`features/<id>/README.md` and `features/README.md` from the remaining task
frontmatter.

## 8. Suggest recording it

After a successful review of a feature whose every task is `done`, say once
that `/pave:learn` records it in the knowledge base, so the next feature in
the same area plans against what this one added.
