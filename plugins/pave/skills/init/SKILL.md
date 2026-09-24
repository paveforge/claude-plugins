---
name: init
description: Set up a Pave hub in a folder. Creates config.yaml, an empty workspace.yaml and the hub scaffolding. Use once, before anything else. Services are added afterwards with /pave:add.
argument-hint: "[hub path]"
---

# Pave — init

Set up the hub. Nothing else.

Init does not look for repos, does not guess what anything is, and does not
scan. It creates a hub and leaves `workspace.yaml` empty. Services are
registered with `/pave:add`, and `/pave:analyse` works out what they are.

That split keeps each step doing one thing you can verify before moving on.

## 1. Choose the hub

The hub is the central command folder. Every spec, design, contract, task
document and report lives here; service repos are only ever changed by a
`builder` agent.

If `$1` was given, use it. Otherwise ask, with two options:

```
Set up a Pave hub here?

  1. /Users/long/be-central          (current folder)
  2. Other                           - tell me where

This creates config.yaml, workspace.yaml, CLAUDE.md and conventions/.
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

If the hub is not a git repository, say so and offer `git init`. If the user
declines, carry on, but tell them plainly that nothing can be shared with the
team until the hub is version controlled — and then write no `.gitignore`, and
skip the what-to-commit advice at the end.

## 3. Write

| File | If absent | If present |
|---|---|---|
| `.pave-hub` | Empty marker — other skills walk up to find it | Leave |
| `config.yaml` | From `templates/config.yaml` | **Leave untouched** — it is team policy |
| `workspace.yaml` | From `templates/workspace.yaml`, with **no services** | Leave |
| `CLAUDE.md` | From `templates/hub-CLAUDE.md`, unless an `AGENTS.md` is already there | Leave |
| `conventions/README.md` | From `templates/conventions-README.md` | Leave |
| `features/README.md` | From `templates/features-README.md` | Leave |
| `.claude/settings.json` | `additionalDirectories: []` | **Merge** — add nothing, leave every other setting alone |
| `.gitignore` | Add `workspace.yaml`, if git | Add the line if missing |

`config.yaml` is never rewritten. A teammate who clones the hub already has
the team's settings, and init must not undo them.

The hub's `CLAUDE.md` is where the user writes rules of their own, and every
agent Pave spawns is given it as required reading. Say so when you report —
it is the answer to "where do I put my own rules", and nothing else in the hub
serves that purpose. If the folder already has an `AGENTS.md`, that is the
same file under the name some other tools use: leave it, write no `CLAUDE.md`,
and say which one you found.

`.claude/settings.json` belongs to Claude Code, not to Pave. Merge into it;
never replace it.

## 4. Report

Say where the hub is and which files were created versus left alone.

Then say what is next, and be concrete — an empty hub does nothing:

```
Hub ready at /Users/long/be-central. No services registered yet.

  /pave:add ../be-user-service
  /pave:add ../be-order-service
  /pave:add ../be-pricing-service

Then /pave:analyse to work out what they are and what they do.
```

If the hub is a git repository, say what to commit: `config.yaml`,
`CLAUDE.md`, `conventions/` and `.pave-hub` are shared with the team.
`workspace.yaml` is not — it holds local paths, and a teammate builds their
own with `/pave:add`.
