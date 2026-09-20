# claude-plugins

Claude Code plugins for paveforge.

```
/plugin marketplace add paveforge/claude-plugins
/plugin install pave@paveforge
```

## pave

Plan a feature once across every service it touches, freeze the contracts, then
build each service in parallel.

When a feature spans several services, the usual approach is to go service by
service, designing each in isolation. The cross-service picture — which
services are affected, what the interfaces between them are, what order things
must ship in — never exists anywhere except in someone's head.

Pave inverts that. A **hub** folder sits beside your service repos and holds the
planning. A feature is designed once, across all of it, with the contracts
between services defined and generated before any implementation starts.
Freezing the contracts is what makes the next step safe: the services stop
depending on each other's in-flight code, so they can be built at the same time
by separate agents, each working from a self-contained task document.

Language-agnostic by design. Build commands are discovered per repo — CI config
first, since that says how *your team* builds *this repo* — so nothing in the
plugin assumes a stack or an architecture.

### Commands

| | |
|---|---|
| `/pave:init` | Set up the hub, scan the repos, write `workspace.yaml` |
| `/pave:analyse` | Learn what each service does; write the knowledge base |
| `/pave:design` | Blast radius → spec → architecture → contracts → task documents |
| `/pave:build` | Land the contracts, fan out one agent per service |
| `/pave:review` | Did the agents do exactly what the plan said? |

| Command | When |
|---|---|
| `init` | First time, and whenever repos are added or move |
| `analyse` | First time, then on demand as services drift |
| `design` | Every new feature |
| `build` | Once the plan is approved |
| `review` | On demand |

`init` records how to *build* each repo. `analyse` records what each service
*does*. Design needs both — without the second it writes confident, concrete
tasks that contradict code which already exists, and an agent faithfully
builds them.

### The hub

```
hub/
├── config.yaml              team policy - commit this
├── workspace.yaml           your repos - gitignored, local to you
├── CLAUDE.md
├── conventions/             how code is written, by language and service
├── artifacts/
│   └── knowledge/           what each service does - indexed, disposable
└── features/
    ├── README.md            portfolio: one row per feature
    └── build-checkout/
        ├── README.md        feature: one row per task
        ├── spec.md
        ├── architecture.md
        ├── contracts/       frozen at gate 2
        ├── tasks/           one self-contained document per unit of work
        └── artifacts/       build and review reports
```

`config.yaml` is shared and machine-independent; `workspace.yaml` holds the repo
paths, which differ per developer. That split is what lets a team share one
policy while everyone keeps their own local layout.

### Selective loading

`/pave:analyse` spawns one agent per service and writes an indexed knowledge
base: a domain model, business flows, integrations and data ownership per
service, plus a single generated index of capabilities, domain terms and
events.

Design loads that index — and only that — then opens the specific files it
points at. A four-service feature in a twelve-service platform reads one index,
four summaries and a handful of deep files.

There is no vector store and no graph database. The index is a generated table
of business vocabulary, and the events table is the dependency graph. Both are
rebuilt from the analysts' frontmatter, so they cannot drift from the files
they describe.

Knowledge goes stale path-scoped rather than by age: each service records the
commit and the source directories its analysis rested on, so a month of commits
to CI config invalidates nothing, and a change under `internal/domain`
invalidates exactly one service.

### Review is a conformance check

Build agents tick their own checkboxes and report their own success. `review`
is the independent check on those claims: every ticked item has to be findable
in the code, and both sides of every frozen contract have to honour it. It
reads code and runs nothing — the builders already ran the commands and CI
runs them again.

It does not ask whether the feature works, or whether the plan was right. That
restraint keeps it cheap and keeps the approval gates meaningful. A gap in the
plan is a comment, not a failure; you decide whether to re-plan.

When an agent claimed work it did not do, review unchecks those specific items,
marks the task `failed`, and writes a per-task report. `/pave:build` then
re-runs only the failed tasks, and each agent reads only its own section — so a
fix touches three items rather than redoing twenty.

### Why it works

Models come from `config.yaml` and are enforced at spawn. Design is the one
exception: it runs on the *stronger* of your session model and the configured
one. On sonnet with opus configured you get opus; on fable you keep fable —
a weaker plan is not a cheaper plan, it is a more expensive one paid later by
build agents faithfully implementing it.

The design phase is the expensive one and gets the strong model. The build
agents get a cheaper one — not because they are doing the same job with less
care, but because their job is genuinely smaller: contracts are frozen, tasks
are concrete, out-of-scope is explicit, and anything ambiguous escalates to the
hub instead of being improvised. Models are set per phase in `config.yaml`.

If build agents routinely need to think their way out of gaps, that is a defect
in the design phase, not a reason to raise the build model.
