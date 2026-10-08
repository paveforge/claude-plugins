# <Hub name>

This is a Pave hub: the central command folder for cross-service feature work.
Specs, plans, task documents and reports live here. The service repos are
reachable through `additionalDirectories` and are modified only by build agents.

## Layout

- `config.yaml` - team policy. Committed, shared.
- `workspace.yaml` - your services. Local, gitignored, source of truth.
  Hand edits here are never overwritten.
- `conventions/` - how code is written, by language and service. Yours to edit.
- `features/` - the durable record of what was decided. In each feature,
  `spec.md` and `plan.md` are the only sources of truth; the task documents
  and `artifacts/` are rebuilt from them. Keeping only those two files per
  feature loses nothing that matters.
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
| `/pave:plan [quick\|scoped\|full]` | Once the spec has no open questions - one approval gate. On a re-plan, the level is yours: asked once, or given as the argument |
| `/pave:build [03,07]` | Once the plan is approved |
| `/pave:review` | On demand |
| `/pave:learn` | After a clean review - records the feature in the knowledge base |
| `/pave:query <question>` | Any time. Reads the code only when knowledge cannot answer, and saves the answer |

**One feature per session.** `/pave:spec` is the only command that takes a
feature; `plan`, `build` and `review` act on the feature it set.

`spec -> plan -> build -> review` is the only route. A change to what the
feature does starts at `/pave:spec`, never in a task.

You never have to remember `analyse` - `/pave:plan` spawns analysts itself for
any service whose knowledge is missing, and refreshes stale knowledge on a
`full` plan. A `quick` or `scoped` re-plan keeps stale knowledge and has the
planner check the code instead.

## Models

Every agent's model comes from `config.yaml` and is enforced when it is
spawned. `/pave:plan` always runs the `planner` agent on its configured model.
The planner decides everything build and review only execute, so the
strongest model you have is recommended for it.

## Status

```
specifying --> planning --> ready --> building --> done
     ^                                  |  ^         |
     |              an agent escalated  |  |         |  review found a deviation,
     |                                  v  |         |  or a build/test/lint failure
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
| `failed` | Review found claimed work that was not real, or a build, test or lint failure |
| `blocked` | An agent escalated - usually an interface that cannot express what is needed |

**A plan answers one version of the spec.** At its gate, `plan.md` records the
spec's hash, and the seal (`artifacts/seal.yaml`) every task document's hash.
`/pave:build` and `/pave:review` check both first and refuse on any mismatch -
a spec changed since, or a task edited by hand - until `/pave:plan` runs
again. With no seal - a fresh clone that kept only `spec.md` and `plan.md` -
`/pave:plan` rebuilds the tasks from the plan.

**Task documents describe the end state.** A re-plan rewrites them in place:
an unbuilt task is simply rewritten; a built one is **reopened**, and the
builder checks every item against the existing code and changes what does
not hold; one the spec no longer wants is marked **obsolete** and a new,
high-priority task removes its work. Task numbers only increase. After a
successful review, `/pave:review` offers to remove reverted obsolete tasks
together with the tasks that reverted them.

Review has two gates. First, each task against the code: did the builder do
what it said? Then each service's own build, test and lint - builders run
none of them. A failure in a file one task names sends that task back to
`/pave:build`. A failure no task explains is a gap in the plan, not a task
failure: review suggests a re-plan, and you decide.

## Rules

**Everything Pave writes lives in this hub.** Specs, plans, task documents,
knowledge and reports are all here. The only thing that changes a service
repo is a `builder` agent. Several may work in one repo at once: the plan
gives each task its own files and orders any two that share one, and
builders only write code - they run no build, test or lint that could
collide.

**Every change goes into the plan first.** Task documents are projections of
`plan.md` and are rebuilt from it; a change that lives only in a task is
lost. Never edit a task by hand - re-run `/pave:plan`.

**Your choices are final.** A level you give `/pave:plan`, or an answer you
give any question, is done as given. Pave recommends and warns; it does not
override you.

**The spec is the user's.** `/pave:spec` writes it only when you approve a
change. The planner never decides what the spec leaves open; it sends the
question back.

**Interfaces are frozen at the plan gate.** An interface between two services
is a planning decision, not an implementation detail. The plan fixes every
field, and both sides are built from it. Interfaces change by re-running
`/pave:plan`, never in a service repo. After a clean review, the built schema
files are copied into the feature's `artifacts/contracts/` as a record.

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

Nothing you write here relaxes the doctrine above. A builder still never
changes a frozen interface, never writes outside the files its task names,
and escalates rather than improvising. Where one of your rules and a task document disagree, the document
wins and the agent tells you so in its summary.

<Your rules. For example: never add a dependency that is not already in the
manifest - say so instead. Or: British English in comments and commit
messages.>
