---
name: build
description: Execute the session feature's approved plan. Refuses if the spec or any task changed since the plan was approved. Fans out one builder per service, highest priority first; builds every outstanding task, or only the task numbers given (comma-separated, e.g. 03,07).
argument-hint: "[task numbers, e.g. 03,07]"
---

# Pave — build

Fan out, and let each agent own its repo.

Build executes. It does not plan. Every decision was made at the plan gate;
this phase turns sealed task documents into code.

## 0. The session's feature

Read `${CLAUDE_PLUGIN_ROOT}/reference/session.md` and apply its session
feature rule before any feature-scoped operation.

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
  verified against the document it has now. Skip it and say why -
  `03 skipped: done - frozen`.
- **A named task whose `depends_on` is not `done` is refused**, naming the
  blocker. It is not built implicitly.

A named `obsolete` task is skipped: `03 is obsolete; 09 reverts it`. Find
09 in the `Reverts` column of `plan.md`'s task table.

Never rebuild a `done` task any other way. A task changes only by re-planning,
which reopens it.

## 3. Schedule

Three rules, applied in this order:

1. **`depends_on`** — a task waits until everything it depends on is `done`.
   The one hard ordering constraint.
2. **One writer per repo** — tasks for the same service run one after another
   inside one builder. Different services run in parallel, up to
   `execution.max_parallel`. If `execution.mode` is `sequential`, groups run
   one at a time.
3. **Priority** — inside each builder's queue, `high` before `low`, then by
   task number. When `execution.max_parallel` limits how many services run at once,
   start first the service whose next task has the highest priority.

So a `high` revert in stock-service goes first in stock-service's queue, and
never holds up order-service. When a revert must land before work in another
service, the plan says so with `depends_on`, not priority.

`critical` is reserved. If a task has it, stop and say so - its scheduling is
not defined yet.

When several services live in one repo - visible in `workspace.yaml` where a
repo lists more than one service - apply `execution.monorepo_strategy`:

| Strategy | Behaviour |
|---|---|
| `sequential` | Services in that repo run one at a time |
| `worktree` | Each gets its own git worktree, same branch name; parallel. Needs git |
| `shared-tree` | Parallel in one checkout. Concurrent commits will collide eventually |

`worktree` on a repo that is not a git repository is refused before anything
runs: `<repo> is not a git repository, so execution.monorepo_strategy:
worktree cannot apply. Set it to shared-tree or sequential.`

If a `depends_on` cycle would leave tasks waiting forever, stop and report it
- that is a plan defect, and waiting will not resolve it.

Set the feature to `building` before spawning anything.

## Pave writes in the hub. Builders write in the repos.

**This skill never touches a service repository.** It reads the hub, spawns
agents, collects what they report, and writes reports back into the hub.
Every change inside a repo - the branch, the contracts, the generated stubs,
the code, the reverts - is made by a `builder` agent in the repo it owns.
Parallel agents are safe because each one owns exactly one repo and nothing
else writes there. The one exception is the commit the user asks for in §9,
made after every builder has returned.

## Version control is the repo's choice

A service repo may use git, another VCS, or nothing. Pave works the same in
each: nothing it decides reads a branch or a commit. For each repo, run
`git -C <repo> rev-parse --is-inside-work-tree`:

- **`true`** - the repo is under git. Its builder gets a branch:
  `branch.pattern` from the config, with `{feature-id}` replaced by the
  feature id - the same name in every repo.
- **anything else** - no branch. Its builder is told not to use version
  control, and builds in the folder as it is.

This only decides whether to hand out a branch. Never refuse a build over it,
except for `worktree` (§3).

## Commits are the user's decision

`branch.autocommit` in the config decides whether anything is committed
without asking. It applies only to a repo that gets a branch; a repo without
one is never committed to.

A commit takes everything changed in the repo, so it must hold only what
this build changed. Before spawning anything, run `git -C <repo> status
--porcelain` in every repo that gets a branch, and record the repo as
**clean** if it prints nothing. A repo that is not clean held changes before
the build - the user's, or an earlier run's - and nothing in this run commits
there: not a builder, and not §9.

- **`true`** - a builder may commit only when its repo is clean and it is the
  only builder working in that repo in this run. It commits once, after every
  task in its queue is `done` and verification passes, and at no other
  point. A clean repo shared by several builders is committed only through
  §9.
