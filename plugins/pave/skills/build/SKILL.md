---
name: build
description: Execute an approved feature plan. Fans out one agent per service, each landing the frozen contracts in its own repo and working through its task documents. Use after /pave:design has passed both gates.
effort: medium
argument-hint: "<feature id>"
---

# Pave — build

Fan out, and let each agent own its repo.

Build executes. It does not design. Every decision was made at the gates; this
phase turns frozen task documents into code.

## Before starting

Locate the hub. Read `config.yaml`, `workspace.yaml`, `features/<feature-id>/`,
and **the hub's own `AGENTS.md` and `CLAUDE.md`** — either, neither or both may
exist, and they hold the user's rules for Pave's agents. Read them explicitly
rather than assuming they are loaded: skills run from inside service repos as
well as from the hub, and a file loads by itself only when you happen to be
standing in the hub. Where both exist and disagree, `AGENTS.md` wins.

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

## Pave writes in the hub. Builders write in the repos.

**This skill never touches a service repository.** It reads the hub, spawns
agents, collects what they report, and writes reports back into the hub. Every
change inside a repo — the branch, the contracts, the generated stubs, the code
— is made by a `builder` agent in the repo it owns.

That is not tidiness. Parallel agents are safe because each one owns exactly
one repo and nothing else writes there. An orchestrator reaching in to commit
something is a second writer, and it is a second writer holding a git index
that four agents are about to use.

So contract landing, which used to happen here, happens in each builder before
it starts work.

## 1. Decide what to build

Build exactly the tasks the entry table selected. **Never rebuild a task that
is `done`** — it has been verified, and rebuilding it risks undoing work while
the report claims otherwise.

On the `failed` path, give each builder the review report alongside its task
document. Review has already unchecked the specific items that were not real,
so the agent fixes those rather than starting over.

## 2. Group tasks

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

If `contracts.land_contracts` is false, tell the builders not to land
contracts and expect drift.

## 3. Fan out

Spawn one `builder` agent per group, passing `agents.builder.model` from
`config.yaml` as the `model` argument. This is where the model choice actually
multiplies, and it is the user's to make — never substitute your own.

Give each agent, and nothing else:

- The absolute path to its task document
- Its required reading, resolved for its service, by absolute path:
  1. the hub's `AGENTS.md` / `CLAUDE.md` — the user's rules, if either exists
  2. `conventions/README.md`
  3. `conventions/<language>.md` — language from `workspace.yaml`
  4. `conventions/<service>.md` — if present, wins on conflict
  5. the repo's own `CLAUDE.md` — if `workspace.yaml` records one
- Its repo path, its `path` within that repo (a monorepo service does not
  live at the root), its branch name, and its build/test/lint commands
- **The contracts it must land**: the frozen files from
  `features/<feature-id>/contracts/` that its task names, and the service's `codegen`
  command from `workspace.yaml`. On a re-run say they are already landed.

Tell it whether this is a first run or a re-run. A re-run lands nothing and
creates no branch — both exist already, full of work.

Name the convention files explicitly as required reading. Do not paste their
contents — the agent reads the files, so an edit to `go.md` takes effect on the
next run with nothing to regenerate.

The same goes for the hub's rules file. **Give the absolute path** — a builder
runs in a service repo and will not find `AGENTS.md` by walking up from there.

The list is ordered from general to specific. The hub's rules apply to every
repo; the convention files narrow them to a language and then a service. None
of them overrides the task document or a frozen contract: where the user's
rules and the task document disagree, the document wins and the builder names
the conflict rather than picking silently. That is a line in its summary, not a
reason to block.

**Require a short report back.** Each agent writes its detail into its own task
document and returns a summary. Four agents returning full narratives into this
session will exhaust the context exactly when it is needed for integration.

## 4. Track

Task status lives in each task document's frontmatter: `pending` →
`in-progress` → `done`, or `blocked`. One agent owns one document; nothing else
writes to it.

After each agent returns, rewrite `features/<feature-id>/README.md` and
`features/README.md` from the task frontmatter and checkbox state. Never
hand-maintain either — they are derived, so they cannot drift.

**If an agent returns nothing or errors, its task is unfinished, not done.**
Leave the status the agent left, record it in the report, and never infer
success from silence. A crashed builder that gets marked `done` sends unwritten
code to review, which will find nothing wrong with work that does not exist.

## 5. Handle escalation

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

## 6. Report

Write `features/<feature-id>/artifacts/build-report.md` from
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

## 7. Set status

Derive it from the tasks, in this order — the first row that matches wins:

| Condition | Feature status |
|---|---|
| Any task `blocked` | `blocked` |
| Any task not `done` — `pending`, `in-progress`, `failed` | `building` |
| Every task `done` | `done` |

`building` as an end state is the partial run: some tasks finished, nothing
escalated, work remains. Re-running `/pave:build <feature-id>` picks up where it
stopped. Say so plainly rather than reporting a partial run as a success.

Never set `done` while a task is unfinished. It is the one status that tells
review, and you, that the feature is ready to look at.

Mention that `/pave:review` will check the work against the plan — it is on
demand, not required.

Nothing is merged and no PR is opened unless the user asks.
