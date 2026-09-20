---
name: init
description: Set up or refresh a Pave hub. Locates the hub folder, scans the service repos, and writes workspace.yaml. Use when starting with Pave for the first time, after cloning a hub, or when repos have been added, moved or changed.
effort: low
argument-hint: "[hub path]"
---

# Pave — init

Set up the hub, then discover what is in the workspace.

Init is **on demand**, not part of the feature workflow. It runs on whatever
model the session is on, because it may be about to create the config file
that would otherwise configure it.

## 1. Locate the hub

The hub is the central command folder. All specs, designs and task documents
live there; the service repos stay untouched except by build agents.

- If `$1` was given, use it.
- Otherwise walk up from the working directory looking for `.pave-hub`, the
  same way every other skill locates the hub.
- Otherwise **ask**. Never guess, and never silently use the working
  directory. Offer the working directory as the default and show what would
  be created.

Create the folder if it does not exist. Write `.pave-hub` (an empty marker) at
its root so other skills can locate it by walking up from anywhere.

### The hub should be a git repository

The whole config split depends on it: `config.yaml` is committed and shared,
`workspace.yaml` is gitignored and local to each person. Without git, neither
happens — the `.gitignore` does nothing and there is nothing to share.

If the hub folder is not a git repository, say so and offer to run `git init`.
If the user declines, continue, but tell them plainly that `config.yaml` and
`conventions/` cannot be shared with the team until the hub is version
controlled, and skip the "what to commit" advice at the end. Do not write a
`.gitignore` that has no effect.

## 2. config.yaml — generate only if absent

| State | Action |
|---|---|
| Absent | Write it from `templates/config.yaml`, with `hub.name` set to the hub folder's name |
| Present | **Leave completely untouched** |

Set `hub.name` from the folder rather than leaving the template's placeholder.
It names the generated workspace file, and `platform.code-workspace` sitting
inside a folder called `be-central` is confusing from the first minute.

`config.yaml` is team policy and is committed. A teammate who clones the hub
already has it; init must never rewrite their settings. If they want different
defaults they edit the file.

## 3. Discover

Repo paths live in `workspace.yaml`, not `config.yaml`.

**Look for repos the user has already opened before asking them to type
anything.** If a multi-root editor workspace is open — a `.code-workspace`
file, or several folders in the sidebar — its other folders are almost
certainly the service repos. Offer them:

```
You have 3 other folders open alongside this hub:
  ../be-user-service
  ../be-order-service
  ../be-pricing-service

Use these as the service repos?  [Y / edit / n]
```

Asking someone to type three paths they already added to their editor is the
kind of friction that makes a setup step feel worse than doing it by hand.

Fall back to asking outright if no workspace is open, or if the user edits the
list. If `workspace.yaml` already exists, use the paths it records and ask
whether anything has been added.

Check each path exists before scanning it. A path that has moved is a finding
for the summary, not a crash.

Then dispatch the `explorer` agent — one per repo, in parallel — using
`agents.explorer.model` from `config.yaml` if it exists.

Never scan repos yourself in the main context. A single large repo will fill it
and you still have a summary to present.

Discovery order per repo, first hit wins:

1. **CI workflows** (`.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`) —
   the best source. A manifest says what language it is; CI says how *this
   team* builds and tests *this repo*.
2. **Task runner** — `Makefile`, `justfile`, `Taskfile.yml`, `package.json`
   scripts
3. **Manifest** — `go.mod`, `package.json`, `pyproject.toml`, `Cargo.toml`,
   `pom.xml`, `build.gradle`, `*.csproj`, `Gemfile`, `composer.json`,
   `mix.exs`, `pubspec.yaml`
4. **README**
5. **Ask**

A repo containing several manifests in subdirectories is a monorepo: record one
service per package, each with its own `path`.

Also record, per service: `kind` (service | library | app | infra), `language`,
any contract files (`.proto`, `openapi.yaml`, `*.graphql`, JSON Schema, Avro),
`consumes` edges where they can be inferred from imports or client code, and
the path to the repo's own `CLAUDE.md` if it has one.

## 4. workspace.yaml — warn before touching

`workspace.yaml` is the source of truth for repos. It is local to this machine
and gitignored, which is what lets the team share one `config.yaml` while each
person keeps their own layout. It may contain hand edits.

If it already exists, **do not overwrite it silently.** Diff what you just
discovered against what the file says, and mark anything that would destroy a
hand edit — a value that differs from discovery on a file whose mtime is later
than its own `generated_at`:

