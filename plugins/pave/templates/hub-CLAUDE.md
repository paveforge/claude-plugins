# <Hub name>

This is a Pave hub: the central command folder for cross-service feature work.
Specs, designs, contracts and task documents live here. The service repos are
reachable through `additionalDirectories` and are modified only by build agents.

## Layout

- `config.yaml` - team policy. Committed, shared.
- `workspace.yaml` - your services. Local, gitignored, source of truth.
  Hand edits here are never overwritten.
- `conventions/` - how code is written, by language and service. Yours to edit.
- `features/` - the durable record of what was decided.
- `artifacts/` - disposable. Delete anything here and it regenerates.
- `artifacts/knowledge/` - what each service does, written by `/pave:analyse`.
  Derived from code, so it is disposable; its index is what lets design load
  selectively instead of scanning everything.

## Workflow

| | When |
|---|---|
| `/pave:init` | Once, to create this hub |
| `/pave:add <folder>` | Whenever a service joins the platform |
| `/pave:analyse` | After adding services, then as they drift |
| `/pave:design` | Every new feature - two approval gates |
| `/pave:build` | Once the plan is approved |
| `/pave:review` | On demand |

`init` creates the hub. `add` records where a service is. `analyse` works out
what it is - language, build commands, contracts - and what it does. Design
needs all of it: without the last part it writes concrete tasks that contradict
code which already exists.

You never have to remember `analyse` - design spawns analysts itself for any
service whose knowledge is missing or stale. Running it explicitly refreshes
the whole platform at once.

## Models

Every agent's model comes from `config.yaml` and is enforced when it is
spawned. Design is the exception: it runs on the stronger of your session
model and the configured one, ranked by `model_ranking`. On sonnet with opus
configured you get opus; on fable you keep fable.

## Status

```
planning --> ready --> building --> done
                          |  ^            |
      an agent escalated  |  |            |  review found the plan
      a contract problem  v  |            |  was not followed
                       blocked            v
                          |            failed
                          |               |
       work still remains v               v
                       building <---------+  /pave:build re-runs
                                             only the failed tasks
```

| Status | Means |
|---|---|
| `planning` | Design is in progress |
| `ready` | Both gates passed; not built yet |
| `building` | Being built, or a run finished with work still to do |
| `done` | Every task built |
| `failed` | Review found claimed work that was not real |
| `blocked` | An agent escalated - usually a contract that cannot express what is needed |

`build` sets `done`. `review` is the independent check that the agents did
what the plan said, and sets `failed` if they did not.

A run that ends at `building` is the honest partial: some tasks finished,
nothing escalated, work remains. Re-running `/pave:build` picks it up.
`blocked` needs you - the build report says what the decision is.

Review checks execution against the plan, not whether the feature works. A
gap in the plan is not a review failure: it is a comment, and you decide
whether to re-design.

`/pave:design <feature-id>` re-designs the whole feature rather than patching the
gap. You cannot know that only one case was missed, and a patched design
produces tasks that are individually reasonable and collectively inconsistent.

## Rules

**Everything Pave writes lives in this hub.** Specs, designs, contracts, task
documents, knowledge and reports are all here. The only thing that changes a
service repo is a `builder` agent, in the one repo it owns — which is what
makes parallel agents safe, because no repo ever has two writers.

**Contracts are frozen at gate 1**, alongside the architecture they belong to.
An interface between two services is a design decision, not an implementation
detail. They change by re-running `/pave:design`, never by editing them in a
service repo. The freeze is what lets services be
built in parallel; a local edit breaks every service building against it.

**Task documents are self-contained.** An agent executing one has not seen the
design discussion and cannot read the others.

**Escalate, do not improvise.** A gap in a task document is a design defect.
Report it rather than guessing - the hub can see every service, the agent
cannot.

**The roll-up READMEs are generated.** `features/README.md` and each feature's
`README.md` are rewritten from task frontmatter. Do not hand-edit them.

## Your rules

Everything above is Pave's own doctrine. Everything below this line is yours.

**This file is given to every agent Pave runs**, by path, as required reading -
the builder writing code in a service repo, the reviewer checking it, the
analyst and the explorer reading a repo, the designer planning the feature. So
what you write here reaches the agent doing the work, not only the session that
spawned it. Skills read it explicitly rather than relying on it being loaded,
because they run from inside service repos as well as from here.

Name it `AGENTS.md` instead if you prefer; Pave reads either, and `AGENTS.md`
wins where both exist and say different things.

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
