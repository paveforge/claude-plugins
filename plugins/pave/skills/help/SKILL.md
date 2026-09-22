---
name: help
description: Ask a question about this hub or about Pave itself - a service's behaviour, a convention, why a feature is stuck, how a command works. Spawns an advisor agent that reads the knowledge base, conventions and hub docs to answer with citations. Use any time.
effort: low
argument-hint: "<question>"
allowed-tools: Read, Glob, Grep, Agent
---

# Pave — help

Answer one question. Nothing else.

This is the only skill that does not assume you are moving the pipeline
forward. You are not designing, building or reviewing anything — you want to
know something, and the answer lives in files this hub or this plugin
already has.

This skill is an orchestrator. It locates what exists and hands the question
to an `advisor`. The reading and the answering happen in the agent, for the
same reason every other phase delegates: keeping this session's context free
for whatever you do next.

## Before starting

Locate the hub, the same way every other skill does (walk up for
`.pave-hub`). **Not finding one is not an error here.** `/pave:help` also
answers questions about Pave itself — "what does `/pave:build` do", "why does
review not fail on a missing case" — and those need no hub at all.

If a hub was found, read `config.yaml` if present.

## 1. Gather paths, not content

Do not read any of these yourself — you are collecting what to hand the
advisor, not answering the question. Note which of these exist:

- `artifacts/knowledge/README.md` — the index
- `conventions/README.md`, and any per-language or per-service file under
  `conventions/`
- the hub's `AGENTS.md` / `CLAUDE.md` (`AGENTS.md` wins where both exist)
- `workspace.yaml`
- if the question names a feature, or the hub has exactly one, that
  feature's `spec.md`, `architecture.md` and `README.md`
- this plugin's own `skills/*/SKILL.md` files — always available, for
  questions about Pave itself rather than about the hub's services

If a hub exists but has no `artifacts/knowledge/`, that's worth noting to the
advisor, not a reason to stop — the question may still be answerable from
conventions, the hub's rules, or the plugin's own docs.

## 2. Spawn the advisor

One `advisor` agent, given: the question verbatim, every path gathered in
§1 labelled with what it is, and nothing else. It has no Bash and cannot
locate anything itself.

Use `agents.advisor.model` from `config.yaml` if that entry exists.
**Default to `sonnet` at `low` effort if it doesn't** — hubs created before
this skill existed won't have the entry, and a missing config line should
never be why `/pave:help` fails.

## 3. Relay the answer

Pass it through as the advisor wrote it — it already cites its sources, and
softening or re-deriving its answer here would just reintroduce the mistake
delegation exists to avoid. If the advisor says part of the question can't
be answered from what it has, say that plainly, and name the fix if there is
one (usually `/pave:analyse <service>` for a knowledge gap).

No report file is written. This phase produces an answer, not an artifact.
