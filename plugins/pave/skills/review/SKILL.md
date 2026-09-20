---
name: review
description: Check that the build agents did exactly what the plan said. Spawns one reviewer per task to compare its task document against the code, marks tasks that deviate as failed, and writes a report. Use on demand after /pave:build, before merging.
effort: low
argument-hint: "<feature slug>"
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
**the user decides**, by running `/pave:design <slug>` to re-design and then
`/pave:build`. Never mark a task failed because the plan was wrong.

**Improvements never change status.** Note them, clearly marked non-blocking.

## 1. Fan out, one reviewer per task

Spawn a `reviewer` for **every task** in the feature, in parallel up to
`execution.max_parallel`, passing `agents.reviewer.model`.

Review follows `config.yaml` exactly. Unlike design, it does not upgrade to
match a stronger session — comparing a document to code is not a phase that
gets better with a stronger model, and there is one reviewer per task, so the
cost multiplies.

Give each reviewer:

- Its **one** task document
- The repo path for that task's service
- The frozen contract files that task names

Nothing else. A reviewer does not need the spec, the architecture, the other
task documents, or any notion of the feature as a whole. It is answering one
narrow question about one document, and keeping its input narrow is what keeps
it accurate.

Contracts decompose the same way. Both sides are checked against the same
frozen file, so if the producer conforms to it and the consumer conforms to
it, they conform to each other — no reviewer needs to see both.

## 2. Record the outcome

**If every reviewer reports clean**, the feature stays `done`. Write the
report with any non-blocking comments and stop.

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

Write `features/<slug>/artifacts/review-report.md` from
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

Record what the reviewers reported. Do not soften a finding, and do not add
one of your own — you did not read the code.

Then summarise in the session: what failed, in which service, and the single
command to run next — `/pave:build <slug>` for execution drift, or
`/pave:design <slug>` when the design itself needs to change. Lead with what
failed.
