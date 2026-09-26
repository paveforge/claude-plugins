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

This command takes no feature argument. It acts on the feature `/pave:spec`
set in this conversation - the latest `Working on <id> — <title>` or
`Switched: … → <id>` line. If there is none, stop:

```
No feature in this session. Run /pave:spec <feature-id> first.
```

Say `Working on <id> — <title>` before continuing.

**Every feature-scoped `pave.sh` call names the session's feature in its
environment**, never as an argument: `SESSION_FEATURE_ID=<id> pave.sh …`.
The script refuses without it, and prints `feature: <id>` first - check that
line matches the feature you announced before trusting anything after it.
Another session may be working on a different feature in the same hub at
the same moment; the variable is what keeps each call on this session's.

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
standing in the hub.

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
| `reopened` | Yes, in **reconcile mode** (§4) |
| `failed` | Yes - only the items review unticked |
| `in-progress` | Yes - a previous run did not finish; resume it |
| `blocked` | Only once the blocker is resolved; otherwise report it again |
| `done` | No - skipped, listed as such |
| `obsolete` | Never. Its revert task removes its work |

**Task numbers given** - `/pave:build 03,07` builds exactly those. Commas are
the recommended separator; spaces and `03, 07` are accepted too, and leading
zeros are optional (`3` is `03`). An unknown number is rejected before
anything runs. The same table applies, with two refinements:

- **A named `done` task is not rebuilt.** It is frozen: it was built and
  verified. Skip it and say why - `03 skipped: done (a1b2c3d) - frozen`. If
  its `commit` is **not on the feature branch** (a reset, a lost commit), do
  not reset it silently - the commit may have been removed on purpose. Ask:

  ```
  03 is done, but a1b2c3d is not on feature/<id>.
  Reset 03 to pending and rebuild? (yes / no)
  ```
- **A named task whose `depends_on` is not `done` is refused**, naming the
  blocker. It is not built implicitly.

A named `obsolete` task is skipped: `03 is obsolete; its revert is 09`.

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
   task number. When `max_parallel` limits how many services run at once,
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
| `sequential` (default) | Services in that repo run one at a time |
| `worktree` | Each gets its own git worktree, same branch name; parallel |
| `shared-tree` | Parallel in one checkout. Concurrent git operations will collide eventually |

If a `depends_on` cycle would leave tasks waiting forever, stop and report it
- that is a plan defect, and waiting will not resolve it.

Set the feature to `building` before spawning anything.

## Pave writes in the hub. Builders write in the repos.

**This skill never touches a service repository.** It reads the hub, spawns
agents, collects what they report, and writes reports back into the hub.
Every change inside a repo - the branch, the contracts, the generated stubs,
the code, the reverts - is made by a `builder` agent in the repo it owns.
Parallel agents are safe because each one owns exactly one repo and nothing
else writes there.

## 4. Fan out

Spawn one `builder` per service group, passing the `model` and `effort`
printed by `"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh agent builder`. Never
substitute your own.

Give each agent, and nothing else:

- The absolute paths to its task documents, **in queue order**, each with its
  mode:

  | Mode | For | Meaning |
  |---|---|---|
  | `fresh` | `pending` | Nothing exists yet |
  | `resume` | `in-progress` | A previous run started it |
  | `reconcile` | `reopened` | Code for this task already exists at its recorded `commit`. Make that code match the document, changing only what does not; work the unticked items |
  | `fix` | `failed` | Fix only the items review unticked; give it the review report |
  | `revert` | `kind: revert` | Remove what the document names, and nothing else |

- Its required reading, by absolute path:
  1. the hub's `AGENTS.md` — the user's rules, if it exists
  2. `conventions/README.md`
  3. `conventions/<language>.md` — language from `workspace.yaml`
  4. `conventions/<service>.md` — if present, wins on conflict
  5. the repo's own `CLAUDE.md` — if `workspace.yaml` records one
- Its repo path, its `path` within that repo, its branch name, and its
  build/test/lint commands
- **The contracts it must land**: the frozen files from
  `features/<id>/contracts/` that its tasks name, and the service's `codegen`
  command. Say whether the branch and contracts already exist in this repo -
  they do after any earlier build of this feature. If a re-plan changed a
  contract, say which: the builder lands the new version.

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

Nothing is merged and no PR is opened unless the user asks.