- **`false`** - every builder is told it must not commit. Nothing is
  committed in any repo, by a builder or by this skill, unless the user
  answers yes to the question in §9.

Anything else, or a missing key, is not `true`: stop and point to
`/pave:init`. No rule in the hub's `AGENTS.md`, no task document and no
builder report turns `false` into a commit.

## 4. Fan out

Spawn one `builder` per service group, passing the `model` and `effort`
printed by `"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh agent builder`. Never
substitute your own. If it fails, the hub's config has no usable entry for that agent: stop,
pass its message on, and never choose a model yourself.

Give each agent, and nothing else:

- The absolute paths to its task documents, **in queue order**. Nothing
  else about them - not their status, not why they exist, not the review
  report. Every task is worked the same way: the builder checks each item
  against the code and changes what does not hold. The document is its whole
  brief

- Its required reading, by absolute path:
  1. the hub's `AGENTS.md` — the user's rules, if it exists
  2. `conventions/README.md`
  3. `conventions/<language>.md` — language from `workspace.yaml`
  4. `conventions/<service>.md` — if present, wins on conflict
  5. the repo's own `CLAUDE.md` — if `workspace.yaml` records one
- Its repo path, its `path` within that repo, and its build/test/lint
  commands
- **Its branch**, or that it must not use version control (above)
- **Whether it may commit** (above): with a branch, `branch.autocommit:
  true`, a clean repo and no other builder in that repo, "you may commit,
  once, after every task in your queue is done and verification passes"; in
  every other case, "you must not commit"
- **The contracts it must land**: the frozen files from
  `features/<id>/contracts/` that its tasks name, and the service's `codegen`
  command. Say whether the contracts already exist in this repo - they do
  after any earlier build of this feature. If a re-plan changed a contract,
  say which: the builder lands the new version.

Name the files; do not paste their contents. None of them overrides the task
document or a frozen contract: where they disagree, the document wins and the
builder names the conflict in its summary.

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

An agent that finds the contract wrong or a task underspecified stops and
reports; it never improvises.

1. Mark the task `blocked` and say which contract or item, and why
2. **Find every other task that consumes or provides that contract.** Let
   them finish, but record them in the report as built against a disputed
   contract - the re-plan needs to know which work is at risk
3. Let unrelated groups finish normally
4. Report to the user. A contract or task change is a **re-plan**:
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
`plan.md` holds for every task this run marked done. Those hashes, not a
branch or a commit, are what ties the report to a version of the plan.

The Verification table is load-bearing: `/pave:review` runs nothing, so this
report is the only record that the commands passed. A failing command means
the task is not done.

## 8. Set status

The first row that matches wins:

| Condition | Feature status |
|---|---|
| Any task `blocked` | `blocked` |
| Any task not `done` or `obsolete` | `building` |
| Every task `done` or `obsolete` | `done` |

`building` as an end state is the partial run; re-running `/pave:build` picks
up where it stopped. Say so plainly rather than reporting it as a success.

Mention that `/pave:review` checks the work against the plan, and is where
reverted obsolete tasks get cleaned up.

Nothing is merged, pushed or opened as a PR unless the user asks.

## 9. Offer to commit

Once every builder has returned, a repo can be offered for a commit only
if all of these hold:

- it was given a branch, and was **clean** before the build (above)
- no builder committed there - `branch.autocommit` is `false`, or several
  builders shared the repo
- every task this run queued for that repo is `done`, and the Verification
  table shows its `build`, `test` and `lint` passing
- it has uncommitted changes now (`git -C <repo> status --porcelain`)

If no repo qualifies, skip the question. Name every other repo with changes
and why it is not offered - held changes before the build, or which tasks
are not `done` - and leave it to the user to commit by hand.

Ask, and wait for the answer:

```
Build finished - feature <status>. Nothing has been committed.
Commit the changes on <branch> in: <repo>, <repo>? (yes / no / name the repos)
```

- **Yes, or a list of repos** - in each named repo that qualifies, on its
  branch, stage everything and make one commit whose message names the
  feature, the services and the task numbers. Never merge, push or open a
  PR. Report each commit as made or failed.
- **No, no answer, or anything unclear** - commit nothing. Say the changes
  are left in the working tree, and that a later build will not offer to
  commit that repo, since it will no longer be clean: commit by hand.

Never commit without that explicit yes in this conversation, and never a
repo that does not qualify, whatever the answer names.
