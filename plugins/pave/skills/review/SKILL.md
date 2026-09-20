---
name: review
description: Check that the build agents did exactly what the plan said. Reads each task document against the code, marks tasks that deviate as failed, and writes a report. Use on demand after /pave:build, before merging.
effort: high
argument-hint: "<feature slug>"
---

# Pave — review

Check the execution against the plan. Nothing else.

Build agents tick their own checkboxes and report their own success. This
phase is the independent check on those claims: **did the agent actually do
what the task document said, or did it claim work it did not do?**

## What this phase is not

It does not verify the feature works. It does not ask whether the design was
right, whether the approach was sound, or whether a case was missed.

That restraint is the point, and it makes the phase cheap. Two consequences
follow, and both are deliberate:

**A gap in the plan is not a review failure.** If the plan said A, B and C and
every agent faithfully did A, B and C, this review passes — even if the
feature needs D. A missing case is a planning problem, so it goes in the report
as a comment and **the user decides**, by running `/pave:design <slug>` to
re-plan and then `/pave:build` again. Never mark a task failed because you
disagree with the plan.

**Improvements never change status.** Note them, clearly marked non-blocking.
An agent that followed the plan exactly did its job, whatever you would have
written instead.

## Before starting

Locate the hub. Read `config.yaml`, then the feature's `spec.md`,
`architecture.md`, `contracts/` and every task document.

Spawn the `reviewer` agent with `model` set to `agents.reviewer.model`. It
reads the code and reports; you record the outcome. Review follows the config
exactly — unlike design, it does not upgrade to match a stronger session.

For a large feature, spawn one reviewer per service and do the contract
checking yourself once they return. Each reads only its own repo.

## 1. Claims against code

Give each reviewer its task documents, its repo path, and the frozen contracts
it touches. It takes every **ticked** item and finds it in the repo.
Not in the agent's report, not in the commit message — in the code.

- The entity exists, with the fields the task named
- The migration exists, with the constraints the task named
- The endpoint is routed and reachable, not just written
- The behaviour the task described is actually implemented, not stubbed
- A claimed test exists and asserts what the item said

Read the code. Run nothing — the builders already ran the commands and CI will
run them again. You are checking that the work is real, which is a reading
problem, not an execution one.

An item you cannot find is a deviation. An item that exists but does something
different from what the task specified is also a deviation.

## 2. Contracts against consumers

Still conformance, and the highest-value check here: the plan froze an
interface, so did both sides honour it?

- The producer implemented the frozen contract, not something adjacent
- Each consumer calls what the contract defines, and handles what it must
- Generated stubs match the contract file in every repo
- No contract was edited locally in a repo after gate 2 — the freeze is what
  let the services be built in parallel, and a local edit means other services
  were built against something that no longer matches

## 3. Record the outcome

**If every ticked item is real and the contracts hold**, the feature stays
`done`. Write the report with any non-blocking comments and stop.

**If anything deviates:**

1. **Uncheck** the specific items that were not real, in their task documents.
   This is what makes the re-run precise — the agent fixes three items rather
   than redoing a task of twenty.
2. Set those task documents to `status: failed`.
3. Set the feature to `failed`.
4. Leave conforming tasks untouched at `done`.

## 4. Report

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

## Comments (non-blocking)
- order-service: Checkout orchestration would read better split in two.
  Follows the plan exactly; noted only.
- The plan has no path for a payment authorised after the reservation
  expired. Not a deviation - the plan does not mention it. Re-plan with
  `/pave:design build-checkout` if you want it covered.
```

Per-task sections are not cosmetic. A re-run builder reads only its own
section, exactly as it reads only its own task document.

Then summarise in the session: what failed, in which service, and whether the
route forward is `/pave:build` (execution drift) or `/pave:design <slug>`
(the plan needs to change). Lead with what failed.
