---
name: design
description: Plan a feature across every service it touches. Finds the blast radius, writes the spec and architecture, freezes the contracts, and produces one self-contained task document per unit of work. Use before building any feature that spans more than one service.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, SendMessage
argument-hint: "[TICKET-123] <description> | <existing feature id>"
---

# Pave — design

Design the feature once, across all services, with contracts defined first.

This is the phase the whole plugin exists for, and the one the feature lives or
dies on. Everything downstream executes what is decided here; nothing
downstream is allowed to redesign it. Spend the effort here.

## 0. Resolve the feature id

Run the script. It parses the argument, picks the id, creates the folder and
tells you what it decided:

```
"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh feature $ARGUMENTS
```

```
id: DGF-8888
title: build checkout
status: new
path: /Users/long/platform/features/DGF-8888
```

**The feature id is the folder name.** There is no second identifier — it is
what `/pave:build` and `/pave:review` take, and what task documents carry in
frontmatter. It exists to be short and retypable, because every later step is
addressed by it from sessions that remember nothing.

A ticket reference becomes the id; otherwise the script allocates `feat-N`.
The id is never derived from the description: a kebab-cased sentence is not
something anyone types twice, and generating one removes the judgement about
how long is too long.

### Act on what it reports

| Field | Meaning |
|---|---|
| `status: new` | First design of this feature |
| `status: exists` | **Re-design.** Say so before re-deriving anything — see below |
| `note: no description` | Nothing says what this feature is. **Ask.** Do not design into an empty folder |

**The title carries the meaning.** The id says nothing about the work, so use
the title as the `# heading` of `spec.md` and the feature `README.md`, and as
the **Title** column of the portfolio table. Otherwise `features/` is a list
of handles nobody can read.

On a re-design the script recovers the title from the existing `spec.md`, so
`/pave:design DGF-8888` on its own is enough — nothing needs retyping.

Say the id and title back before continuing. Everything downstream is
addressed by them.

## Re-designing an existing feature

When the argument matched an existing feature directory, re-design that
feature. This is the route back when the **design** was wrong rather than the
execution — a missed case, a contract that cannot express what is needed.

**Re-design the whole feature. Do not patch it.**

The temptation is to find the one case that was missed, add a task for it and
leave everything else alone. Resist it: you cannot know that only one case was
missed. A patched design produces tasks that are each individually reasonable
and collectively inconsistent — a service handling a state its caller never
sends, an error path nobody raises — and that is the hardest kind of defect to
see, because every task looks fine on its own.

So run the whole phase again: re-read the knowledge, re-derive the blast
radius, re-examine the architecture, and rewrite every task from it. Keep what
still holds — this is re-deriving, not discarding — but derive it, do not
assume it.

Set the feature to `planning` while you work. Contracts are re-frozen at gate
1, so any task already built against a contract that changed goes back to
`pending`.

The user decides when this is the right move. Do not re-design because a build
agent found something awkward.

## Before starting

Locate the hub by walking up for `.pave-hub`. Read `config.yaml` and
`workspace.yaml`. If either is missing, stop and tell the user to run
`/pave:init`.

Read the hub's own `AGENTS.md` and `CLAUDE.md` too, if it has either — the
user's rules for Pave's agents. Read them explicitly rather than assuming they
are loaded. You walked up to find the hub, which means you may not be standing
in it, and a file only loads by itself when you are. `AGENTS.md` wins where
both exist and disagree.

## Choosing the model

`config.yaml` decides. Ask the script rather than reading the YAML yourself:

```
"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh agent designer
```

```
model=sonnet
effort=high
source=config
```

| Session model vs `model=` | What to do |
|---|---|
| Same | Design here, in this session |
| Different, stronger or weaker | Spawn the `designer` agent with that `model` and `effort` |
| You cannot tell your session model | Spawn. The configured model is guaranteed on that path |

`source=default` means `config.yaml` has no `designer` entry and the script
filled in Pave's default. Treat it the same way, and say so in one line.

Never substitute your own judgement for the configured model, in either
direction. The team chose it, and it is their token budget.

**The user's rules apply on both paths.** If you do the work here, follow the
hub's `AGENTS.md` / `CLAUDE.md` yourself. If you spawn the `designer`, their
absolute paths go in the design brief (§1), which it reads first.

### The spawned path: one designer, two stages

Spawn the `designer` **once**, after the blast radius is confirmed and the
design brief is written. Give it only:

- the absolute path to `features/<feature-id>/artifacts/design-brief.md`
- the absolute path to `writing-rules.md`, next to this skill
- which stage to produce: stage 1

It writes `spec.md`, `architecture.md` and `contracts/`, then returns. You
present them at gate 1.

After gate 1 is approved, **resume the same agent** with `SendMessage`. Don't
spawn a new one. Tell it the gate is approved and which files the user
changed, if any, then ask for stage 2. It still has the brief, the knowledge
and its own reasoning in context, so stage 2 costs only the task writing.

