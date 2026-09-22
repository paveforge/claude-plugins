---
name: help
description: Explain how a Pave command works, or what to run next. Answers from the plugin's own docs only - no hub needed. For questions about your hub's services, conventions or features, use /pave:query instead.
effort: low
argument-hint: "[command or question]"
allowed-tools: Read, Glob, Grep
---

# Pave — help

Explain Pave itself. Nothing about your hub.

This skill answers from the plugin's own files —
`${CLAUDE_PLUGIN_ROOT}/skills/*/SKILL.md` and nothing else. No hub lookup, no
`.pave-hub` walk, no agent spawn: the whole answer is a handful of small
files already in the plugin, so reading them here costs less than delegating
would.

For anything about *your* hub — what a service does, why a feature is
stuck, what a convention says — this skill is the wrong tool. Say so and
point at `/pave:query <question>` rather than guessing.

## No argument — overview

List the workflow in order (`init` → `add` → `analyse` → `design` → `build`
→ `review`), then the anytime commands (`help`, `query`, `visualize`), each
with the one-line `description` read straight from its `SKILL.md`
frontmatter — never hand-copied, so it can't drift from the real text.

## Argument names a command

`/pave:help design`, `/pave:help build` — read that skill's full `SKILL.md`
and explain what it does, what it asks the user, and what normally comes
before and after it, in plain language.

## Argument is a free-form question

Decide first whether it's actually about Pave:

- **About Pave** — "how does build decide which tasks run in parallel",
  "why doesn't review fail on a missing case" — answer from the relevant
  `SKILL.md` file(s).
- **About the hub** — names a service, a feature id, a convention, or
  anything only the hub's own docs could answer — don't attempt it. Say
  plainly this needs `/pave:query <question>` instead.

When unsure which it is, look for a concrete noun that isn't a Pave concept
(a service name, a feature id) — that's the signal it belongs to `/pave:query`.