```
!  workspace.yaml already exists - generated 2026-09-14, modified since.
   This file is your source of truth and may contain corrections.

   Rescanning would change:
     + loyalty-service    ../loyalty-service                       new
     ~ payment-service    test: make test-integration -> go test ./...
                          ^ your edit would be overwritten
     - legacy-billing     ../legacy-billing no longer exists

   Back up to workspace-old.yaml and regenerate?  [Y / n / cancel]
```

On yes: copy to `workspace-old.yaml` (one generation only — it overwrites any
previous backup), then continue. On no: keep the existing file and report what
is stale. On cancel: stop.

## 5. Summarise and ask

Discovery will miss things. Never write `workspace.yaml` straight from a scan.
Present three groups — the split is what makes the review actually happen,
because a flat list of twelve services gets skimmed and accepted:

```
Scanned /Users/long/platform - found 5 services across 4 repos

  Service          Path                             Lang  Kind     Build/test   Contracts
  order-service    ../order-service                 go    service  CI           1 proto
  stock-service    ../stock-service                 go    service  CI           1 proto
  web-checkout     ../storefront/apps/web           ts    app      pnpm         -
  shared-events    ../storefront/packages/events    ts    library  pnpm         3 schemas

Needs your input
  !  payment-service   no lint command found anywhere
  !  shared-events     guessed kind=library from package.json - correct?

Found but not included
  ?  ../legacy-billing  no manifest, no CI - include it?
  ?  ../infra           terraform only - include as kind=infra?

Anything I missed? Add a repo path, a monorepo subpath, or a service
I can't detect. Enter to accept.
```

"Found but not included" is not optional. Anything that looked like a repo but
had no recognisable tooling goes there rather than being dropped — that is
exactly where a legacy service with no CI would otherwise vanish.

Loop until the user accepts. Their answers go into `workspace.yaml` itself,
including an `ignored:` list so init stops asking about the same vendored
folder on every run.

## 6. Write

- `workspace.yaml` — from `templates/workspace.yaml`
- `artifacts/<hub.name>.code-workspace` — hub plus every repo, multi-root.
  **Skip this if a multi-root workspace is already open** with the hub and the
  repos in it. The user built that layout by hand to get here; generating a
  second file describing it is clutter, not help. Say you skipped it and why.
- `.claude/settings.json` — `additionalDirectories` pointing at every repo
  path. Without this the build agents cannot read or write the service repos.
  **If the file exists, merge into it.** Add missing directories and leave
  every other setting alone — it is a Claude Code config the user may have
  customised, not a Pave artefact.
- `CLAUDE.md` — from `templates/hub-CLAUDE.md`, if absent
- `conventions/README.md` — from `templates/conventions-README.md`, if absent
- `conventions/<language>.md` — drafted, see below, if absent
- `features/README.md` — from `templates/features-README.md`, empty table, if absent
- `.gitignore` — if the hub is a git repository, ensure it contains
  `workspace.yaml` and `workspace-old.yaml`

## 7. Draft the conventions

For each language found, spawn an `analyst` — one per language, using
`agents.analyst.model` — to sample the repos using it and draft
`conventions/<language>.md`. Tell the user these are drafts to correct.

The `analyst`, not the `explorer`. Explorer answers mechanical questions: which
manifest, which test command. Inferring a house style from source files is
pattern work, and a convention file drafted too shallowly is worse than none —
every builder follows it.

Asking a team to hand-write a convention file per language before they can
start is where this stalls. A wrong draft they fix in two minutes is worth more
than a blank file they never fill in.

Seed these once. Never rewrite an existing convention file — it is theirs the
moment they touch it, which is why `conventions/` sits outside `artifacts/`.

Skip a repo that already has its own `CLAUDE.md`: record the path in
`workspace.yaml` instead, and build agents will read it directly. Do not
duplicate conventions the team already wrote.

## 8. Report

State where the hub is, how many services are registered, which files were
created versus left alone, and what to run next.

If the hub is a git repository, say what to commit: `config.yaml`,
`CLAUDE.md`, `conventions/` and `.pave-hub` are shared with the team.
`workspace.yaml` is not — it is gitignored, and a teammate generates their own
by running this command. That split is what lets everyone share one policy
with different local paths.

If it is not, say that instead: the hub works locally, but nothing can be
shared until it is version controlled.

Next is `/pave:analyse`, not `/pave:design`. Init recorded how to *build* each
repo; nothing yet knows what any service *does*, and design writes confident,
concrete tasks that will contradict existing code without it.
