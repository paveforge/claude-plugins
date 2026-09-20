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
| `/pave:design` | Blast radius → spec → architecture → contracts → task documents |
| `/pave:build` | Land the contracts, fan out one agent per service |
| `/pave:review` | Contracts against consumers, tests, rollout order |

### The hub

```
hub/
├── config.yaml              team policy - commit this
├── workspace.yaml           your repos - gitignored, local to you
├── CLAUDE.md
├── conventions/             how code is written, by language and service
├── artifacts/               disposable
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

### Why it works

The design phase is the expensive one and gets the strong model. The build
agents get a cheaper one — not because they are doing the same job with less
care, but because their job is genuinely smaller: contracts are frozen, tasks
are concrete, out-of-scope is explicit, and anything ambiguous escalates to the
hub instead of being improvised. Models are set per phase in `config.yaml`.

If build agents routinely need to think their way out of gaps, that is a defect
in the design phase, not a reason to raise the build model.
