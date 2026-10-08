---
name: build
description: Execute the session feature's approved plan. Refuses if the spec or any task changed since the plan was approved. Runs the plan's depends_on graph - every task whose dependencies are done builds at once, in one service or many - with builders that only write code; builds every outstanding task, or only the task numbers given (comma-separated, e.g. 03,07).
argument-hint: "[task numbers, e.g. 03,07]"
---

# Pave — build

Fan out, and let each builder own its tasks.

Build executes. It does not plan and it decides nothing. Every decision -
including what may run at the same time - was made by the planner and sealed
at the plan gate; this phase turns task documents into code, in the order
their `depends_on` allow. Builders only write code: build, test and lint run
in `/pave:review`, once everything is built.

## 0. The session's feature

Read `${CLAUDE_PLUGIN_ROOT}/reference/session.md` and apply its session
feature rule before continuing.

## 1. The plan must be the one approved for this spec

```
SESSION_FEATURE_ID=<id> "${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh check
```

**Anything but `ok` is a refusal.** Print what it reported and stop:

```
spec.md changed since the plan was approved → run /pave:plan
```

No partial build, no "just the unaffected tasks". A stale plan may build
tasks the spec no longer wants, and a task edited by hand has skipped the
gate. This is a script check on purpose: it cannot be talked out of.

Then locate the hub and read the hub's config file (`config.yaml`,
`config.yml` or `config.toml`), `workspace.yaml`, the feature's task
documents, and **the hub's own `AGENTS.md`** - read it
explicitly; Claude Code loads it by itself only when you happen to be
standing in the hub. If the config lacks a setting this command uses, stop: name the setting and
tell the user to run `/pave:init`. Never assume a value.

| Feature status | Build |
|---|---|
| `ready`, `building`, `failed`, `blocked` | Yes - the outstanding tasks (§2) |
| `done` | Nothing outstanding. Say so, and suggest `/pave:review` |
| `specifying`, `planning` | Refuse. The plan has not passed its gate: `/pave:plan` |

## 2. Decide what to build

**No task numbers** - build every outstanding task:

| Task status | Build? |
|---|---|
| `pending` | Yes |
| `reopened` | Yes |
| `failed` | Yes |
| `in-progress` | Yes |
| `blocked` | Only once the blocker is resolved; otherwise report it again |
| `done` | No - skipped, listed as such. A `done` task a re-plan rewrote is reopened by `pave.sh seal`, so it is never `done` here |
| `obsolete` | Never. The task that reverts it removes its work |

**Task numbers given** - `/pave:build 03,07` builds exactly those. Commas are
the recommended separator; spaces and `03, 07` are accepted too, and leading
zeros are optional (`3` is `03`). An unknown number is rejected before
anything runs. The same table applies, with two refinements:

- **A named `done` task is not rebuilt.** It is frozen: it was built and
  reviewed against the document it has now. Skip it and say why -
  `03 skipped: done - frozen`.
- **A named task whose `depends_on` is not `done` is refused**, naming the
  blocker. It is not built implicitly.

A named `obsolete` task is skipped: `03 is obsolete; 09 reverts it`. Find
09 in the `Reverts` column of `plan.md`'s task table.

Never rebuild a `done` task any other way. A task changes only by re-planning,
which reopens it.

## 3. Schedule

The plan's `depends_on` graph is the schedule. Nothing else orders tasks, and
nothing here second-guesses it: the planner gave a `depends_on` to every pair
of tasks that must not run at the same time, and none to the rest.

1. **`depends_on`** — a task waits until everything it depends on is `done`.
   The one ordering constraint. Every task whose `depends_on` are done may
   run at once - two tasks in the same service as readily as two in
   different services.
2. **Chains** — tasks linked by `depends_on` within one service form a chain,
   built one after another by one builder, so it keeps its context. Every
   task that heads no chain and joins none is a chain of its own. A chain
   that waits on a task in another chain starts when that task is `done`.
3. **Limits** — up to `execution.max_parallel` builders run at once. If
   `execution.mode` is `sequential`, one at a time. When the limit holds
   ready chains back, start first the one whose next task has the highest
   priority, then the lowest task number.

Priority orders nothing else. A revert that must land before other work has
a `depends_on` in the plan.

`critical` is reserved. If a task has it, stop and say so - its scheduling is
not defined yet.

If a `depends_on` cycle would leave tasks waiting forever, stop and report it
- that is a plan defect, and waiting will not resolve it.

Set the feature to `building` before spawning anything.

## Pave writes in the hub. Builders write in the repos.

**This skill never edits a service repository.** It reads the hub, spawns
agents, collects what they report, and writes reports back into the hub.
Every change inside a repo - the branch, the code, the reverts - is made by
a `builder` agent. Several builders may work in one repo at once: the plan
keeps them on different files, and none of them runs a command there that
could collide with another's. The one exception is the commit in §9, made
by this skill after every builder has returned.

## Version control is the repo's choice

A service repo may use git, another VCS, or nothing. Pave works the same in
each: nothing it decides reads a branch or a commit. For each repo, run
`git -C <repo> rev-parse --is-inside-work-tree`:

- **`true`** - the repo is under git. Its builder gets a branch:
  `branch.pattern` from the config, with `{feature-id}` replaced by the
  feature id - the same name in every repo.
- **anything else** - no branch. Its builder is told not to use version
  control, and builds in the folder as it is.

This only decides whether to hand out a branch. Never refuse a build over it.

## Commits are the user's decision

Builders never commit. Committing is this skill's, once, at the end (§9),
and `branch.autocommit` in the config decides whether it asks first. It
applies only to a repo that gets a branch; a repo without one is never
committed to.

