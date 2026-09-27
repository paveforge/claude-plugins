---
name: init
description: Set up a Pave hub in a folder, or bring an existing hub up to date after a Pave upgrade. Creates config.yaml, an empty workspace.yaml and the hub scaffolding; on an existing hub, offers to fix config drift. Services are added afterwards with /pave:add.
argument-hint: "[hub path]"
---

# Pave — init

Set up the hub. Nothing else.

Re-running it on an existing hub is also the upgrade step after a Pave update:
it creates what is missing, leaves what exists, and offers to bring the config
up to date (§3, *An existing hub's config*).

Init does not look for repos, does not guess what anything is, and does not
scan. It creates a hub and leaves `workspace.yaml` empty. Services are
registered with `/pave:add`, and `/pave:analyse` works out what they are.

That split keeps each step doing one thing you can verify before moving on.

## 1. Choose the hub

The hub is the central command folder. Every spec, plan, contract, task
document and report lives here; service repos are only ever changed by a
`builder` agent.

If `$1` was given, use it. Otherwise ask, with two options:

```
Set up a Pave hub here?

  1. /Users/long/platform          (current folder)
  2. Other                           - tell me where

This creates config.yaml, workspace.yaml, AGENTS.md and conventions/.
```

Offer the current folder first when it is empty or already contains
`.pave-hub`. If it contains something else — a service repo, another
project — say so and let the user choose. A hub inside a service repo is
almost always a mistake.

Never guess. Never silently use the working directory.

## 2. Check for git

The config split depends on it: `config.yaml` is committed and shared,
`workspace.yaml` is gitignored and local to each person. Without git neither
happens.

If the hub is not a git repository, say so and offer `git init -b main` (so
the hub starts on `main`, not `master`). If the user
declines, carry on, but tell them plainly that nothing can be shared with the
team until the hub is version controlled — and then write no `.gitignore`, and
skip the what-to-commit advice at the end.

## 3. Write

| File | If absent | If present |
|---|---|---|
| `.pave-hub` | Empty marker — other skills walk up to find it | Leave |
| `config.yaml` | From `templates/config.yaml` — **unless `config.yml` or `config.toml` exists**, in which case write nothing | **Leave as it is** — it is team policy. Offer to bring it up to date, below |
| `workspace.yaml` | From `templates/workspace.yaml`, with **no services** | Leave |
| `AGENTS.md` | From `templates/hub-AGENTS.md` | Leave |
| `CLAUDE.md` | One line: `@AGENTS.md` | Leave if it already imports `@AGENTS.md`; otherwise see below |
| `conventions/README.md` | From `templates/conventions-README.md` | Leave |
| `features/README.md` | From `templates/features-README.md` | Leave |
| `.claude/settings.json` | `additionalDirectories: []` | **Merge** — add nothing, leave every other setting alone |
| `.gitignore` | Add `workspace.yaml`, if git | Add the line if missing |

The config file is rewritten only by `pave.sh config-fix`, on the user's
choice below, and never added beside another one. A hub
may use `config.yaml`, `config.yml` or `config.toml`, but only one: a second
file makes every command that reads the config stop with an error. A teammate
who clones the hub already has the team's settings, and init must not undo
them.

The hub's `AGENTS.md` is where the user writes rules of their own, and every
agent Pave spawns is given it as required reading. Say so when you report —
it is the answer to "where do I put my own rules", and nothing else in the hub
serves that purpose. `CLAUDE.md` exists only so Claude Code, which does not
read `AGENTS.md` by itself, loads the same rules in an interactive session.

**A hub from before this change** has its rules in `CLAUDE.md` and no
`AGENTS.md`. Pave no longer reads that file for rules, so offer to move it:
rename `CLAUDE.md` to `AGENTS.md` and write the one-line `CLAUDE.md`. Do it
only on "yes". If both files have rules of their own, do not merge them -
say so and let the user move theirs into `AGENTS.md`.

**An existing hub's config.** Pave has no defaults: every command reads its
agents and settings from the config, and stops when one is missing. After an
upgrade the config may also hold keys Pave no longer reads, which do nothing.
Run:

```
"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh config-check
```

It compares the config with `templates/config.yaml` and prints a `leftover`
line for each key the template does not have, a `missing` line for each key
the template has and the config lacks, and a `result:` line. If there is
nothing to fix, say nothing about it. Otherwise show its lines as they are and
ask one question:

```
config.yaml differs from what this version of Pave reads:

  leftover  agents.designer = { model: fable, effort: max }
  missing   agents.planner = { model: opus, effort: high }

  1. Add missing keys and remove leftovers   (recommended)
  2. Add missing keys only
  3. Remove leftovers only
  4. Leave the config as it is

Pave rewrites the file: its opening comment block stays, other comments do not.
A removed key's value is not carried over - edit the config afterwards to keep it.
```

Run the script with the option chosen, and nothing else:

| Choice | Command |
|---|---|
| 1 | `pave.sh config-fix all` |
| 2 | `pave.sh config-fix add` |
| 3 | `pave.sh config-fix remove` |
| 4 | none |

Report its lines as they are. Never edit the config yourself. If missing keys
remain, say that commands needing them will stop until they are added.

`.claude/settings.json` belongs to Claude Code, not to Pave. Merge into it;
never replace it.

## 4. Report

Say where the hub is and which files were created versus left alone, and
whether the config was brought up to date.

Then say what is next, and be concrete — an empty hub does nothing:

```
Hub ready at /Users/long/platform. No services registered yet.

  /pave:add ../user-service
  /pave:add ../order-service
  /pave:add ../pricing-service

Then /pave:analyse to work out what they are and what they do.
```

If the hub is a git repository, say what to commit: the config file
(`config.yaml`, or the `.yml` / `.toml` the hub uses), `AGENTS.md`, `CLAUDE.md`, `conventions/`, `.pave-hub` and, once it exists, `artifacts/knowledge/on-demand/` are shared with the team.
`workspace.yaml` is not — it holds local paths, and a teammate builds their
own with `/pave:add`.
