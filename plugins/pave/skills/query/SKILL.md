---
name: query
description: Ask a question about this hub - a service's behaviour, a convention, why a feature is stuck. Spawns a retriever agent that reads the knowledge base, conventions and hub docs to answer with citations. Use any time.
effort: low
argument-hint: "<question>"
allowed-tools: Read, Glob, Grep, Agent
---

# Pave — query

Answer one question about this hub. Nothing else.

This is the only phase besides `/pave:help` that does not assume you are
moving the pipeline forward. You want to know something about a service, a
convention or a feature, and the answer lives in files earlier phases
already wrote.

This skill is an orchestrator. It locates what exists and hands the question
to a `retriever`. The reading and the answering happen in the agent, for the
same reason every other phase delegates: keeping this session's context free
for whatever you do next.

For questions about Pave itself rather than about your hub — "what does
`/pave:build` do", "why does review not fail on a missing case" — use
`/pave:help` instead; it needs no hub and no agent.

## Before starting

Locate the hub, the same way every other skill does (walk up for
`.pave-hub`). If none is found, stop and say to run `/pave:init` first —
this phase has nothing to answer from without one.

Read `config.yaml` if present.

## 1. Gather paths, not content

Do not read any of these yourself — you are collecting what to hand the
retriever, not answering the question. Note which of these exist:

- `artifacts/knowledge/README.md` — the index
- `conventions/README.md`, and any per-language or per-service file under
  `conventions/`
- the hub's `AGENTS.md` / `CLAUDE.md` (`AGENTS.md` wins where both exist)
- `workspace.yaml`
- if the question names a feature, or the hub has exactly one, that
  feature's `spec.md`, `architecture.md` and `README.md`

If a hub exists but has no `artifacts/knowledge/`, that's worth noting to the
retriever, not a reason to stop — the question may still be answerable from
conventions or the hub's rules.

## 2. Spawn the retriever

One `retriever` agent, given: the question verbatim, every path gathered in
§1 labelled with what it is, and nothing else. It has no Bash and cannot
locate anything itself.

Pass the `model` and `effort` printed by `"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh agent retriever`.
**Default to `sonnet` at `low` effort if it exits 2** — hubs created before
this skill existed won't have the entry, and a missing config line should
never be why `/pave:query` fails.

## 3. Relay the answer

Pass it through as the retriever wrote it — it already cites its sources,
and softening or re-deriving its answer here would just reintroduce the
mistake delegation exists to avoid. If the retriever says part of the
question can't be answered from what it has, say that plainly, and name the
fix if there is one (usually `/pave:analyse <service>` for a knowledge gap).

No report file is written. This phase produces an answer, not an artifact.
