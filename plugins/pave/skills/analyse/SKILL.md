---
name: analyse
description: Work out what the registered services are and what they do. Discovers each one's language, build commands and contracts, then reads its domain model and writes an indexed knowledge base. Use after /pave:add, and when services drift.
effort: medium
argument-hint: "[service name, or blank for everything missing or stale]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# Pave — analyse

Turn registered folders into knowledge.

`/pave:add` recorded where the services are. This phase answers both of the
remaining questions:

| Question | Answered by | Written to |
|---|---|---|
| How do I build this repo? | `explorer` | `workspace.yaml` |
| What does this service **do**? | `analyst` | `artifacts/knowledge/` |

The second is the one that is easy to skip and expensive to miss. Without it,
design writes confident, concrete tasks that contradict code which already
exists — a `Reservation` entity in a service that has had `StockHold` for two
years. Concrete and wrong is worse than vague, because a builder will
faithfully build it.

## Before starting

Locate the hub. Read `config.yaml` and `workspace.yaml`.

If no services are registered, stop and say to run `/pave:add <folder>` first.

## 1. Decide what to analyse

Run the script. It checks every registered service and reports what each one
needs:

```
"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh stale $ARGUMENTS
```

```
undiscovered svc-d       no language in workspace.yaml
missing      svc-c       no knowledge folder
stale        svc-b       1 file(s) changed under internal/domain
orphan       old-svc     knowledge folder, no such service in workspace.yaml
current      svc-a       unchanged since 0818f6e
```

| State | Do |
|---|---|
| `undiscovered` | §2 discovery, then §3 analysis |
| `missing` | §3 analysis |
| `stale` | §3 analysis |
| `orphan` | Delete the knowledge folder and say so |
| `current` | Nothing |
| `unreachable` | Report it. Do not analyse, do not guess |

Given a service name, the script checks only that one. Given none, it checks
everything.

**Staleness is path-scoped, not time-based**, which is what the script
implements: a service is stale only when the source directories its analysis
rested on have changed. A month of commits to CI config, READMEs or unrelated
packages invalidates nothing, and re-reading a service that has not moved is
pure cost.

Report what needs doing, and why, before spawning anything.

An `orphan` matters more than it looks. A knowledge folder for a service no
longer registered keeps appearing in the index, and design will happily plan
against a service nobody can build.

## 2. Discover — what each repo is

Spawn one `explorer` per service needing discovery, in parallel up to
`execution.max_parallel`, using `agents.explorer.model`.

Pass each one its **agent rules**, pasted verbatim: the top-level `rules` from
`config.yaml` followed by `agents.explorer.rules`. Nothing if both are empty.

Never scan a repo yourself in the main context. One large repo will fill it,
and you still have the rest of the phase to run.

Discovery order, first hit wins:

1. **CI workflows** (`.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`) —
   the best source. A manifest says what language a repo is; CI says how *this
   team* builds and tests *this repo*, which is the question that matters.
2. **Task runner** — `Makefile`, `justfile`, `Taskfile.yml`, `package.json`
   scripts
3. **Manifest** — whatever declares the project. Common ones:
   `go.mod`, `package.json`, `pyproject.toml`, `requirements.txt`,
   `Cargo.toml`, `pom.xml`, `build.gradle`, `*.csproj`, `Gemfile`,
   `composer.json`, `mix.exs`, `pubspec.yaml`, `*.cabal`, `dune-project`
   — and for infrastructure: `*.tf`, `Pulumi.yaml`, `Chart.yaml`,
   `kustomization.yaml`, `ansible.cfg`, `Dockerfile`, `*.bicep`
4. **README**
5. **Report it as unknown** — never invent a command

That list is a hint, not a definition. It will be out of date the day someone
adopts a tool nobody here has heard of. Treat an unrecognised project as a
discovery problem to report, never as a reason to assume — and a repo that
does not match anything still has CI, a task runner or a README, which are the
sources that actually matter.

### `commands` mean whatever the repo does, not compilation

`build`, `test` and `lint` are slots, not literal compiler invocations. A
Terraform repo's are `terraform validate`, `terraform plan` and `tflint`; a
Helm chart's are `helm template`, `helm test` and `helm lint`; a docs site's
may be a static build and a link checker. Record what the repo's own CI runs to
decide whether a change is good.

