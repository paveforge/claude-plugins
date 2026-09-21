---
name: review
description: Check that the build agents did exactly what the plan said. Spawns one reviewer per task to compare its task document against the code, marks tasks that deviate as failed, and writes a report. Use on demand after /pave:build, before merging.
effort: low
argument-hint: "<feature id>"
---

# Pave — review

Compare the plan against the execution. Nothing else.

Build agents tick their own checkboxes and report their own success. This
phase is the independent check on those claims: **did each agent actually do
what its task document said, or did it claim work it did not do?**

This skill is an orchestrator. It spawns the reviewers, collects what they
found, and records the outcome. The comparing happens in the agents.

## What this phase is not

It does not verify the feature works. It does not ask whether the design was
right or whether a case was missed.

That restraint is the point, and it is what makes the phase cheap. Two
consequences, both deliberate:

**A gap in the plan is not a review failure.** If the plan said A, B and C and
every agent did A, B and C, this passes — even if the feature needs D. A
missing case is a planning problem, so it goes in the report as a comment and
**the user decides**, by running `/pave:design <feature-id>` to re-design and then
`/pave:build`. Never mark a task failed because the plan was wrong.

**Improvements never change status.** Note them, clearly marked non-blocking.

## Before starting

Locate the hub. Read `config.yaml`, `workspace.yaml` and `features/<feature-id>/`.

| Feature status | Review |
|---|---|
| `done` | Yes. The normal case. |
| `failed` | Yes — a re-review after `/pave:build` fixed the deviations. |
| `blocked` | Yes, but only the tasks that are `done`. Say plainly that the feature is incomplete. |
| `building` | Yes, only the `done` tasks. A partial run leaves work unfinished, not wrong. |
| `ready`, `planning` | Refuse. Nothing has been built. |

**Only review tasks that are `done`.** A `pending` task has no code to compare
against, so a reviewer would report every item missing — which is true and
useless, and would mark as failed a task that was never attempted.

## 1. Fan out, one reviewer per task

Spawn a `reviewer` for **every `done` task** in the feature, in parallel up to
`execution.max_parallel`, passing `agents.reviewer.model`.

Re-review checks every `done` task again, including ones that passed last
time. That is deliberate, not waste: a re-run builder fixing three items may
have touched code another task depends on, and a task that passed against the
old code is not known to pass against the new.

Review follows `config.yaml` exactly. Unlike design, it does not upgrade to
match a stronger session — comparing a document to code is not a phase that
gets better with a stronger model, and there is one reviewer per task, so the
cost multiplies.

Give each reviewer:

- Its **one** task document
- The repo path for that task's service
- The frozen contract files that task names
- **Its agent rules**, pasted verbatim: the top-level `rules` from
  `config.yaml` followed by `agents.reviewer.rules`. Nothing if both are empty

Nothing else. Agent rules are how to review, not what this feature is — a
reviewer still does not need the spec, the architecture, the other task
documents, or any notion of the feature as a whole. It is answering one narrow
question about one document, and keeping its input narrow is what keeps it
accurate.

A rule can add something to look for. It cannot add something to fail on: a
rule-derived finding is a non-blocking improvement. `failed` means an agent
claimed work it did not do, and §2 unchecks the specific items a reviewer
names so a re-run builder fixes exactly those — a finding with no ticked item
behind it has nothing to uncheck, and would send a builder back with nothing
to act on.

Contracts decompose the same way. Both sides are checked against the same
frozen file, so if the producer conforms to it and the consumer conforms to
it, they conform to each other — no reviewer needs to see both.

## 2. Record the outcome

**If every reviewer reports clean**, leave the feature status as it is. A
clean review confirms what was built; it does not finish what was not. A
`blocked` or `building` feature stays that way — say so rather than letting a
green review read as a complete feature.

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
command to run next — `/pave:build <feature-id>` for execution drift, or
`/pave:design <feature-id>` when the design itself needs to change. Lead with what
failed.
