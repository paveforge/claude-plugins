---
name: build
description: Execute an approved feature plan. Lands the frozen contracts in each repo, then fans out one agent per service to work through its task documents. Use after /pave:design has passed both gates.
effort: medium
argument-hint: "<feature slug>"
---

# Pave — build

Land the contracts, then fan out.

Build executes. It does not design. Every decision was made at the gates; this
phase turns frozen task documents into code.

## Before starting

Locate the hub. Read `config.yaml`, `workspace.yaml`, and
`features/<slug>/`. Refuse to start if:

- the feature's status is not `ready` — design has not passed gate 2
- any task document fails the readiness check in `/pave:design` §6

A task document that is not self-contained is a design defect. Send it back to
`/pave:design`. Do not fill the gap here.

## 1. Land the contracts

Sequential, driven from this session, before any agent spawns.

For each repo with a task in this feature:

1. Create the branch from `branch.pattern` in `config.yaml`, same name in every
   repo
2. Copy the frozen contract files from `features/<slug>/contracts/`
3. Run the service's `codegen` command from `workspace.yaml`
4. Commit the contract and its generated output — **nothing else**

This is what makes the fan-out safe. Agents start against real, compiling
interfaces instead of each generating their own from a spec and drifting apart.
If `contracts.land_before_fanout` is false, skip this and expect drift.

Stop if codegen fails. A broken stub multiplied across four parallel agents is
four broken builds.

## 2. Decide what to build

**If the feature is `failed`, build only the tasks marked `failed`.** Review
found those agents claimed work they had not done. Everything else stays as it
is — do not rebuild a task that passed.

Each re-run builder is given the review report alongside its task document.
Review has already unchecked the specific items that were not real, so the
agent fixes those rather than starting over.

Otherwise build every task in the feature.

## 3. Group tasks

Read the frontmatter of every task document. Group by `service`.

**Tasks targeting the same service run sequentially inside one agent.** Two
agents in one repo on one branch is a write conflict. Different services run in
parallel, up to `execution.max_parallel`.

If `execution.mode` is `sequential`, run every group one at a time.

When several services live in one repo — a monorepo, visible in
`workspace.yaml` where a repo lists more than one service — apply
`execution.monorepo_strategy`:

| Strategy | Behaviour |
|---|---|
| `sequential` (default) | Services in that repo run one at a time |
| `worktree` | Each gets its own git worktree, same branch name; parallel |
| `shared-tree` | Parallel in one checkout. Concurrent git operations will collide eventually |

Respect `depends_on`. Anything it blocks waits for its blocker to reach `done`.

## 4. Fan out

Spawn one `builder` agent per group, passing `agents.builder.model` from
`config.yaml` as the `model` argument. This is where the model choice actually
multiplies, and it is the user's to make — never substitute your own.

Give each agent, and nothing else:

- The absolute path to its task document
- Its required reading, resolved for its service:
  1. `conventions/README.md`
  2. `conventions/<language>.md` — language from `workspace.yaml`
  3. `conventions/<service>.md` — if present, wins on conflict
  4. the repo's own `CLAUDE.md` — if `workspace.yaml` records one
- Its repo path, its branch name, and its build/test/lint commands

Name the convention files explicitly as required reading. Do not paste their
contents — the agent reads the files, so an edit to `go.md` takes effect on the
next run with nothing to regenerate.

**Require a short report back.** Each agent writes its detail into its own task
document and returns a summary. Four agents returning full narratives into this
session will exhaust the context exactly when it is needed for integration.

## 5. Track

Task status lives in each task document's frontmatter: `pending` →
`in-progress` → `done`, or `blocked`. One agent owns one document; nothing else
writes to it.

After each agent returns, rewrite `features/<slug>/README.md` and
`features/README.md` from the task frontmatter and checkbox state. Never
hand-maintain either — they are derived, so they cannot drift.

## 6. Handle escalation

An agent that finds the contract wrong or insufficient must stop and report,
never improvise. Three siblings are building against that contract; a local fix
turns one contract error into four divergent guesses.

On escalation:

1. Mark the task `blocked` and say which contract and why
2. Let the other groups finish — they are unaffected unless they share the contract
3. Report to the user. A contract change is a **re-gate**: back to
   `/pave:design`, not a patch applied here

The same applies to anything ambiguous. If build agents routinely need to think
their way out of gaps, that is a defect in `design`, not a reason to raise the
build model.

## 7. Report

Write `features/<slug>/artifacts/build-report.md` from
`templates/build-report.md`.

It is triaged by **who must act**, not by service or chronology. Someone
should know from the first line whether they are needed, and be able to stop
there if they are not.

**Do not ask a question the report can state as a fact.** An in-scope
judgement an agent made — a library already in the repo, a name, an ordering
the task left open — goes under *Decisions taken*, where it can be skimmed.
Only what genuinely cannot be resolved without a person goes under *Needs
you*, and each of those carries the decision and the exact command.

Surfacing beats asking. It keeps the workflow moving while leaving the work
reviewable, which is the whole trade this phase is making.

**When nothing needs a person, say so in full** — "Nothing. All tasks
completed and no decisions were deferred." An empty section is the point of
the workflow; a blank heading reads as an oversight.

The Verification table is load-bearing rather than decoration: `/pave:review`
reads code and runs nothing, so this report is the only record that the
commands ever passed. A failing command means the task is not done — if a row
says fail and its task says done, stop and find out which is wrong.

## 8. Set status

Set the feature to `done` when every task is `done`, and `blocked` if any
agent escalated. Mention that `/pave:review` will check the work against the
plan — it is on demand, not required.

Nothing is merged and no PR is opened unless the user asks.