Leave a slot absent when the repo genuinely has no equivalent. An absent
command is a fact a builder can work with; an invented one is a command that
fails in CI and nobody can explain.

Record per service: `kind` (service | library | app | infra), `language`,
`commands`, `contracts`, `consumes` where imports make it clear, the repo's own
`CLAUDE.md` if it has one, and `repo_root` — the git root, so that two services
sharing one are recognised as a monorepo and `execution.monorepo_strategy`
applies to them.

### Filling in workspace.yaml

**Fill empty fields. Never overwrite a field that has a value.**

`workspace.yaml` is the user's source of truth and they are invited to correct
it. A hand-written `test: make test-integration` must survive every future run,
or the correction has to be made again each time and will eventually be lost
without anyone noticing.

Where discovery disagrees with a value already there, leave the file alone and
report it:

```
payment-service  test: file says `make test-integration`, CI says `go test ./...`
                 Kept yours. Edit workspace.yaml if that is wrong.
```

Anything discovery could not determine stays absent, and is reported as a gap
for the user to fill.

## 3. Analyse — what each service does

Spawn one `analyst` per service, in parallel up to `execution.max_parallel`,
using `agents.analyst.model`.

Each writes only its own folder under
`artifacts/knowledge/services/<service>/`, its README from
`templates/knowledge-service-README.md`. One writer per directory, the same
rule as the builders.

Give each analyst its path, its language, its entry from `workspace.yaml`, and
**the current commit sha of its repo** — the analyst has no Bash and cannot
read it itself, and without it the staleness check has nothing to compare
against.

Pass its **agent rules** too, pasted verbatim: the top-level `rules` from
`config.yaml` followed by `agents.analyst.rules`. Nothing if both are empty.

Require a short summary back. Detail belongs in the files; four analysts
returning full narratives will exhaust this session's context.

## 4. Draft the conventions

For each language found, spawn one `analyst` to sample the repos using it and
draft `conventions/<language>.md`. Tell the user these are drafts to correct.

The `analyst`, not the `explorer`. Inferring a house style from source files is
pattern work, and a convention file drafted too shallowly is worse than none —
every builder follows it.

Pass its agent rules here too — the same `rules` plus `agents.analyst.rules`
as §3. But **a rule does not become a convention**:
this file records what the repos already do, and a rule saying how the team
*should* write code stays in `config.yaml` where the user put it. Copying it
here would turn one instruction into two copies that drift, and dress an
instruction up as an observation.

Seed once. **Never rewrite an existing convention file**; it is the user's the
moment they touch it, which is why `conventions/` sits outside `artifacts/`.

Skip a repo that has its own `CLAUDE.md` — record the path in `workspace.yaml`
and builders read it directly rather than following a duplicate.

## 5. Regenerate the index

`artifacts/knowledge/README.md` is the only file design loads unconditionally,
so it must be small and it must be generated — never hand-written, never
appended to.

**Rebuild it from every service README, not only the ones just analysed.**
`/pave:analyse <service>` regenerates the whole index from all of them.
Building it from one analyst's output would erase every other service from the
capabilities, terms and events tables, and design would then plan as though
those services did not exist.

Build it from `templates/knowledge-README.md`, filled from the frontmatter of
every service README.

The **Events** table is the dependency graph. There is no graph database here,
but adjacency written down as a generated table answers the same questions and
costs nothing to load.

The **Terms** table earns its place on its own. The failure this phase exists
to prevent is a vocabulary miss — design inventing a concept the platform
already names. Having the glossary in the always-loaded index catches it before
a task document is written.

Where two services define the same term differently, record both and mark it
ambiguous. Do not pick a winner; that is a finding, and design needs to see it.

## 6. Report

State which services were discovered, which were analysed, which were skipped
as current, every conflict you left alone, every gap discovery could not fill,
and every `uncertain` entry the analysts raised. Those last ones are the points
design must verify against code rather than trust.

**Do not report a service as done if its agent returned blocked, incomplete or
nothing at all.** Leave its previous state, do not update its `commit`, and say
it still needs analysing — otherwise the next run sees a current `commit` and
skips a service that was never read. A repo that could not be reached is the
same case.

Then say what is next: `/pave:design <feature>`.
