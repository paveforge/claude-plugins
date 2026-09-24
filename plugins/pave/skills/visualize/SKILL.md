---
name: visualize
description: Draw a picture of a feature's blast radius, or of anything else about the hub you describe. Renders an interactive diagram with Claude's Artifact tool when it's available in this environment, otherwise writes a self-contained local HTML file. Use any time.
effort: low
argument-hint: "<feature id> | <description of what to draw>"
---

# Pave — visualize

Turn what's already written down into a picture. Nothing here is discovered
fresh — this skill reads the feature and knowledge files other phases wrote,
never a service repo.

## Before starting

Locate the hub, the same way every other skill does (walk up for
`.pave-hub`). Read `config.yaml` and the hub's `AGENTS.md` / `CLAUDE.md` if
either exists — the user's rules may shape labels or wording, never the
underlying facts.

## 1. Resolve the target

The argument is one of two things:

**A feature id** — `features/<id>/` exists → **blast radius mode**. Read
that feature's `spec.md` (Services touched table) and `architecture.md`
(Flow table, Contracts table, State ownership). The picture is a graph:
nodes are services, edges are the Flow steps and the Contracts between them,
labelled with what's emitted or produced.

**Anything else** — **freeform mode**. Treat the argument as a description
of what to draw. Pull only what it needs from `artifacts/knowledge/README.md`
(Capabilities, Terms, Events tables) and `workspace.yaml`; if the description
names a feature, read that feature's docs too, as above.

**No argument** — ask what to draw, and list the known feature ids from
`features/README.md` as a hint.

In either mode, **never read a service repo to fill a gap.** If the
knowledge a good picture needs is missing or stale, draw what the hub does
have and say plainly what's missing, pointing at `/pave:analyse` — a
fabricated node or edge is worse than an incomplete diagram, because it
looks authoritative.

## 2. Render

Check whether an `Artifact`-shaped tool is available in this session.

**If it is:** load the `artifact-diagramming` skill (and `artifact-design`)
first for the inline-SVG and layout conventions, then publish the diagram
and report the link back.

**If it is not:** write a single self-contained HTML file — inline SVG, no
external assets, no network calls — so it opens correctly from disk in any
browser. In blast radius mode, write it to
`features/<feature-id>/artifacts/diagram.html`. In freeform mode, write it to
the hub's `artifacts/visualizations/<slug>.html`, where `<slug>` is a short
kebab-case name derived from what was drawn — freeform requests describe
different things each time, so each gets its own file instead of overwriting
the last one. Both live under the same disposable-output convention
`artifacts/` already carries elsewhere in the hub. Tell the user the path to
open.

## 3. Report

One line: what was drawn, which files it came from, and the link or the
path to open. If anything was left out for a gap noted in §1, repeat that
here too — a diagram someone screenshots and shares should not quietly drop
the caveat.
