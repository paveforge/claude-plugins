---
name: review
description: Verify a built feature across every service it touched - contracts against consumers, tests, and rollout safety. Use after /pave:build, before merging anything.
effort: high
argument-hint: "<feature slug>"
---

# Pave — review

Check the seams. Four green services do not make a working feature.

Every agent verified its own work against its own task document. Nobody checked
that the pieces fit. That is this phase, and it is the last gate before the
feature is called done.

## Before starting

Locate the hub. Read `config.yaml`, `workspace.yaml`,
`features/<slug>/spec.md`, `architecture.md`, `contracts/` and every task
document.

Check the session model against `phases.review.model` and warn once if it is
lower. A contract mismatch that slips through costs more than the tokens saved
catching it.

## 1. Contracts against consumers

For each contract, compare what the producer actually implemented against what
each consumer actually calls. Read both sides in the repos — not the spec, and
not the generated stubs alone.

Look for:

- A producer that implemented something other than the frozen contract
- A consumer calling a field or method that does not exist, or ignoring one it must handle
- Generated stubs out of sync with the contract file, in any repo
- A contract edited locally in a repo. It was frozen at gate 2; a local edit is
  the failure mode the freeze exists to prevent, and it means other services
  are building against something that no longer matches
- Version or compatibility stance violated — a breaking change on an
  additive-only contract

## 2. Tasks against code

For each task document, verify the checked items are actually done in the repo.
An agent ticking its own homework is not evidence. Spot-check the concrete
claims — the migration exists, the endpoint is routed, the idempotency is real.

Report unchecked items and anything checked that you cannot find.

## 3. Tests

Run each touched service's `test` and `lint` from `workspace.yaml`. Report
failures per service with output. Never report a feature as reviewed on
untested code, and never paper over a failure as flaky.

## 4. Feature acceptance

Take the whole-feature acceptance criteria from `spec.md` and check them across
the services together. This is the part no single agent could have done and the
main reason this phase exists.

Where the criteria cannot be checked statically, say exactly what to run or
click, rather than assuming it works.

## 5. Rollout order

Deployment order is not implementation order. Work out what must ship first for
the system to stay working while it is partly deployed:

- Consumers of a new contract cannot ship before its producer
- A library must publish before consumers bump the pin — two phases, with a
  window where both versions are live
- A migration others read must land before the code that reads it
- Anything behind a flag: say what the flag is and what order it flips in

Call out any step that breaks if deployed alone.

## 6. Report

Write `features/<slug>/artifacts/review-report.md` and summarise in the
session. Lead with what is broken.

If everything passes, set the feature status to `done` and give the rollout
order. If not, list what is failing, in which service, and whether it is a code
fix (back to `/pave:build`) or a contract problem (back to `/pave:design`).

Report faithfully. A feature that passes review is one someone will merge.
