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

Record exactly what the reviewers reported. Do not soften a finding, and do
not add one of your own — you did not read the code.

## 3. Report

Write `features/<slug>/artifacts/review-report.md`, **organised per task**:

```markdown
# Review — build-checkout
Reviewed 2026-09-20 · 4 tasks · 1 failed

## 02-payment-intent — FAILED
Claimed and not found:
- [ ] "Authorize transitions Pending -> Authorized"
      internal/domain/intent.go has the states but no transition; the
      usecase sets the field directly, bypassing validation.
- [ ] "Provider adapter behind an interface"
      stripe client is called directly from usecase/authorize.go:41.

## 01-stock-reservation — OK
## 03-order-checkout — OK
## 04-notification-confirm — OK

## Comments (non-blocking)
- order-service: Checkout orchestration would read better split in two.
  Follows the plan exactly; noted only.
- The plan has no path for a payment authorised after the reservation
  expired. Not a deviation - the plan does not mention it. Re-design with
  `/pave:design build-checkout` if you want it covered.
```

Per-task sections are not cosmetic. A re-run builder reads only its own
section, exactly as it reads only its own task document.

Then summarise in the session: what failed, in which service, and whether the
route forward is `/pave:build` (execution drift) or `/pave:design <slug>` (the
design needs to change). Lead with what failed.
