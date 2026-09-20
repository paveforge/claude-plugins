# <Hub name>

This is a Pave hub: the central command folder for cross-service feature work.
Specs, designs, contracts and task documents live here. The service repos are
reachable through `additionalDirectories` and are modified only by build agents.

## Layout

- `config.yaml` - team policy. Committed, shared.
- `workspace.yaml` - your repos. Local, gitignored, source of truth.
- `conventions/` - how code is written, by language and service. Yours to edit.
- `features/` - the durable record of what was decided.
- `artifacts/` - disposable. Delete anything here and it regenerates.
- `artifacts/knowledge/` - what each service does, written by `/pave:analyse`.
  Derived from code, so it is disposable; its index is what lets design load
  selectively instead of scanning everything.

## Workflow

| | When |
|---|---|
| `/pave:init` | First time, and whenever repos are added or move |
| `/pave:analyse` | First time, then on demand as services drift |
| `/pave:design` | Every new feature - two approval gates |
| `/pave:build` | Once the plan is approved |
| `/pave:review` | On demand |

`init` records how to build each repo. `analyse` records what each service
does. Design needs both: without the second it writes concrete tasks that
contradict code which already exists.

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
planning -> ready -> building -> done
                                  |
                                  |  review finds the plan was not followed
                                  v
                               failed -> building -> done
```

`build` sets `done`. `review` is the independent check that the agents did
what the plan said, and sets `failed` if they did not - then `/pave:build`
re-runs only the failed tasks.

Review checks execution against the plan, not whether the feature works. A
gap in the plan is not a review failure: it is a comment, and you decide
whether to re-design.

`/pave:design <slug>` re-designs the whole feature rather than patching the
gap. You cannot know that only one case was missed, and a patched design
produces tasks that are individually reasonable and collectively inconsistent.

## Rules

**Contracts are frozen at gate 2.** They change by re-running `/pave:design`,
never by editing them in a service repo. The freeze is what lets services be
built in parallel; a local edit breaks every service building against it.

**Task documents are self-contained.** An agent executing one has not seen the
design discussion and cannot read the others.

**Escalate, do not improvise.** A gap in a task document is a design defect.
Report it rather than guessing - the hub can see every service, the agent
cannot.

**The roll-up READMEs are generated.** `features/README.md` and each feature's
`README.md` are rewritten from task frontmatter. Do not hand-edit them.

## Conventions

<Cross-cutting rules that apply to every repo. Language-specific rules belong
in `conventions/<language>.md`, which is loaded only when a task targets that
language.>
