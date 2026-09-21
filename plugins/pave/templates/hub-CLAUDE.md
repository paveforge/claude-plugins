# <Hub name>

This is a Pave hub: the central command folder for cross-service feature work.
Specs, designs, contracts and task documents live here. The service repos are
reachable through `additionalDirectories` and are modified only by build agents.

## Layout

- `config.yaml` - team policy and your agent rules. Committed, shared.
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

## Agent rules

`config.yaml` carries a top-level `rules` list and a `rules` list per agent.
They are free text, handed to an agent verbatim every time it is spawned: the
top-level ones first, then the agent's own. Absent or empty, nothing is passed
and nothing is mentioned.

Three places can instruct an agent, and they do not overlap:

| Where | What belongs there |
|---|---|
| this file | Pave's workflow doctrine - gates, contracts, escalation. Not yours to relax. |
| `config.yaml` `rules:` | Your standing instructions to the agents. |
| `conventions/` | How code is written, by language and service. |

**Order of authority**, strongest first: the agent's own definition, then the
task document and the frozen contracts, then agent rules, then the conventions
and the repo's own `CLAUDE.md`.

So a rule beats a convention - you wrote it deliberately, the conventions were
drafted from existing code. A rule loses to a task document, and the agent
names the conflict in a line rather than picking silently. That is a report,
not an escalation: `blocked` stays for contract defects and underspecified
tasks.

A `rules` list under a name that is not one of the five agents is almost
always a typo - `builders` for `builder`. Say so once and carry on.

## Notes

<Anything you want to remember about this platform. This file is yours and is
loaded whenever you work in the hub.

It is not given to the agents, so nothing written here reaches one. A standing
instruction for them goes in `rules:` in `config.yaml`; how code is written
goes in `conventions/README.md` for every repo, or `conventions/<language>.md`
for one language. Builders are given those files by name.>
