---
name: build
description: Execute an approved feature plan. Lands the frozen contracts in each repo, then fans out one agent per service to work through its task documents. Use after /pave:design has passed both gates.
effort: medium
argument-hint: "<feature slug>"
---

# Pave — build

Branch, land the contracts, then fan out.

Build executes. It does not design. Every decision was made at the gates; this
phase turns frozen task documents into code.

## Before starting

Locate the hub. Read `config.yaml`, `workspace.yaml`, and `features/<slug>/`.

| Feature status | Build |
|---|---|
| `ready` | Everything. First run. |
| `failed` | Only the tasks marked `failed`. Review found claims that were not real. |
| `blocked` | Only tasks that are `blocked` or still `pending`, once the blocker is resolved. |
| `building` | A previous run did not finish — resume `pending` and `blocked` tasks. |
| `done` | Refuse. Nothing to do. Re-run review instead. |
| `planning` | Refuse. Design has not passed gate 2. |

Also refuse if any task document fails the readiness check in `/pave:design`
§6. A task document that is not self-contained is a design defect: send it
back to `/pave:design` rather than filling the gap here.

Set the feature to `building` before spawning anything. A run that dies
mid-way leaves a status that says so, instead of one that claims the feature
is still waiting to start.

## 1. Branches

Sequential, from this session, before anything else.

For each repo with a task in this feature, create the branch from
`branch.pattern` in `config.yaml` — the same name in every repo. **If it
already exists, check it out; do not recreate it.** A re-run after review lands
on branches that are already there and full of work.

This happens whether or not contracts are being landed. A feature can touch
four services without introducing a single new contract, and those agents still
need somewhere to commit.

## 2. Land the contracts

**Skip this entirely on a re-run.** Contracts froze at gate 1 and landed on the
first run; re-landing them would commit over work that is already built against
them. Only a fresh `ready` feature lands contracts.

For each repo with a task in this feature:

1. Copy the frozen contract files from `features/<slug>/contracts/`
2. Run the service's `codegen` command from `workspace.yaml`
3. Commit the contract and its generated output — **nothing else**

This is what makes the fan-out safe. Agents start against real, compiling
interfaces instead of each generating their own from a spec and drifting apart.
If `contracts.land_before_fanout` is false, skip it and expect drift.

Stop if codegen fails. A broken stub multiplied across four parallel agents is
four broken builds.

## 3. Decide what to build

Build exactly the tasks the entry table selected. **Never rebuild a task that
is `done`** — it has been verified, and rebuilding it risks undoing work while
the report claims otherwise.

On the `failed` path, give each builder the review report alongside its task
document. Review has already unchecked the specific items that were not real,
so the agent fixes those rather than starting over.

## 4. Group tasks

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
If a cycle would leave tasks waiting on each other forever, stop and report it
— that is a design defect, and waiting will not resolve it.

## 5. Fan out

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
- Its repo path, its `path` within that repo (a monorepo service does not
  live at the root), its branch name, and its build/test/lint commands

Name the convention files explicitly as required reading. Do not paste their
contents — the agent reads the files, so an edit to `go.md` takes effect on the
next run with nothing to regenerate.

**Require a short report back.** Each agent writes its detail into its own task
document and returns a summary. Four agents returning full narratives into this
session will exhaust the context exactly when it is needed for integration.

## 6. Track

Task status lives in each task document's frontmatter: `pending` →
`in-progress` → `done`, or `blocked`. One agent owns one document; nothing else
writes to it.

After each agent returns, rewrite `features/<slug>/README.md` and
`features/README.md` from the task frontmatter and checkbox state. Never
hand-maintain either — they are derived, so they cannot drift.

**If an agent returns nothing or errors, its task is unfinished, not done.**
Leave the status the agent left, record it in the report, and never infer
success from silence. A crashed builder that gets marked `done` sends unwritten
code to review, which will find nothing wrong with work that does not exist.

## 7. Handle escalation

An agent that finds the contract wrong or insufficient must stop and report,
never improvise. Three siblings are building against that contract; a local fix
turns one contract error into four divergent guesses.

On escalation:

1. Mark the task `blocked` and say which contract and why
2. **Find every other task that consumes or provides that contract.** They are
   building against something now known to be wrong. Let them finish — the work
   is on a branch and stopping mid-change leaves a worse state — but record them
   in the report as built against a disputed contract. Re-design needs to know
   which work is at risk, and the escalating agent could not see its siblings.
3. Let unrelated groups finish normally
4. Report to the user. A contract change is a **re-gate**: back to
   `/pave:design`, not a patch applied here

The same applies to anything ambiguous. If build agents routinely need to think
their way out of gaps, that is a defect in `design`, not a reason to raise the
build model.

## 8. Report

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

## 9. Set status

Derive it from the tasks, in this order — the first row that matches wins:

| Condition | Feature status |
|---|---|
| Any task `blocked` | `blocked` |
| Any task not `done` — `pending`, `in-progress`, `failed` | `building` |
| Every task `done` | `done` |

`building` as an end state is the partial run: some tasks finished, nothing
escalated, work remains. Re-running `/pave:build <slug>` picks up where it
stopped. Say so plainly rather than reporting a partial run as a success.

Never set `done` while a task is unfinished. It is the one status that tells
review, and you, that the feature is ready to look at.

Mention that `/pave:review` will check the work against the plan — it is on
demand, not required.

Nothing is merged and no PR is opened unless the user asks.