A commit takes everything changed in the repo, so it must hold only what
this build changed. Before spawning anything, run `git -C <repo> status
--porcelain` in every repo that gets a branch, and record the repo as
**clean** if it prints nothing. A repo that is not clean held changes before
the build - the user's, or an earlier run's - and nothing in this run commits
there.

- **`true`** - at the end of the build, commit every repo that qualifies
  (§9), without asking.
- **`false`** - nothing is committed unless the user answers yes to the
  question in §9.

Anything else, or a missing key, is not `true`: stop and point to
`/pave:init`. No rule in the hub's `AGENTS.md`, no task document and no
builder report turns `false` into a commit.

## 4. Fan out

Spawn one `builder` per chain (§3), passing the `model` and `effort`
printed by `"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh agent builder`. Never
substitute your own. If it fails, the hub's config has no usable entry for that agent: stop,
pass its message on, and never choose a model yourself.

Give each agent, and nothing else:

- The absolute paths to its chain's task documents, **in chain order**.
  Nothing else about them - not their status, not why they exist, not the review
  report. Every task is worked the same way: the builder checks each item
  against the code and changes what does not hold. The document is its whole
  brief; what review found in a failed task is already in its Build notes

- Its required reading, by absolute path:
  1. the hub's `AGENTS.md` — the user's rules, if it exists
  2. `conventions/README.md`
  3. `conventions/<language>.md` — language from `workspace.yaml`
  4. `conventions/<service>.md` — if present, wins on conflict
  5. the repo's own `CLAUDE.md` — if `workspace.yaml` records one
- Its repo path and its `path` within that repo
- **Its branch**, or that it must not use version control (above)
- That it must not commit, and must run nothing - no build, test, lint or
  codegen. Other builders may be working in the same repo

Name the files; do not paste their contents. None of them overrides the task
document: where they disagree, the document wins and the builder names the
conflict in its summary.

**Require a short report back.** Detail goes in each task's Build notes.

## 5. Track

Task status lives in each task document's frontmatter. One agent owns one
document while it runs; nothing else writes to it.

After each agent returns, rewrite `features/<id>/README.md` and
`features/README.md` from the task frontmatter. Never hand-maintain either.

**If an agent returns nothing or errors, its tasks are unfinished, not done.**
Leave the status the agent left, record it in the report, and never infer
success from silence.

## 6. Handle escalation

An agent that finds an interface wrong or a task underspecified stops and
reports; it never improvises.

1. Mark the task `blocked` and say which interface or item, and why
2. **Find every other task that consumes or provides that interface** - its
   Interfaces table names the element. Let them finish, but record them in
   the report as built against a disputed interface - the re-plan needs to
   know which work is at risk
3. Let unrelated chains finish normally
4. Report to the user. An interface or task change is a **re-plan**:
   `/pave:plan` (and `/pave:spec` first if the fix changes what the feature
   does), never a patch applied here

If builders routinely need to think their way out of gaps, that is a defect
in the plan, not a reason to raise the build model.

## 7. Report

Write `features/<id>/artifacts/build-report.md` from
`templates/build-report.md`, triaged by **who must act**. Do not ask a
question the report can state as a fact: an in-scope judgement goes under
*Decisions taken*; only what needs a person goes under *Needs you*, with the
decision and the exact command. When nothing needs a person, say so in full.

List skipped tasks - `done`, `obsolete`, or refused - with the reason.

Record what the build ran against: `spec_hash` from `plan.md`, and the hash
the seal (`artifacts/seal.yaml`) holds for every task this run marked done.
Those hashes, not a branch or a commit, are what ties the report to a
version of the plan.

Nothing was compiled or tested: builders run nothing. `/pave:review` runs
each service's `codegen`, `build`, `test` and `lint` once its tasks are
built. Say so in the report - a `done` task here means its items were
written, not that the code works yet.

## 8. Set status

The first row that matches wins:

| Condition | Feature status |
|---|---|
| Any task `blocked` | `blocked` |
| Any task not `done` or `obsolete` | `building` |
| Every task `done` or `obsolete` | `done` |

`building` as an end state is the partial run; re-running `/pave:build` picks
up where it stopped. Say so plainly rather than reporting it as a success.

Mention that `/pave:review` checks the work against the tasks, runs build,
test and lint, and is where reverted obsolete tasks get cleaned up.

Nothing is merged, pushed or opened as a PR unless the user asks.

## 9. Commit

Once every builder has returned, a repo qualifies for a commit only if all
of these hold:

- it was given a branch, and was **clean** before the build (above)
- every task this run queued in that repo is `done`
- it has uncommitted changes now (`git -C <repo> status --porcelain`)

Name every other repo with changes and why it does not qualify - held
changes before the build, or which tasks are not `done` - and leave it to
the user to commit by hand. If no repo qualifies, stop here.

The code has not been compiled or tested yet; review does that. Say so in
the line that reports or offers the commit.

**`branch.autocommit: true`** - in each repo that qualifies, on its branch,
stage everything and make one commit whose message names the feature, the
services and the task numbers. Report each commit as made or failed.

**`branch.autocommit: false`** - ask, and wait for the answer:

```
Build finished - feature <status>. Nothing has been committed, and nothing
has been compiled or tested yet (/pave:review does that).
Commit the changes on <branch> in: <repo>, <repo>? (yes / no / name the repos)
```

- **Yes, or a list of repos** - commit each named repo that qualifies, as
  above.
- **No, no answer, or anything unclear** - commit nothing. Say the changes
  are left in the working tree, and that a later build will not commit that
  repo, since it will no longer be clean: commit by hand.

Never merge, push or open a PR. Never commit with `false` without that
explicit yes in this conversation, and never a repo that does not qualify,
whatever the answer names.