Spawn a fresh `designer` for stage 2 only when resuming isn't possible: no
`SendMessage` tool, or the agent is gone. Pass the same brief and
`writing-rules.md`, plus the approved stage-1 files. That is exactly why
`architecture.md` has to carry the reasoning and not only the conclusions.

You keep the conversation, the blast-radius confirmation and both gates. It
does the thinking. Do not read `writing-rules.md` yourself on this path; the
designer reads it.

## 1. Blast radius — from the knowledge index

Work out which services the feature touches before writing anything. This is
the step that justifies planning centrally: the answer is usually wider than
the person asking expects.

Load knowledge in stages. Never scan every service, and never read a knowledge
file the index did not point you at.

| Stage | Load | Purpose |
|---|---|---|
| 1 | `artifacts/knowledge/README.md` — **only this** | Match the feature against capabilities, terms and events |
| 2 | `knowledge/services/<candidate>/README.md` | Confirm or drop each candidate. ~50 lines each |
| 3 | The files the index named | `domain.md` for services being modified, `integration.md` for services at the seam |

A four-service feature in a twelve-service platform reads one index, four
summaries and a handful of deep files. That is the whole point of the index
existing.

**On the spawned path, stop at stage 2.** The designer reads the deep files
itself, so opening them here reads each one twice. Pick them from the index
and the summaries and list them in the brief. Open a deep file here only when
a summary cannot tell you whether a service is in the radius at all.

Read the Terms table carefully. The most expensive mistake this phase can make
is a vocabulary miss — designing a `Reservation` into a service that has named
that concept `StockHold` for two years. The task will be concrete, confident
and wrong, and an agent will build it.

Then confirm against `consumes` edges in `workspace.yaml` and the events table.
Topological coupling and domain coupling are different: an import graph will
not tell you that checkout touches stock because reservations expire.

### When knowledge is missing or stale

Never proceed blind, and never stop to send the user away. Check each
candidate for staleness the way `/pave:analyse` does — whether its
`source_paths` have changed since its recorded `commit` — then spawn `analyst`
agents for anything missing or stale, with the `model` and `effort` that
`pave.sh agent analyst` prints, and the same
required reading `/pave:analyse` §3 gives them — the hub's `AGENTS.md` /
`CLAUDE.md` — and continue once they return.

Say what you are doing and why, in one line. Do not ask permission for it.

### Uncertainty is not knowledge

Every `uncertain:` entry on a service you are about to design against must be
resolved by reading the code yourself, not carried forward. The analyst
flagged it precisely because it could not tell. If it bears on the feature,
verify it; if you cannot, say so at gate 1 rather than designing over it.

Report the radius and ask before continuing:

```
"Build checkout" appears to touch:
  order-service     orchestrates the flow                  confident
  stock-service     must reserve inventory                 confident
  payment-service   must authorise payment                 confident
  notification-service  confirmation email                 likely
  web-checkout      new UI flow                            likely
  shared-events     new OrderCheckedOut schema             likely

Missing anything?
```

A service the user adds here is worth more than three you inferred.

### Write the design brief

Once the radius is confirmed, write `features/<feature-id>/artifacts/design-brief.md`.
It is the hand-off: whoever writes the design outputs starts from it instead of
redoing the discovery you just did.

- The feature id, title and description, as the user gave them
- The confirmed services, with each one's role and your confidence
- Services the user added or removed, and why if they said
- **The exact knowledge files to read**, by absolute path — only the ones
  §1 judged relevant, not the index
- Each `uncertain:` entry you resolved, and what the code showed
- Anything still unresolved, to surface at gate 1
- Absolute paths to the hub's `AGENTS.md` / `CLAUDE.md`, if either exists

Keep it short: facts and paths, not the knowledge files' contents. The
designer reads those files itself. The brief exists so it never re-reads the
index or re-runs the staleness checks.

Write it on the in-session path too. It costs a few lines, and a re-design or
a resumed session can pick it up.

## 2–6. Spec, architecture, contracts, tasks, readiness

The rules for writing every design output live in `writing-rules.md`, next to this
file. Read it when you start writing, not before: the blast radius does not
need it, and a spawned designer reads it instead of you.

- Stage 1: §2 Spec, §3 Architecture, §4 Contracts, then **gate 1**
- Stage 2: §5 Task documents, §6 Readiness check, then **gate 2**

You own both gates, whichever path wrote the files. Stop and wait for
approval. On approval at gate 1 the contracts are frozen.

**Present a summary, not the files.** At each gate show:
- the path of every file written
- one line per file saying what it covers
- the decisions, assumptions and open questions the user must rule on

Do not read the files back into this session to present them. The user opens
the files; you open one only when they ask about it or ask for a change. On
the spawned path the designer's returned summary is the gate summary. On the
in-session path you wrote the files, so summarise from what you already have.

## 7. Write the roll-ups

**After approval, not before.** A feature marked `ready` that nobody approved
would let `/pave:build` run against a rejected plan.

- `features/<feature-id>/README.md` — from `templates/feature-README.md`, one row per
  task, built from task frontmatter
- `features/README.md` — from `templates/features-README.md`, one row per
  feature, status `ready`

Then say what to run next: `/pave:build <feature-id>`.
