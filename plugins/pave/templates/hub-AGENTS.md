# <Hub name>

This is a Pave hub: the central command folder for cross-service feature work.
Specs, plans, contracts and task documents live here. The service repos are
reachable through `additionalDirectories` and are modified only by build agents.

## Layout

- `config.yaml` - team policy. Committed, shared.
- `workspace.yaml` - your services. Local, gitignored, source of truth.
  Hand edits here are never overwritten.
- `conventions/` - how code is written, by language and service. Yours to edit.
- `features/` - the durable record of what was decided.
- `artifacts/` - disposable. Delete anything here and it regenerates - except
  `artifacts/knowledge/on-demand/`, see below.
- `artifacts/knowledge/` - what each service does, written by `/pave:analyse`.
  Derived from code, so it is disposable; its index is what lets planning load
  selectively instead of scanning everything.
- `artifacts/knowledge/on-demand/` - knowledge nobody can regenerate by
  scanning: `source/` holds answers `/pave:query` read from the code, and
  `features/` holds what each finished feature added, recorded by
  `/pave:learn`. `/pave:analyse` never rewrites or deletes it, and nothing
  can regenerate it - do not delete it. If the hub is shared through git,
  commit it with the rest of the team's files.

## Workflow

| | When |
|---|---|
| `/pave:init` | Once, to create this hub |
| `/pave:add <folder>` | Whenever a service joins the platform |
| `/pave:analyse` | After adding services, then as they drift |
| `/pave:spec <feature>` | Every feature - sets the session's feature and works out what it must do |
| `/pave:plan` | Once the spec has no open questions - one approval gate |
| `/pave:build [03,07]` | Once the plan is approved |
| `/pave:review` | On demand |
| `/pave:learn` | After a clean review - records the feature in the knowledge base |
| `/pave:query <question>` | Any time. Reads the code only when knowledge cannot answer, and saves the answer |

**One feature per session.** `/pave:spec` is the only command that takes a
feature; `plan`, `build` and `review` act on the feature it set.

`spec -> plan -> build -> review` is the only route. A change to what the
feature does starts at `/pave:spec`, never in a task.

You never have to remember `analyse` - `/pave:plan` spawns analysts itself for
any service whose knowledge is missing or stale.

## Models

Every agent's model comes from `config.yaml` and is enforced when it is
spawned. `/pave:plan` always runs the `planner` agent on its configured model.

## Status

```
specifying --> planning --> ready --> building --> done
     ^                                  |  ^         |
     |              an agent escalated  |  |         |  review found the plan
     |                                  v  |         |  was not followed
     |                               blocked         v
     |                                             failed --> building
     +-- any spec change, at any point
```

| Status | Means |
|---|---|
| `specifying` | The spec changed and has not been planned since |
| `planning` | `/pave:plan` is in progress |
| `ready` | The plan passed its gate and is sealed; not built yet |
| `building` | Being built, or a run finished with work still to do |
| `done` | Every task built |
| `failed` | Review found claimed work that was not real |
| `blocked` | An agent escalated - usually a contract that cannot express what is needed |

**A plan answers one version of the spec.** At its gate, `plan.md` records the
spec's hash and every task document's hash. `/pave:build` and `/pave:review`
check both first and refuse on any mismatch - a spec changed since, or a task
edited by hand - until `/pave:plan` runs again.

**Task documents describe the end state.** A re-plan rewrites them in place:
an unbuilt task is simply rewritten; a built one is **reopened**, and the
builder checks every item against the existing code and changes what does
not hold; one the spec no longer wants is marked **obsolete** and a new,
high-priority task removes its work. Task numbers only increase. After a
successful review, `/pave:review` offers to remove reverted obsolete tasks
together with the tasks that reverted them.

Review checks execution against the plan, not whether the feature works. A
gap in the plan is not a review failure: it is a comment, and you decide
whether the spec needs to change.

## Rules

**Everything Pave writes lives in this hub.** Specs, plans, contracts, task
documents, knowledge and reports are all here. The only thing that changes a
service repo is a `builder` agent, in the one repo it owns — which is what
makes parallel agents safe, because no repo ever has two writers.

**The spec is the user's.** `/pave:spec` writes it only when you approve a
change. The planner never decides what the spec leaves open; it sends the
question back.

**Contracts are frozen at the plan gate.** An interface between two services
is a planning decision, not an implementation detail. They change by
re-running `/pave:plan`, never by editing them in a service repo.

**Task documents are self-contained.** An agent executing one has not seen the
plan and cannot read the others.

**Escalate, do not improvise.** A gap in a task document is a plan defect.
Report it rather than guessing - the hub can see every service, the agent
cannot.

**The roll-up READMEs are generated.** `features/README.md` and each feature's
`README.md` are rewritten from task frontmatter. Do not hand-edit them.

## Your rules

Everything above is Pave's own doctrine. Everything below this line is yours.

**This file is given to every agent Pave runs**, by path, as required reading -
the builder writing code in a service repo, the reviewer checking it, the
analyst and the explorer reading a repo, the planner planning the feature. So
what you write here reaches the agent doing the work, not only the session that
spawned it. Skills read it explicitly rather than relying on it being loaded,
because they run from inside service repos as well as from here.

The hub's `CLAUDE.md` holds only `@AGENTS.md`, so Claude Code loads this file
too when you work in the hub. Write your rules here, not there.

Keep this about what agents should do. **How code is written belongs in
`conventions/`** - builders are given those too, narrowed to a language and a
service, and `/pave:analyse` drafts them from your repos.

Nothing you write here relaxes the doctrine above. A builder still never edits
a frozen contract, never writes outside its own repo, and escalates rather than
improvising. Where one of your rules and a task document disagree, the document
wins and the agent tells you so in its summary.

<Your rules. For example: never add a dependency that is not already in the
manifest - say so instead. Or: British English in comments and commit
messages.>
