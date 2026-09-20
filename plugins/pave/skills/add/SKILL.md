---
name: add
description: Register a service folder with the Pave hub. Records its absolute path in workspace.yaml and grants Claude access to it. Use after /pave:init, and whenever a new service joins the platform.
effort: low
argument-hint: "<folder> [more folders...]"
---

# Pave — add

Register where a service lives. Not what it is.

This skill records a path and grants access. It does not detect the language,
find the build commands, or read any code — `/pave:analyse` does all of that,
and doing it here would mean two skills discovering the same things
differently.

## 1. Locate the hub

Walk up from the working directory for `.pave-hub`. If there is none, stop and
say to run `/pave:init` first.

## 2. Check each folder

For every path given:

- **It must exist and be a directory.** Report and skip anything that is not.
- **Resolve it to an absolute path.** `workspace.yaml` never leaves this
  machine, and skills run from inside service repos as well as from the hub,
  so a relative path would mean different things depending on where you were
  standing.
- **Warn if it is not a git repository.** Builders commit their work on a
  branch; a folder without git cannot take one. Let the user continue if they
  want — it may be deliberate — but say it once.
- **Warn if it is the hub, or inside it.** That is almost always a mistake:
  the hub holds planning, not code, and a builder would end up committing to
  it.
- **Skip silently if it is already registered.** Adding twice is not an error.

## 3. Name it

Default to the folder's own name — `../be-order-service` becomes
`be-order-service`.

If a service with that name already exists at a different path, stop and ask.
Two services with one name would make task documents ambiguous about which
repo they target, and a builder would have no way to tell.

For a service inside a monorepo, point at the package, not the repo root:

```
/pave:add ../storefront/packages/events
```

`/pave:analyse` notices that two services share a git root and records the
monorepo relationship, which is what `execution.monorepo_strategy` acts on.

## 4. Write

Append to `services:` in `workspace.yaml`:

```yaml
  - name: be-order-service
    path: /Users/long/be-order-service
    # everything else is filled in by /pave:analyse
```

Only `name` and `path`. Leave the rest absent rather than guessing — an empty
field is a question `/pave:analyse` will answer, while a wrong guess is
something it will trust.

Then add the path to `additionalDirectories` in `.claude/settings.json`,
merging rather than replacing. **This is the step that actually grants access**
— without it, agents cannot read or write that repo however correctly
`workspace.yaml` describes it.

## 5. Report

List what was added, what was skipped and why, and how many services the hub
now knows about.

Then point at the next step: `/pave:analyse`, which reads each registered
folder and works out its language, build commands, contracts and what it does.

Until that runs, Pave knows where these services are and nothing else.
