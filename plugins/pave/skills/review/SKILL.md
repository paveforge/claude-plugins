---
name: review
description: Check that the build agents did exactly what the plan said, for the session's feature. Refuses if the spec or plan changed since approval. Spawns one reviewer per task, marks tasks that deviate as failed, writes a report, and after a clean review offers to clean up reverted obsolete tasks. Use on demand after /pave:build, before merging.
---

# Pave — review

Compare the plan against the execution. Nothing else.

Build agents tick their own checkboxes and report their own success. This
phase is the independent check on those claims: **did each agent actually do
what its task document said, or did it claim work it did not do?**

This skill is an orchestrator. It spawns the reviewers, collects what they
found, and records the outcome. The comparing happens in the agents.

## What this phase is not

It does not verify the feature works. It does not ask whether the plan was
right or whether a case was missed.

That restraint is the point, and it is what makes the phase cheap. Two
consequences, both deliberate:

**A gap in the plan is not a review failure.** If the plan said A, B and C and
every agent did A, B and C, this passes — even if the feature needs D. A
missing case is a spec or planning problem, so it goes in the report as a
comment and **the user decides** - `/pave:spec` to change what the feature
must do, then `/pave:plan` and `/pave:build`. Never mark a task failed because
the plan was wrong.

**Improvements never change status.** Note them, clearly marked non-blocking.

## 0. The session's feature

This command takes no argument. It acts on the feature `/pave:spec` set in
this conversation - the latest `Working on <id> — <title>` or
`Switched: … → <id>` line. If there is none, stop:

```
No feature in this session. Run /pave:spec <feature-id> first.
```

Say `Working on <id> — <title>` before continuing.

## Before starting

```
"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh check <id>
```

**Anything but `ok` is a refusal.** Print what it reported and stop. Review
compares code against task documents; if the spec moved on or a task was
edited since the plan was approved, there is no approved document to compare
against - only `/pave:plan` can make one.

Locate the hub. Read the hub's config file (`config.yaml`, `config.yml` or `config.toml`), `workspace.yaml`, `features/<id>/`,
and the hub's own `AGENTS.md` and `CLAUDE.md` if it has either — the user's
rules for Pave's agents. Read them explicitly; they load by themselves only
when you happen to be standing in the hub. `AGENTS.md` wins where both exist
and disagree.

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
their revert task is, like any other `done` task.

## 1. Fan out, one reviewer per task

Spawn a `reviewer` for **every `done` task** in the feature, in parallel up to
`execution.max_parallel`, passing the `model` and `effort` printed by
`"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh agent reviewer`.

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
- The frozen contract files that task names
- The absolute path to the hub's `AGENTS.md` / `CLAUDE.md`, if either exists —
  the user's rules

Nothing else about the feature. The user's rules say how this team wants a
review done; they are not feature context. A reviewer still does not need the
spec, the architecture, the other task documents, or any notion of the feature
as a whole. It is answering one narrow question about one document, and keeping
its input narrow is what keeps it accurate.

Those rules can add something to look for. They cannot add something to fail
on: a finding that comes from them is a non-blocking improvement. `failed`
means an agent claimed work it did not do, and §2 unchecks the specific items
a reviewer names so a re-run builder fixes exactly those — a finding with no
ticked item behind it has nothing to uncheck, and would send a builder back
with nothing to act on.

Contracts decompose the same way. Both sides are checked against the same
frozen file, so if the producer conforms to it and the consumer conforms to
it, they conform to each other — no reviewer needs to see both.

## 2. Record the outcome

**If every reviewer reports clean**, leave the feature status as it is. A
clean review confirms what was built; it does not finish what was not. A
`blocked` or `building` feature stays that way — say so rather than letting a
green review read as a complete feature. Then go to §4.

**For each reviewer reporting a deviation:**

1. **Uncheck** the specific items it named, in that task document. This is
   what makes the re-run precise — the agent fixes three items rather than
   redoing a task of twenty.
2. Set that task document to `status: failed`.
3. Leave conforming tasks untouched at `done`.

If any task failed, set the feature to `failed`.

**If a reviewer returns nothing or errors**, that task is unreviewed, not
passed. Leave its status untouched, record it in the report, and say so in
your summary. Never let a missing result read as a clean one.

Record exactly what the reviewers reported. Do not soften a finding, and do
not add one of your own — you did not read the code.

## 3. Report

Write `features/<feature-id>/artifacts/review-report.md` from
`templates/review-report.md`.

Its structure exists to serve two readers at once:

- **A person** deciding whether this is mergeable reads the header and the
  Failed section, and stops.
- **A re-run builder** reads only its own subsection. It sees nothing else,
  exactly as it sees only its own task document — so every subsection names
  its task file and repo, and quotes the failed items verbatim.

Three rules the template encodes, all of them load-bearing:

**Quote items exactly** as they appear in the task document. The builder
matches on that text to find what to fix.

**Never omit the Not reviewed section** when a reviewer returned nothing or
errored. A task with no section reads as a pass, and silence must never mean
approval.

**Keep improvements in a section builders do not read.** A suggestion that
reaches a re-run agent becomes work it does, and the builder's authority is
the task document, not a reviewer's opinion.

Then summarise in the session: what failed, in which service, and the single
command to run next — `/pave:build` for execution drift, or `/pave:spec` when
what the feature must do needs to change. Lead with what failed.

## 4. Clean up reverted obsolete tasks

**Only after a successful review**: every `done` task reviewed, none failed,
none unreviewed. A failed or partial review never offers clean-up.

An obsolete task whose revert is `done` and has just passed review describes
nothing left in the code - and neither does its revert. Both are noise in the
task list. Look for them in the task frontmatter: `status: obsolete`, and a
`kind: revert` task whose `reverts:` names it. If there are any, ask:

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
"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh prune-obsoleted-tasks <id>
```

It removes each obsolete task and its reverts, and drops their entries from
`plan.md`'s task hashes. It leaves `spec_hash` and every other task's hash
untouched, and never lowers `next_task`, so numbers are still never reused.
It refuses - removing nothing - if any obsolete task's revert is not `done`.

Add what it printed to the review report under **Cleaned up**, then rewrite
`features/<id>/README.md` and `features/README.md` from the remaining task
frontmatter.
